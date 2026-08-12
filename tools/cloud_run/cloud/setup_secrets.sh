#!/usr/bin/env bash
# Upload OpenAI (and optional LinkedIn) secrets for run-protocols Cloud Run Job.
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

OPENAI_SECRET="${OPENAI_SECRET:-openai-api-key}"
LINKED_API_SECRET="${LINKED_API_SECRET:-linked-api-token}"
LINKED_IDENT_SECRET="${LINKED_IDENT_SECRET:-linked-identification-token}"

gcloud config set project "$GCP_PROJECT"

create_or_update_secret() {
  local name="$1"
  local value="$2"
  if gcloud secrets describe "$name" --project="$GCP_PROJECT" &>/dev/null; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --project="$GCP_PROJECT" --data-file=-
    echo "Updated secret $name"
  else
    printf '%s' "$value" | gcloud secrets create "$name" \
      --project="$GCP_PROJECT" \
      --replication-policy=automatic \
      --data-file=-
    echo "Created secret $name"
  fi
}

if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  create_or_update_secret "$OPENAI_SECRET" "$OPENAI_API_KEY"
else
  echo "Set OPENAI_API_KEY in the environment, or paste when prompted:"
  read -r -s -p "OpenAI API key: " OPENAI_API_KEY
  echo
  if [[ -z "$OPENAI_API_KEY" ]]; then
    echo "No key provided; skipping OpenAI secret." >&2
  else
    create_or_update_secret "$OPENAI_SECRET" "$OPENAI_API_KEY"
  fi
fi

if [[ -n "${LINKED_API_TOKEN:-}" ]]; then
  create_or_update_secret "$LINKED_API_SECRET" "$LINKED_API_TOKEN"
fi
if [[ -n "${LINKED_IDENTIFICATION_TOKEN:-}" ]]; then
  create_or_update_secret "$LINKED_IDENT_SECRET" "$LINKED_IDENTIFICATION_TOKEN"
fi

ADMIN_API_KEY_SECRET="${ADMIN_API_KEY_SECRET:-admin-api-key}"
if [[ -n "${ADMIN_API_KEY:-}" ]]; then
  create_or_update_secret "$ADMIN_API_KEY_SECRET" "$ADMIN_API_KEY"
elif [[ -n "${ADMIN_PASSWORD:-}" ]]; then
  create_or_update_secret "$ADMIN_API_KEY_SECRET" "$ADMIN_PASSWORD"
  echo "Set ${ADMIN_API_KEY_SECRET} from ADMIN_PASSWORD (matches GitHub Pages login / X-Admin-Key)"
else
  echo "Tip: ADMIN_API_KEY=… or ADMIN_PASSWORD=… ./setup_secrets.sh so Pages sign-in works with the API."
fi

JOB_SA="recruiter-scan-job@${GCP_PROJECT}.iam.gserviceaccount.com"
if gcloud iam service-accounts describe "$JOB_SA" --project="$GCP_PROJECT" &>/dev/null; then
  for secret in "$OPENAI_SECRET" "$LINKED_API_SECRET" "$LINKED_IDENT_SECRET" "$ADMIN_API_KEY_SECRET"; do
    if gcloud secrets describe "$secret" --project="$GCP_PROJECT" &>/dev/null; then
      gcloud secrets add-iam-policy-binding "$secret" \
        --project="$GCP_PROJECT" \
        --member="serviceAccount:${JOB_SA}" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet
    fi
  done
  echo "Granted ${JOB_SA} access to protocol secrets."
fi

echo "Done. Also run tools/gmail/cloud/setup_secrets.sh if Gmail OAuth is not uploaded yet."
