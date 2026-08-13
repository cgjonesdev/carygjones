#!/usr/bin/env bash
# Run the same Cloud Run admin API + UI locally — GCS is the source of truth (dev = prod code path).
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
port="${1:-8080}"

if [[ -f "$root/tools/cloud_run/cloud/config.env" ]]; then
  # shellcheck disable=SC1090
  source "$root/tools/cloud_run/cloud/config.env"
elif [[ -f "$root/tools/gmail/cloud/config.env" ]]; then
  # shellcheck disable=SC1090
  source "$root/tools/gmail/cloud/config.env"
fi

if [[ -f "$root/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$root/.env"
  set +a
fi

export GCS_BUCKET="${GCS_BUCKET:-cgjonesdev-recruiter-inbox}"
export JOB_MODE=cloud
export ADMIN_STATIC_DIR="$root/website/admin"
export INTERVIEW_PREP_DIR="$root/interview/prep"
export ASSETS_DIR="$root"
export PYTHONPATH="$root/tools/cloud_run:$root/tools/gmail:${PYTHONPATH:-}"

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "WARNING: OPENAI_API_KEY not set — add it to repo .env or export before starting." >&2
else
  echo "OPENAI_API_KEY loaded (generate + LLM enabled)"
fi

ensure_python_deps() {
  local cloud_req="$root/tools/cloud_run/requirements.txt"
  local gmail_req="$root/tools/gmail/requirements.txt"
  if python3 -c "import html2docx, playwright, fastapi, uvicorn, openai" 2>/dev/null; then
    return 0
  fi
  echo "Installing admin API dependencies (html2docx, playwright, fastapi, …)…"
  python3 -m pip install --quiet -r "$cloud_req" -r "$gmail_req"
  if ! python3 -c "import playwright" 2>/dev/null; then
    echo "Playwright install failed." >&2
    exit 1
  fi
  if [[ ! -d "${HOME}/.cache/ms-playwright" ]] && [[ ! -d "${PLAYWRIGHT_BROWSERS_PATH:-}" ]]; then
    echo "Installing Playwright Chromium (one-time, for PDF generation)…"
    python3 -m playwright install chromium
  fi
}

ensure_python_deps

free_listen_port() {
  local listen_port="$1"
  local pids
  pids="$(lsof -nP -iTCP:"$listen_port" -sTCP:LISTEN -t 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "Stopping stale process on port ${listen_port} (pid(s): ${pids//$'\n'/ })"
    kill $pids 2>/dev/null || true
    sleep 0.5
  fi
}

free_listen_port "$port"

echo "Unified admin API (local = prod code path)"
echo "  GCS_BUCKET=$GCS_BUCKET"
echo "  Admin UI:  http://127.0.0.1:${port}/admin/"
echo "  API:       http://127.0.0.1:${port}/api/health"
echo "Press Ctrl+C to stop."
cd "$root/tools/cloud_run"
exec python3 -m uvicorn service.app:app --host 127.0.0.1 --port "$port" --reload
