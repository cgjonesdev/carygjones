#!/usr/bin/env bash
# Build and deploy Cloud Run Job: run-protocols (Gmail scan + OpenAI generate + GCS).
set -euo pipefail

export CLOUDSDK_PYTHON="${CLOUDSDK_PYTHON:-/usr/local/bin/python3.11}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/../.." && pwd)"
CONFIG="${ROOT}/cloud/config.env"

if [[ ! -f "$CONFIG" ]]; then
  echo "Copy cloud/config.env.example → cloud/config.env and set values." >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$CONFIG"

: "${GCP_PROJECT:?Set GCP_PROJECT in config.env}"
: "${GCP_REGION:?Set GCP_REGION in config.env}"
: "${GCS_BUCKET:?Set GCS_BUCKET in config.env}"

JOB_NAME="${JOB_NAME:-run-protocols}"
OPENAI_SECRET="${OPENAI_SECRET:-openai-api-key}"
GMAIL_TOKEN_SECRET="${GMAIL_TOKEN_SECRET:-gmail-token}"
GMAIL_CLIENT_SECRET="${GMAIL_CLIENT_SECRET:-gmail-oauth-client}"
LINKED_API_SECRET="${LINKED_API_SECRET:-linked-api-token}"
LINKED_IDENT_SECRET="${LINKED_IDENT_SECRET:-linked-identification-token}"

IMAGE="gcr.io/${GCP_PROJECT}/${JOB_NAME}:latest"
JOB_SA="recruiter-scan-job@${GCP_PROJECT}.iam.gserviceaccount.com"
RUN_URI="https://${GCP_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${GCP_PROJECT}/jobs/${JOB_NAME}:run"

gcloud config set project "$GCP_PROJECT"

echo "==> Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  gmail.googleapis.com \
  containerregistry.googleapis.com \
  --project="$GCP_PROJECT"

echo "==> GCS bucket..."
if ! gsutil ls -b "gs://${GCS_BUCKET}" &>/dev/null; then
  gsutil mb -p "$GCP_PROJECT" -l "$GCP_REGION" -b on "gs://${GCS_BUCKET}"
fi

echo "==> Service account (reuse recruiter-scan-job)..."
if ! gcloud iam service-accounts describe "$JOB_SA" --project="$GCP_PROJECT" &>/dev/null; then
  echo "Missing ${JOB_SA}. Deploy tools/gmail/cloud/deploy.sh first." >&2
  exit 1
fi

gsutil iam ch "serviceAccount:${JOB_SA}:objectAdmin" "gs://${GCS_BUCKET}" 2>/dev/null || \
gsutil iam ch "serviceAccount:${JOB_SA}:roles/storage.objectAdmin" "gs://${GCS_BUCKET}"

gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
  --member="serviceAccount:${JOB_SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --quiet

echo "==> Building image from repo root..."
gcloud builds submit "$REPO_ROOT" \
  --project="$GCP_PROJECT" \
  --config="${ROOT}/cloud/cloudbuild.yaml" \
  --quiet

ENV_VARS="JOB_MODE=cloud,GCS_BUCKET=${GCS_BUCKET},APP_ROOT=/app,ASSETS_DIR=/app/assets"
for var in MATCH_THRESHOLD MAX_GENERATE_PER_RUN OPENAI_MODEL_SCORE OPENAI_MODEL_GENERATE SKIP_LINKEDIN LINKEDIN_SEARCH_TERM; do
  if [[ -n "${!var:-}" ]]; then
    ENV_VARS="${ENV_VARS},${var}=${!var}"
  fi
done

SECRET_FLAGS="GMAIL_CREDENTIALS_JSON=${GMAIL_CLIENT_SECRET}:latest,GMAIL_TOKEN_JSON=${GMAIL_TOKEN_SECRET}:latest,OPENAI_API_KEY=${OPENAI_SECRET}:latest"

if gcloud secrets describe "$LINKED_API_SECRET" --project="$GCP_PROJECT" &>/dev/null; then
  SECRET_FLAGS="${SECRET_FLAGS},LINKED_API_TOKEN=${LINKED_API_SECRET}:latest"
fi
if gcloud secrets describe "$LINKED_IDENT_SECRET" --project="$GCP_PROJECT" &>/dev/null; then
  SECRET_FLAGS="${SECRET_FLAGS},LINKED_IDENTIFICATION_TOKEN=${LINKED_IDENT_SECRET}:latest"
fi

RUN_JOBS="gcloud alpha run jobs"
JOB_FLAGS=(
  --project="$GCP_PROJECT"
  --region="$GCP_REGION"
  --image="$IMAGE"
  --service-account="$JOB_SA"
  --set-env-vars="$ENV_VARS"
  --set-secrets="$SECRET_FLAGS"
  --max-retries=1
  --task-timeout=30m
  --memory=2Gi
  --cpu=2
)

echo "==> Deploying Cloud Run Job ${JOB_NAME}..."
if $RUN_JOBS describe "$JOB_NAME" --region="$GCP_REGION" --project="$GCP_PROJECT" &>/dev/null; then
  $RUN_JOBS update "$JOB_NAME" "${JOB_FLAGS[@]}"
else
  $RUN_JOBS create "$JOB_NAME" "${JOB_FLAGS[@]}"
fi

SCHEDULER_NAME="${SCHEDULER_NAME:-run-protocols-weekdays}"
SCHEDULE_CRON="${SCHEDULE_CRON:-0 7 * * 1-5}"
SCHEDULE_TIMEZONE="${SCHEDULE_TIMEZONE:-America/Los_Angeles}"
SCHEDULER_SA="recruiter-scan-scheduler@${GCP_PROJECT}.iam.gserviceaccount.com"

if [[ "${SKIP_SCHEDULER:-}" != "1" ]]; then
  echo "==> Cloud Scheduler (${SCHEDULE_CRON}, ${SCHEDULE_TIMEZONE})..."
  if gcloud scheduler jobs describe "$SCHEDULER_NAME" --location="$GCP_REGION" --project="$GCP_PROJECT" &>/dev/null; then
    gcloud scheduler jobs update http "$SCHEDULER_NAME" \
      --project="$GCP_PROJECT" \
      --location="$GCP_REGION" \
      --schedule="$SCHEDULE_CRON" \
      --time-zone="$SCHEDULE_TIMEZONE" \
      --uri="$RUN_URI" \
      --http-method=POST \
      --oauth-service-account-email="$SCHEDULER_SA" \
      --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform"
  else
    gcloud scheduler jobs create http "$SCHEDULER_NAME" \
      --project="$GCP_PROJECT" \
      --location="$GCP_REGION" \
      --schedule="$SCHEDULE_CRON" \
      --time-zone="$SCHEDULE_TIMEZONE" \
      --uri="$RUN_URI" \
      --http-method=POST \
      --oauth-service-account-email="$SCHEDULER_SA" \
      --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform" \
      --description="Trigger run-protocols Cloud Run Job"
  fi
fi

echo ""
echo "Deployed."
echo "  Job:       ${JOB_NAME} (${GCP_REGION})"
echo "  Image:     ${IMAGE}"
echo "  Bucket:    gs://${GCS_BUCKET}/"
echo ""
echo "Secrets:  cloud/setup_secrets.sh (+ tools/gmail/cloud/setup_secrets.sh for Gmail)"
echo "Test:     gcloud alpha run jobs execute ${JOB_NAME} --region=${GCP_REGION} --wait"
echo "Pull:     python tools/gmail/sync_gcs_inbox.py --all"
