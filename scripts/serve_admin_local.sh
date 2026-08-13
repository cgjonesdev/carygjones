#!/usr/bin/env bash
# Local admin — unified mode runs the same Cloud Run service code against GCS (dev = prod).
# Set ADMIN_LEGACY=1 for the old static server + local sync port split.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"

if [[ "${ADMIN_LEGACY:-0}" == "1" ]]; then
  exec "$root/scripts/serve_admin_local_legacy.sh" "$@"
fi

exec "$root/scripts/run_admin_api_local.sh" "$@"
