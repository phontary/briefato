#!/usr/bin/env bash
# Briefato — staging deploy: secrets in the vault + Portainer-native stack via the API.
# Run from the agent container (repo root). The repo must already be synced to the host:
#   ./deploy/sync-to-host.sh && ./deploy/deploy-staging.sh
#
# Secrets: generated once, stored in `pass` (services/briefato), pushed to Portainer as the
# stack's `env` array (the compose interpolates them). No secret is ever written to the repo
# and the API responses are parsed, never printed raw (they echo env values).
set -euo pipefail

HOST="${HOST:-root@192.168.178.100}"
SSH_PORT="${SSH_PORT:-2222}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/sysadmin_phontary}"
REPO_LOCAL="/workspace/briefato"
STACK="briefato"
STACK_ID_FILE="/tmp/.briefato_stack_id"
PAYLOAD="/tmp/.briefato_payload.json"
PK="/tmp/.briefato_pk"

export PATH="$HOME/.local/bin:$PATH"
export GNUPGHOME="/home/hermeswebui/.hermes/profiles/sysadmin/home/.gnupg"
export PASSWORD_STORE_DIR="/home/hermeswebui/.hermes/profiles/sysadmin/home/.password-store"
ssh_opts=(-i "$SSH_KEY" -p "$SSH_PORT" -o StrictHostKeyChecking=no -o BatchMode=yes)

cleanup() { shred -u "$PAYLOAD" "$PK" 2>/dev/null || rm -f "$PAYLOAD" "$PK"; }
trap cleanup EXIT

# ---------------------------------------------------------------- 1. secrets
secret_key="$(pass show services/briefato 2>/dev/null | sed -n 's/^secret_key: *//p' || true)"
field_key="$(pass show services/briefato 2>/dev/null | sed -n 's/^field_key: *//p' || true)"
if [ -z "${secret_key:-}" ] || [ -z "${field_key:-}" ]; then
  secret_key="$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')"
  field_key="$(python3 -c 'import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())')"
  entry="$(mktemp)"; chmod 600 "$entry"
  { echo "secret_key: $secret_key"
    echo "field_key: $field_key"
    echo "warn: rotating field_key makes stored clinical text unreadable"
    echo "note: stack env lives in Portainer (stacks/briefato) + this entry"
  } > "$entry"
  pass insert -m -f services/briefato < "$entry" >/dev/null
  shred -u "$entry"
  echo "vault: generated services/briefato"
else
  echo "vault: reusing services/briefato"
fi

# ---------------------------------------------------------------- 2. host image build
if [ "${SKIP_BUILD:-0}" != "1" ]; then
  echo "== building image on the host =="
  ssh "${ssh_opts[@]}" "$HOST" 'cd /mnt/fast/docker/briefato && DOCKER_BUILDKIT=1 docker build -f app/Dockerfile -t briefato:latest . >/tmp/briefato-build.log 2>&1; rc=$?; tail -3 /tmp/briefato-build.log; exit $rc' \
    || { echo "FATAL: image build failed (see /tmp/briefato-build.log on the host)" >&2; exit 1; }
fi

# The bind-mounted data dir must be writable by the container's uid 10001 (the image's own chown
# does not survive a bind mount) — otherwise startup dies with PermissionError on /data/letters.
ssh "${ssh_opts[@]}" "$HOST" 'mkdir -p /mnt/fast/docker/briefato/data && chown 10001:10001 /mnt/fast/docker/briefato/data && chmod 750 /mnt/fast/docker/briefato/data && ls -ld /mnt/fast/docker/briefato/data'

# ---------------------------------------------------------------- 3. payload (compose + env)
python3 - "$REPO_LOCAL/deploy/docker-compose.yml" "$REPO_LOCAL/deploy/stack.env.example" \
          "$PAYLOAD" "$secret_key" "$field_key" "$STACK" <<'PY'
import json, sys
compose_path, env_path, out_path, secret_key, field_key, stack = sys.argv[1:7]
env: dict[str, str] = {}
for line in open(env_path):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env[k.strip()] = v.strip()
env["BRIEFATO_SECRET_KEY"] = secret_key
env["BRIEFATO_FIELD_KEY"] = field_key
payload = {
    "name": stack,
    "stackFileContent": open(compose_path).read(),
    "env": [{"name": k, "value": v} for k, v in env.items()],
}
json.dump(payload, open(out_path, "w"))
print(f"payload: {len(payload['env'])} env entries, compose {len(payload['stackFileContent'])} bytes")
PY

# ---------------------------------------------------------------- 3. portainer auth
pass show services/portainer-admin | sed -n 's/^api-key: *//p' > "$PK"
[ -s "$PK" ] || { echo "FATAL: no api-key in services/portainer-admin" >&2; exit 1; }
chmod 600 "$PK"
ssh "${ssh_opts[@]}" "$HOST" 'cat > /root/.pk && chmod 600 /root/.pk' < "$PK"
scp -q -i "$SSH_KEY" -P "$SSH_PORT" -o StrictHostKeyChecking=no "$PAYLOAD" "$HOST:/root/payload.json"

endpoint="$(ssh "${ssh_opts[@]}" "$HOST" 'curl -sk https://localhost:9443/api/endpoints -H "X-API-Key: $(cat /root/.pk)"' \
  | python3 -c 'import json,sys;d=json.load(sys.stdin);print([e["Id"] for e in d if e["Name"]=="local"][0])')"
stack_id="$(ssh "${ssh_opts[@]}" "$HOST" 'curl -sk https://localhost:9443/api/stacks -H "X-API-Key: $(cat /root/.pk)"' \
  | python3 -c 'import json,sys;d=json.load(sys.stdin);print(next((s["Id"] for s in d if s["Name"]=="briefato"),""))')"

echo "endpoint=$endpoint stack_id=${stack_id:-<new>}"

if [ -n "$stack_id" ]; then
  ssh "${ssh_opts[@]}" "$HOST" "curl -sk -X PUT 'https://localhost:9443/api/stacks/$stack_id?endpointId=$endpoint' -H \"X-API-Key: \$(cat /root/.pk)\" -H 'Content-Type: application/json' --data-binary @/root/payload.json" > /tmp/.briefato_resp
else
  ssh "${ssh_opts[@]}" "$HOST" "curl -sk -X POST 'https://localhost:9443/api/stacks/create/standalone/string?endpointId=$endpoint' -H \"X-API-Key: \$(cat /root/.pk)\" -H 'Content-Type: application/json' --data-binary @/root/payload.json" > /tmp/.briefato_resp
fi

python3 - /tmp/.briefato_resp <<'PY'
import json, sys
raw = open(sys.argv[1]).read()
try:
    d = json.loads(raw)
except Exception:
    print("RAW RESPONSE:", raw[:300]); raise SystemExit(1)
if "Id" in d:
    print("stack:", d.get("Name"), "id:", d.get("Id"), "status:", d.get("Status"))
else:
    print("ERROR:", str(d.get("message") or d)[:400]); raise SystemExit(1)
PY
rm -f /tmp/.briefato_resp
ssh "${ssh_opts[@]}" "$HOST" 'rm -f /root/payload.json /root/.pk'

# ---------------------------------------------------------------- 4. verify
echo "== verify =="
sleep 5
ssh "${ssh_opts[@]}" "$HOST" "docker ps --filter name=briefato --format '{{.Names}} | {{.Status}} | {{.Ports}}'; curl -s -o /dev/null -w 'healthz via loopback: %{http_code}\n' http://127.0.0.1:8085/healthz; curl -s -o /dev/null -w 'landing via loopback: %{http_code}\n' http://127.0.0.1:8085/"
