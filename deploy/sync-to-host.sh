#!/usr/bin/env bash
# Mirror the repo from the agent container to the Docker host.
# Usage: ./deploy/sync-to-host.sh [user@host]
# The host copy is the build context for the Portainer stack (see deploy/docker-compose.yml).
set -euo pipefail

HOST="${1:-root@192.168.178.100}"
PORT="${SSH_PORT:-2222}"
KEY="${SSH_KEY:-$HOME/.ssh/sysadmin_phontary}"
SRC="/workspace/briefato"
DST="/mnt/fast/docker/briefato"

ssh_opts=(-i "$KEY" -p "$PORT" -o StrictHostKeyChecking=no -o BatchMode=yes)

ssh "${ssh_opts[@]}" "$HOST" "mkdir -p '$DST' '$DST/data' '$DST/deploy' && chmod 700 '$DST/data'"

# The mirror must be exact: tar extraction only overwrites, so files deleted in the repo (e.g. merged
# Musterbriefe) would linger on the host and end up in the image. Wipe the code trees only — never
# `data/` (the live SQLite DB) and never `deploy/stack.env` (secrets live in Portainer, the file is
# kept for reference).
ssh "${ssh_opts[@]}" "$HOST" "rm -rf '$DST/app' '$DST/landing' '$DST/brain' '$DST/docs' '$DST/tools' '$DST/deploy/docker-compose.yml'"

tar czf - -C "$SRC" \
  --exclude='./.venv' --exclude='./.git' --exclude='./data' --exclude='__pycache__' \
  --exclude='*.pyc' --exclude='.pytest_cache' . \
  | ssh "${ssh_opts[@]}" "$HOST" "tar xzf - -C '$DST' && chmod -R a+rX '$DST/app' '$DST/landing' '$DST/docs' 2>/dev/null || true"

ssh "${ssh_opts[@]}" "$HOST" "ls -la '$DST' && du -sh '$DST'"
echo "synced $SRC -> $HOST:$DST"
