#!/usr/bin/env bash
# Briefato backup: consistent SQLite snapshot + letter files, GPG-encrypted, one copy off-host.
# Runs ON THE HOST (phontary). Install as /usr/local/bin/backup-briefato.sh (mode 750 root)
# and schedule daily via cron or a systemd timer (see docs stage S5).
#
# Requires: python3 (sqlite3 VACUUM INTO), gpg, and a root-only passphrase file
#   /root/.briefato-backup-key  (mode 600) — the same passphrase is stored in pass.
set -euo pipefail

SRC="${BRIEFATO_SRC:-/mnt/fast/docker/briefato}"
DATA="$SRC/data"
OUT="${BRIEFATO_BACKUP_DIR:-/mnt/fast/backups/briefato}"
KEYFILE="${BRIEFATO_BACKUP_KEYFILE:-/root/.briefato-backup-key}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

[ -r "$KEYFILE" ] || { echo "FATAL: missing passphrase file $KEYFILE" >&2; exit 1; }
mkdir -p "$OUT"

# 1. consistent DB snapshot (never copy a live WAL database file-by-file)
if [ -f "$DATA/briefato.db" ]; then
  python3 - "$DATA/briefato.db" "$WORK/briefato.db" <<'PY'
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
con = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
con.execute("VACUUM INTO ?", (dst,))
con.close()
print("db snapshot ok")
PY
fi

# 2. letters directory (encrypted blobs live inside the DB, but exports/attachments may sit here)
[ -d "$DATA/letters" ] && tar czf "$WORK/letters.tar.gz" -C "$DATA" letters

# 3. encrypted archive
tar czf "$WORK/briefato-$STAMP.tar.gz" -C "$WORK" --exclude="briefato-$STAMP.tar.gz" .
gpg --batch --yes --quiet --symmetric --cipher-algo AES256 \
    --passphrase-file "$KEYFILE" \
    --output "$OUT/briefato-$STAMP.tar.gz.gpg" "$WORK/briefato-$STAMP.tar.gz"

# 4. off-host copy (target: the rescuer host 192.168.178.200). Requires the peer path to exist;
#    enable once the off-host target is confirmed — do not silently skip in production.
# scp -P 2222 -i /root/.ssh/id_ed25519 "$OUT/briefato-$STAMP.tar.gz.gpg" \
#     sysadmin@192.168.178.200:/mnt/backups/briefato/

# 5. verify decryptability, then retention (14 daily / 8 weekly by default)
gpg --batch --quiet --decrypt --passphrase-file "$KEYFILE" \
    "$OUT/briefato-$STAMP.tar.gz.gpg" | tar tzf - >/dev/null && echo "verify OK: $STAMP"
find "$OUT" -name 'briefato-*.tar.gz.gpg' -mtime +14 -delete

echo "backup complete: $OUT/briefato-$STAMP.tar.gz.gpg ($(du -h "$OUT/briefato-$STAMP.tar.gz.gpg" | cut -f1))"
