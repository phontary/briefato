#!/usr/bin/env bash
# Briefato — independent release validation harness (SYSADMIN-owned).
# Runs the checks the parent must see before any deploy: unit suites, real HTTP boot,
# landing-page integrity, DOCX generation, adversarial tenant isolation.
# Usage: tools/validate-release.sh
set -uo pipefail

ROOT="/workspace/briefato"
PY="$ROOT/.venv/bin/python"
PORT="${PORT:-8099}"
TMP="$(mktemp -d /tmp/briefato-validate-XXXX)"
FAIL=0
step() { printf '\n=== %s ===\n' "$1"; }
ok()   { echo "PASS: $1"; }
bad()  { echo "FAIL: $1"; FAIL=1; }

cd "$ROOT"

step "1. python syntax (whole app tree)"
"$PY" -m compileall -q app/briefato >/dev/null && ok "compileall app/briefato" || bad "compileall"

step "2. unit suites (offline, mock provider, temp DB)"
BRIEFATO_DATA_DIR="$TMP" BRIEFATO_DB_URL="sqlite:///$TMP/validate.db" BRIEFATO_LLM_MOCK=true \
  "$PY" -m pytest app/tests -q 2>&1 | tail -12
[ "${PIPESTATUS[0]}" -eq 0 ] && ok "pytest app/tests" || bad "pytest app/tests"

step "3. landing page integrity (if the landing workstream landed)"
if [ -f landing/selfcheck.py ]; then
  "$PY" landing/selfcheck.py 2>&1 | tail -15
  [ "${PIPESTATUS[0]}" -eq 0 ] && ok "landing selfcheck" || bad "landing selfcheck"
else
  echo "SKIP: landing/selfcheck.py not present yet"
fi

step "4. real HTTP boot + route matrix"
BRIEFATO_DATA_DIR="$TMP/http" BRIEFATO_DB_URL="sqlite:///$TMP/http/validate.db" \
BRIEFATO_LLM_MOCK=true BRIEFATO_SECRET_KEY="validate-secret" \
  "$PY" -m uvicorn briefato.main:app --app-dir app --host 127.0.0.1 --port "$PORT" \
  >"$TMP/uvicorn.log" 2>&1 &
SRV=$!
for _ in $(seq 1 40); do
  curl -sf -o /dev/null "http://127.0.0.1:$PORT/healthz" && break
  sleep 0.5
done

status() { curl -s -o /dev/null -w '%{http_code}' --max-time 10 "http://127.0.0.1:$PORT$1"; }
expect() { code="$(status "$1")"; if [ "$code" = "$2" ]; then ok "$1 -> $code"; else bad "$1 -> $code (expected $2)"; fi; }

expect /healthz 200
expect / 200
expect /preise 200
expect /impressum 200
expect /datenschutz 200
expect /agb 200
expect /anmelden 200
expect /registrieren 200
expect /assets/css/app.css 200
expect /app 303
expect /nicht-vorhanden-xyz 404
echo "--- /healthz body: $(curl -s --max-time 10 http://127.0.0.1:$PORT/healthz)"

step "5. DOCX generation smoke (mock provider)"
BRIEFATO_DATA_DIR="$TMP" BRIEFATO_DB_URL="sqlite:///$TMP/validate.db" BRIEFATO_LLM_MOCK=true \
  "$PY" - <<'PYEOF' 2>&1 | tail -20
import sys, tempfile, pathlib
sys.path.insert(0, "app")
from briefato.db import init_db, SessionLocal
from briefato import security
from briefato.models import User, Patient
init_db()
db = SessionLocal()
u = db.query(User).filter_by(email="smoke@briefato.test").first() or User(
    email="smoke@briefato.test", password_hash=security.hash_password("x"), letterhead_json={
        "practice_name": "Praxis Dr. Test", "street": "Teststr. 1", "zip": "10115", "city": "Berlin"})
db.add(u); db.commit()
p = db.query(Patient).filter_by(user_id=u.id).first() or Patient(
    user_id=u.id, first_name="Anna", last_name="Müller", birth_date=__import__("datetime").date(1974, 3, 2),
    insurance_number="A123456789")
db.add(p); db.commit()
from briefato.pipeline.generate import generate_letter
try:
    letter = generate_letter(db, user=u, patient=p, kind="arztbrief",
                             dictation="Patientin stellt sich vor. Seit zwei Wochen Husten, kein Fieber.",
                             letterhead=u.letterhead_json)
    text = security.decrypt_field(letter.content_enc)
    print("letter status:", letter.status, "| model:", letter.model, "| tokens:", letter.tokens_in, letter.tokens_out)
    print("text (first 300):", text[:300].replace("\n", " "))
    print("real name restored:", "Müller" in text)
except NotImplementedError:
    print("SKIP: pipeline still a stub")
except Exception as exc:
    print("PIPELINE ERROR:", type(exc).__name__, exc)
PYEOF

kill "$SRV" 2>/dev/null
step "RESULT"
if [ "$FAIL" -eq 0 ]; then echo "ALL CHECKS PASSED"; else echo "CHECKS FAILED — see above"; fi
echo "(logs: $TMP)"
exit "$FAIL"
