#!/bin/bash
# Add the briefato.sabry.io site block to Caddy (stack 54) — validated, with a compose backup.
# Runs ON phontary as root. Procedure per skill devops/portainer (Caddy heredoc + stack 54).
set -euo pipefail

COMPOSE_DIR=/mnt/fast/lib/docker/volumes/portainer_data/_data/compose/54
COMPOSE="$COMPOSE_DIR/docker-compose.yml"
TS="$(date +%Y%m%d-%H%M%S)"

echo "== backup =="
cp "$COMPOSE" "$COMPOSE.bak-$TS"
echo "backup: $COMPOSE.bak-$TS"

echo "== candidate Caddyfile (live + new block) =="
docker exec caddy cat /etc/caddy/Caddyfile > /root/cand.Caddyfile
if ! grep -q "briefato.sabry.io" /root/cand.Caddyfile; then
  cat >> /root/cand.Caddyfile <<'CEOF'

briefato.sabry.io {
    tls internal
    import common
    import crowdsec_protect
    reverse_proxy 127.0.0.1:8085 {
        header_up Host {upstream_hostport}
    }
}
CEOF
fi
docker cp /root/cand.Caddyfile caddy:/tmp/cand.Caddyfile
echo "== validate =="
docker exec caddy caddy validate --adapter caddyfile --config /tmp/cand.Caddyfile

echo "== patch compose heredoc =="
python3 - <<'PY'
import pathlib
p = pathlib.Path("/mnt/fast/lib/docker/volumes/portainer_data/_data/compose/54/docker-compose.yml")
text = p.read_text()
if "briefato.sabry.io" in text:
    print("compose already contains briefato block — no change")
    raise SystemExit(0)
anchor = "      healthchecks.sabry.io {"
if anchor not in text:
    raise SystemExit("anchor not found: healthchecks.sabry.io block")
i = text.index(anchor)
end = text.index("\n      }\n", i) + len("\n      }\n")
ind = "      "
block = (
    f"{ind}briefato.sabry.io {{\n"
    f"{ind}    tls internal\n"
    f"{ind}    import common\n"
    f"{ind}    import crowdsec_protect\n"
    f"{ind}    reverse_proxy 127.0.0.1:8085 {{\n"
    f"{ind}        header_up Host {{upstream_hostport}}\n"
    f"{ind}    }}\n"
    f"{ind}}}\n"
)
p.write_text(text[:end] + block + text[end:])
print("compose patched")
PY
grep -n -A8 "briefato.sabry.io" "$COMPOSE" | head -12

echo "== targeted caddy redeploy =="
cd "$COMPOSE_DIR"
ln -sf stack.env .env
docker compose -p infrastructure up -d --no-deps caddy
sleep 6
docker ps --filter name=caddy --format '{{.Names}} | {{.Status}}'
echo "== live Caddyfile has the block? =="
docker exec caddy grep -c "briefato.sabry.io" /etc/caddy/Caddyfile || true
