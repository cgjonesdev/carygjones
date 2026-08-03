#!/usr/bin/env bash
# Upload local Gmail OAuth files to Secret Manager (run once after browser auth).
set -euo pipefail

export CLOUDSDK_PYTHON="${CLOUDSDK_PYTHON:-/usr/local/bin/python3.11}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="${ROOT}/cloud/config.env"

if [[ ! -f "$CONFIG" ]]; then
  echo "Copy cloud/config.env.example → cloud/config.env and set GCP_PROJECT." >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$CONFIG"

GMAIL_TOKEN_SECRET="${GMAIL_TOKEN_SECRET:-gmail-token}"
GMAIL_CLIENT_SECRET="${GMAIL_CLIENT_SECRET:-gmail-oauth-client}"

CREDS="${ROOT}/credentials.json"
TOKEN="${ROOT}/token.json"

for f in "$CREDS" "$TOKEN"; do
  if [[ ! -f "$f" ]]; then
    echo "Missing $f — run scan_recruiter_mail.py locally first to authorize." >&2
    exit 1
  fi
done

gcloud config set project "$GCP_PROJECT"

create_or_update_secret() {
  local name="$1"
  local file="$2"
  if gcloud secrets describe "$name" --project="$GCP_PROJECT" &>/dev/null; then
    gcloud secrets versions add "$name" --project="$GCP_PROJECT" --data-file="$file"
    echo "Updated secret $name"
  else
    gcloud secrets create "$name" --project="$GCP_PROJECT" --replication-policy=automatic --data-file="$file"
    echo "Created secret $name"
  fi
}

create_or_update_secret "$GMAIL_CLIENT_SECRET" "$CREDS"
create_or_update_secret "$GMAIL_TOKEN_SECRET" "$TOKEN"

JOB_SA="recruiter-scan-job@${GCP_PROJECT}.iam.gserviceaccount.com"
if gcloud iam service-accounts describe "$JOB_SA" --project="$GCP_PROJECT" &>/dev/null; then
  for secret in "$GMAIL_CLIENT_SECRET" "$GMAIL_TOKEN_SECRET"; do
    gcloud secrets add-iam-policy-binding "$secret" \
      --project="$GCP_PROJECT" \
      --member="serviceAccount:${JOB_SA}" \
      --role="roles/secretmanager.secretAccessor" \
      --quiet
  done
  echo "Granted ${JOB_SA} access to Gmail secrets."
fi

echo "Done. Secrets ready for Cloud Run Job."
