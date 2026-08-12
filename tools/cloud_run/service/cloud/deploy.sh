#!/usr/bin/env bash
# Deploy Cloud Run Service: admin API + dashboard UI
set -euo pipefail

export CLOUDSDK_PYTHON="${CLOUDSDK_PYTHON:-/usr/local/bin/python3.11}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/../../.." && pwd)"
CONFIG="${ROOT}/cloud/config.env"
if [[ ! -f "$CONFIG" ]]; then
  CONFIG="${ROOT}/../cloud/config.env"
fi

if [[ ! -f "$CONFIG" ]]; then
  echo "Copy tools/cloud_run/cloud/config.env.example → config.env" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$CONFIG"

: "${GCP_PROJECT:?Set GCP_PROJECT in config.env}"
: "${GCP_REGION:?Set GCP_REGION in config.env}"
: "${GCS_BUCKET:?Set GCS_BUCKET in config.env}"

SERVICE_NAME="${ADMIN_SERVICE_NAME:-job-search-admin}"
OPENAI_SECRET="${OPENAI_SECRET:-openai-api-key}"
GMAIL_TOKEN_SECRET="${GMAIL_TOKEN_SECRET:-gmail-token}"
GMAIL_CLIENT_SECRET="${GMAIL_CLIENT_SECRET:-gmail-oauth-client}"
ADMIN_API_KEY_SECRET="${ADMIN_API_KEY_SECRET:-admin-api-key}"
LINKED_API_SECRET="${LINKED_API_SECRET:-linked-api-token}"
LINKED_IDENT_SECRET="${LINKED_IDENT_SECRET:-linked-identification-token}"

IMAGE="gcr.io/${GCP_PROJECT}/${SERVICE_NAME}:latest"
JOB_SA="recruiter-scan-job@${GCP_PROJECT}.iam.gserviceaccount.com"

gcloud config set project "$GCP_PROJECT"

echo "==> Building admin service image..."
gcloud builds submit "$REPO_ROOT" \
  --project="$GCP_PROJECT" \
  --config="${ROOT}/cloud/cloudbuild.yaml" \
  --quiet

ENV_VARS="JOB_MODE=cloud,GCS_BUCKET=${GCS_BUCKET},APP_ROOT=/app,ASSETS_DIR=/app/assets,LINKEDIN_SYNC_APPLIED=0"
for var in MATCH_THRESHOLD MAX_GENERATE_PER_RUN OPENAI_MODEL_SCORE OPENAI_MODEL_GENERATE ADMIN_CORS_ORIGINS; do
  if [[ -n "${!var:-}" ]]; then
    ENV_VARS="${ENV_VARS},${var}=${!var}"
  fi
done

SECRET_FLAGS="GMAIL_CREDENTIALS_JSON=${GMAIL_CLIENT_SECRET}:latest,GMAIL_TOKEN_JSON=${GMAIL_TOKEN_SECRET}:latest,OPENAI_API_KEY=${OPENAI_SECRET}:latest"
if gcloud secrets describe "$ADMIN_API_KEY_SECRET" --project="$GCP_PROJECT" &>/dev/null; then
  SECRET_FLAGS="${SECRET_FLAGS},ADMIN_API_KEY=${ADMIN_API_KEY_SECRET}:latest"
fi
if gcloud secrets describe "$LINKED_API_SECRET" --project="$GCP_PROJECT" &>/dev/null; then
  SECRET_FLAGS="${SECRET_FLAGS},LINKED_API_TOKEN=${LINKED_API_SECRET}:latest"
fi
if gcloud secrets describe "$LINKED_IDENT_SECRET" --project="$GCP_PROJECT" &>/dev/null; then
  SECRET_FLAGS="${SECRET_FLAGS},LINKED_IDENTIFICATION_TOKEN=${LINKED_IDENT_SECRET}:latest"
fi

echo "==> Deploying Cloud Run service ${SERVICE_NAME}..."
gcloud run deploy "$SERVICE_NAME" \
  --project="$GCP_PROJECT" \
  --region="$GCP_REGION" \
  --image="$IMAGE" \
  --service-account="$JOB_SA" \
  --set-env-vars="$ENV_VARS" \
  --set-secrets="$SECRET_FLAGS" \
  --memory=2Gi \
  --cpu=2 \
  --timeout=3600 \
  --min-instances=0 \
  --max-instances=2 \
  --allow-unauthenticated \
  --quiet

URL="$(gcloud run services describe "$SERVICE_NAME" --region="$GCP_REGION" --project="$GCP_PROJECT" --format='value(status.url)')"
echo ""
echo "Admin API:       ${URL}"
echo "API health:      ${URL}/api/health"
echo ""
echo "Set GitHub repo variable on cgjonesdev/carygjones:"
echo "  gh variable set ADMIN_API_BASE_URL --body \"${URL}\" --repo cgjonesdev/carygjones"
echo "Then push to main (or re-run Deploy portfolio website workflow) to wire Pages admin."
