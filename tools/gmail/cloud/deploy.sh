#!/usr/bin/env bash
# Build image, deploy Cloud Run Job, and schedule every 10 minutes.
set -euo pipefail

export CLOUDSDK_PYTHON="${CLOUDSDK_PYTHON:-/usr/local/bin/python3.11}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
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

JOB_NAME="${JOB_NAME:-recruiter-scan}"
ARTIFACT_REPO="${ARTIFACT_REPO:-job-search}"
SCHEDULER_NAME="${SCHEDULER_NAME:-recruiter-scan-weekdays}"
SCHEDULE_CRON="${SCHEDULE_CRON:-*/10 * * * 1-5}"
SCHEDULE_TIMEZONE="${SCHEDULE_TIMEZONE:-America/Los_Angeles}"
GMAIL_TOKEN_SECRET="${GMAIL_TOKEN_SECRET:-gmail-token}"
GMAIL_CLIENT_SECRET="${GMAIL_CLIENT_SECRET:-gmail-oauth-client}"

IMAGE="gcr.io/${GCP_PROJECT}/${JOB_NAME}:latest"
JOB_SA="recruiter-scan-job@${GCP_PROJECT}.iam.gserviceaccount.com"
SCHEDULER_SA="recruiter-scan-scheduler@${GCP_PROJECT}.iam.gserviceaccount.com"
RUN_URI="https://${GCP_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${GCP_PROJECT}/jobs/${JOB_NAME}:run"

gcloud config set project "$GCP_PROJECT"

echo "==> Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  gmail.googleapis.com \
  containerregistry.googleapis.com \
  --project="$GCP_PROJECT"

echo "==> GCS bucket..."
if ! gsutil ls -b "gs://${GCS_BUCKET}" &>/dev/null; then
  gsutil mb -p "$GCP_PROJECT" -l "$GCP_REGION" -b on "gs://${GCS_BUCKET}"
fi

echo "==> Service accounts..."
if ! gcloud iam service-accounts describe "$JOB_SA" --project="$GCP_PROJECT" &>/dev/null; then
  gcloud iam service-accounts create recruiter-scan-job \
    --project="$GCP_PROJECT" \
    --display-name="Recruiter scan Cloud Run Job"
fi
if ! gcloud iam service-accounts describe "$SCHEDULER_SA" --project="$GCP_PROJECT" &>/dev/null; then
  gcloud iam service-accounts create recruiter-scan-scheduler \
    --project="$GCP_PROJECT" \
    --display-name="Scheduler for recruiter scan job"
fi

gsutil iam ch "serviceAccount:${JOB_SA}:objectAdmin" "gs://${GCS_BUCKET}" 2>/dev/null || \
gsutil iam ch "serviceAccount:${JOB_SA}:roles/storage.objectAdmin" "gs://${GCS_BUCKET}"

gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
  --member="serviceAccount:${JOB_SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --quiet

gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
  --member="serviceAccount:${SCHEDULER_SA}" \
  --role="roles/run.developer" \
  --quiet

echo "==> Building image (Cloud Build)..."
gcloud builds submit "$ROOT" \
  --project="$GCP_PROJECT" \
  --tag="$IMAGE" \
  --quiet

ENV_VARS="JOB_MODE=cloud,GCS_BUCKET=${GCS_BUCKET}"
if [[ -n "${GMAIL_QUERY:-}" ]]; then
  ENV_VARS="${ENV_VARS},GMAIL_QUERY=${GMAIL_QUERY}"
fi
if [[ -n "${SCAN_MAX_RESULTS:-}" ]]; then
  ENV_VARS="${ENV_VARS},SCAN_MAX_RESULTS=${SCAN_MAX_RESULTS}"
fi
if [[ -n "${SCAN_MIN_SCORE:-}" ]]; then
  ENV_VARS="${ENV_VARS},SCAN_MIN_SCORE=${SCAN_MIN_SCORE}"
fi

SECRET_FLAGS="GMAIL_CREDENTIALS_JSON=${GMAIL_CLIENT_SECRET}:latest,GMAIL_TOKEN_JSON=${GMAIL_TOKEN_SECRET}:latest"

echo "==> Deploying Cloud Run Job..."
RUN_JOBS="gcloud alpha run jobs"
if $RUN_JOBS describe "$JOB_NAME" --region="$GCP_REGION" --project="$GCP_PROJECT" &>/dev/null; then
  $RUN_JOBS update "$JOB_NAME" \
    --project="$GCP_PROJECT" \
    --region="$GCP_REGION" \
    --image="$IMAGE" \
    --service-account="$JOB_SA" \
    --set-env-vars="$ENV_VARS" \
    --set-secrets="$SECRET_FLAGS" \
    --max-retries=1 \
    --task-timeout=5m \
    --memory=512Mi \
    --cpu=1
else
  $RUN_JOBS create "$JOB_NAME" \
    --project="$GCP_PROJECT" \
    --region="$GCP_REGION" \
    --image="$IMAGE" \
    --service-account="$JOB_SA" \
    --set-env-vars="$ENV_VARS" \
    --set-secrets="$SECRET_FLAGS" \
    --max-retries=1 \
    --task-timeout=5m \
    --memory=512Mi \
    --cpu=1
fi

echo "==> Cloud Scheduler (${SCHEDULE_CRON}, ${SCHEDULE_TIMEZONE})..."
SCHEDULER_PY="${ROOT}/cloud/create_scheduler.py"
if [[ -f "$SCHEDULER_PY" ]]; then
  if [[ -x "${ROOT}/.venv/bin/python" ]]; then
    "${ROOT}/.venv/bin/python" "$SCHEDULER_PY"
  else
    python3 "$SCHEDULER_PY"
  fi
else
  gcloud alpha scheduler jobs create http "$SCHEDULER_NAME" \
    --project="$GCP_PROJECT" \
    --location="$GCP_REGION" \
    --schedule="$SCHEDULE_CRON" \
    --time-zone="$SCHEDULE_TIMEZONE" \
    --uri="$RUN_URI" \
    --http-method=POST \
    --oauth-service-account-email="$SCHEDULER_SA" \
    --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform" \
    --description="Trigger recruiter Gmail scan Cloud Run Job"
fi

echo ""
echo "Deployed."
echo "  Job:       ${JOB_NAME} (${GCP_REGION})"
echo "  Image:     ${IMAGE}"
echo "  Bucket:    gs://${GCS_BUCKET}/inbox/recruiter/"
echo "  Schedule:  ${SCHEDULE_CRON} ${SCHEDULE_TIMEZONE} (${SCHEDULER_NAME})"
echo ""
echo "One-time: run cloud/setup_secrets.sh if you have not uploaded OAuth tokens yet."
echo "Test now:  gcloud alpha run jobs execute ${JOB_NAME} --region=${GCP_REGION} --wait"
echo "Pull local: GCS_BUCKET=${GCS_BUCKET} python sync_gcs_inbox.py"
