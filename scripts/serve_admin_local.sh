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

if [[ -z "${ADMIN_API_BASE_URL:-}" ]]; then
  if command -v gh >/dev/null 2>&1; then
    ADMIN_API_BASE_URL="$(gh variable get ADMIN_API_BASE_URL --repo cgjonesdev/carygjones 2>/dev/null || true)"
  fi
fi
export ADMIN_API_BASE_URL="${ADMIN_API_BASE_URL:-https://job-search-admin-416806702268.us-west1.run.app}"

free_sync_port() {
  local pids
  pids="$(lsof -nP -iTCP:"$sync_port" -sTCP:LISTEN -t 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "Stopping stale sync server on port ${sync_port} (pid(s): ${pids//$'\n'/ })"
    kill $pids 2>/dev/null || true
    sleep 0.5
    pids="$(lsof -nP -iTCP:"$sync_port" -sTCP:LISTEN -t 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
      echo "Port ${sync_port} still in use. Run: lsof -nP -iTCP:${sync_port} -sTCP:LISTEN" >&2
      exit 1
    fi
  fi
}

echo "GCS_BUCKET=$GCS_BUCKET"
echo "ADMIN_API_BASE_URL=$ADMIN_API_BASE_URL"
python3 "$root/scripts/build_admin_data.py" >/dev/null

free_sync_port
python3 "$root/scripts/local_sync_server.py" "$sync_port" &
sync_pid=$!
cleanup() {
  kill "$sync_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS "http://127.0.0.1:${sync_port}/api/health" >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$sync_pid" 2>/dev/null; then
    echo "Local sync server failed to start on port ${sync_port}." >&2
    wait "$sync_pid" 2>/dev/null || true
    exit 1
  fi
  sleep 0.2
done
if ! curl -fsS "http://127.0.0.1:${sync_port}/api/health" >/dev/null 2>&1; then
  echo "Local sync server did not become ready on port ${sync_port}." >&2
  exit 1
fi

echo "Admin UI:  http://localhost:${port}/admin/"
echo "Sync API:  http://127.0.0.1:${sync_port}/api/sync"
echo "Protocol API: ${ADMIN_API_BASE_URL} (enter admin password in Connection → Save key to run protocols)"
echo "Press Ctrl+C to stop both servers."
exec python3 -m http.server "$port" --directory "$root/website"
