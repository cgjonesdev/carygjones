#!/usr/bin/env bash
# Print the admin dashboard password (same value as Cloud Run ADMIN_API_KEY).
#
# The password is stored in GCP Secret Manager as admin-api-key.
# GitHub secret ADMIN_PASSWORD is write-only and cannot be retrieved.
#
# Usage:
#   ./scripts/show_admin_password.sh
#   GCP_PROJECT=cgjonesdev ./scripts/show_admin_password.sh

set -euo pipefail

export CLOUDSDK_PYTHON="${CLOUDSDK_PYTHON:-python3.11}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="${ROOT}/tools/cloud_run/cloud/config.env"

if [[ -f "$CONFIG" ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG"
fi

PROJECT="${GCP_PROJECT:-cgjonesdev}"
SECRET="${ADMIN_API_KEY_SECRET:-admin-api-key}"

if ! gcloud secrets describe "$SECRET" --project="$PROJECT" &>/dev/null; then
  echo "Secret gs://${PROJECT}/${SECRET} not found." >&2
  echo "Create it with:" >&2
  echo "  ADMIN_API_KEY='your-password' ${ROOT}/tools/cloud_run/cloud/setup_secrets.sh" >&2
  exit 1
fi

echo "Admin password (also use as X-Admin-Key for the API):"
gcloud secrets versions access latest --secret="$SECRET" --project="$PROJECT"
