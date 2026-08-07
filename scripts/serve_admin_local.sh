#!/usr/bin/env bash
# Serve admin UI locally + optional GCS sync helper for "Pull from GCS" button.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
port="${1:-8080}"
sync_port="${LOCAL_SYNC_PORT:-8765}"

if [[ -z "${GCS_BUCKET:-}" ]]; then
  if [[ -f "$root/tools/gmail/cloud/config.env" ]]; then
    # shellcheck disable=SC1090
    source "$root/tools/gmail/cloud/config.env"
  elif [[ -f "$root/tools/cloud_run/cloud/config.env" ]]; then
    # shellcheck disable=SC1090
    source "$root/tools/cloud_run/cloud/config.env"
  fi
fi

export GCS_BUCKET="${GCS_BUCKET:-cgjonesdev-recruiter-inbox}"

echo "GCS_BUCKET=$GCS_BUCKET"
python3 "$root/scripts/build_admin_data.py" >/dev/null

python3 "$root/scripts/local_sync_server.py" "$sync_port" &
sync_pid=$!
cleanup() {
  kill "$sync_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Admin UI:  http://localhost:${port}/admin/"
echo "Sync API:  http://127.0.0.1:${sync_port}/api/sync"
echo "Press Ctrl+C to stop both servers."
exec python3 -m http.server "$port" --directory "$root/website"
