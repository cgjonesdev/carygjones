# Cloud Run protocols pipeline

Runs the full job-search protocol stack without Cursor:

1. **Gmail scan** — new recruiter mail → `gs://{GCS_BUCKET}/inbox/recruiter/`
2. **Triage + generate** — OpenAI scores each inbox message; ≥80% matches get resume/cover letter HTML, PDF, DOCX → `gs://{GCS_BUCKET}/applications/{slug}/`
3. **LinkedIn** (optional) — search via Linked API when tokens are configured

State and run summaries: `gs://{GCS_BUCKET}/protocols/_state/`

## Prerequisites

- GCP project with billing (same as `tools/gmail/cloud/`)
- Gmail OAuth uploaded via `tools/gmail/cloud/setup_secrets.sh`
- OpenAI API key

## One-time setup

```bash
cd tools/cloud_run/cloud
cp config.env.example config.env
# edit GCP_PROJECT, GCP_REGION, GCS_BUCKET

# Gmail secrets (if not done)
cd ../../gmail/cloud && ./setup_secrets.sh

# OpenAI (+ optional LinkedIn) secrets
cd ../../cloud_run/cloud
OPENAI_API_KEY=sk-... ./setup_secrets.sh
```

Deploy Gmail scan first if you have not (`tools/gmail/cloud/deploy.sh`) — it creates the service account and bucket IAM.

## Deploy

From repo root:

```bash
cd tools/cloud_run/cloud
./deploy.sh
```

Build context is the **repo root** (Dockerfile copies `base/`, `website/`, `applications/weave/`, and `tools/gmail/`).

## Run manually

```bash
gcloud alpha run jobs execute run-protocols --region=us-west1 --wait
```

Skip phases with env vars on the job (re-deploy or override at execute time):

| Variable | Effect |
|----------|--------|
| `SKIP_GMAIL_SCAN=1` | Skip phase 1 |
| `SKIP_GENERATE=1` | Skip OpenAI generation |
| `SKIP_LINKEDIN=1` | Skip LinkedIn search |
| `SKIP_FREELANCER_SCAN=1` | Skip Freelancer scan (default on `run all`) |
| `FREELANCER_MATCH_THRESHOLD=70` | Minimum score to create bid folders |
| `FREELANCER_MAX_PER_RUN=5` | Cap new Freelancer applications per scan |
| `SKIP_CRAIGSLIST_SCAN=1` | Skip Craigslist gigs scan — LA Central, SF Bay Area, San Diego (default on `run all`) |
| `CRAIGSLIST_SEARCH_URL=…` | Override with a single Craigslist search URL (default: all three regions) |
| `CRAIGSLIST_MATCH_THRESHOLD=60` | Minimum score to create reply folders |
| `CRAIGSLIST_MAX_PER_RUN=5` | Cap new Craigslist applications per scan |
| `SKIP_INDEED_SCAN=1` | Skip Indeed job search (default on `run all`) |
| `INDEED_SEARCH_QUERY=python developer` | Indeed search keywords |
| `INDEED_SEARCH_LOCATION=Los Angeles, CA` | Indeed search location |
| `INDEED_MATCH_THRESHOLD=70` | Minimum score after location adjustment |
| `INDEED_MAX_PER_RUN=5` | Cap new Indeed applications per scan |
| `MAX_GENERATE_PER_RUN=5` | Cap new applications per run |
| `MATCH_THRESHOLD=80` | Minimum score to generate |

## Pull artifacts to your Mac

```bash
cd tools/gmail
GCS_BUCKET=your-bucket python sync_gcs_inbox.py --all
```

This updates `inbox/recruiter/` and `applications/` from GCS.

## Local test (optional)

```bash
cd tools/cloud_run
pip install -r requirements.txt -r ../gmail/requirements.txt
playwright install chromium

export GCS_BUCKET=your-bucket
export OPENAI_API_KEY=sk-...
# APP_ROOT defaults to tools/ when running from cloud_run/phases; for local runs:
export APP_ROOT=/path/to/job_search/tools
export ASSETS_DIR=/path/to/job_search

python run_protocols.py
```

## Architecture notes

- **GitHub Pages** can host a read-only dashboard; it cannot run this pipeline (needs secrets + OpenAI + Gmail).
- **LinkedIn Easy Apply** stays manual; cloud generates files and stores apply URLs in `meta.json`.
- LinkedIn phase uses workflow API: `POST /workflows` with `st.searchJobs`, then polls `GET /workflows/{id}` (not `/v1/jobs/search`).
- **Location scoring:** after OpenAI scoring, apply a server-side adjustment (`tools/cloud_run/location_score.py`):
  - **Remote** — anywhere; no penalty
  - **Onsite / hybrid** — **Los Angeles metro** or **SF Bay Area** only; no penalty
  - **Onsite / hybrid outside those metros** — `match_score × 0.1` (falls below the 80 generate threshold and ranks at the bottom of the admin table)
- **Applied status sync:** opens each tracked application’s LinkedIn job via `st.openJob` (up to `LINKEDIN_APPLIED_CHECK_LIMIT`, default 15) and marks `meta.json` `status: applied` when LinkedIn shows an applied signal. Linked API does not support the Job tracker Applied tab URL — that path was removed.

## Unified admin (dev = prod)

One Cloud Run **service** serves `/admin/` UI and `/api/*` — all application data lives in **GCS** (no separate local sync server).

| Environment | How to run | Data |
|-------------|------------|------|
| **Local dev** | `./scripts/serve_admin_local.sh` → uvicorn on `:8080` | Same GCS bucket as prod |
| **Production** | `tools/cloud_run/service/cloud/deploy.sh` | GCS |

Legacy split (static server + `:8765` sync): `ADMIN_LEGACY=1 ./scripts/serve_admin_local.sh`

**LLM in admin:** `POST /api/applications/{slug}/llm` (interview prep assistant). Requires `OPENAI_API_KEY` on the service.

**Generate one app:** `POST /api/applications/{slug}/generate` (GCS-only; works on Cloud Run and local unified API).

GitHub Pages can remain a read-only portfolio mirror; interactive admin should use the Cloud Run URL (or local unified API).

## Admin dashboard (legacy Pages + API split)

Static UI: `website/admin/` (deployed with GitHub Pages at `/admin/`).

| Feature | Where |
|---------|--------|
| Manual JD textarea | Admin UI → calls `POST /api/jd/manual` |
| Run Gmail / Generate / LinkedIn / Indeed / Freelancer / Craigslist / All | Admin UI → `POST /api/run/*` |
| Applications table + clickable links | Apply · Gmail · Resume · Cover |
| Application preview pages | `admin/app.html?slug=…` |

**Read-only on Pages:** tables load from `data/applications.json` (built by `scripts/build_admin_data.py` on deploy).

**Interactive mode:** set GitHub repo variable **`ADMIN_API_BASE_URL`** to your Cloud Run admin service URL (no trailing slash). The deploy workflow writes it into `website/admin/config.json` automatically.

```bash
# After deploying the admin API service:
gh variable set ADMIN_API_BASE_URL --body "https://job-search-admin-….run.app"
# Push to main or re-run "Deploy portfolio website"
```

Deploy the API service:

```bash
cd tools/cloud_run/service/cloud
./deploy.sh
```

If Cloud Run requires `ADMIN_API_KEY`, enter it once in the dashboard **Connection** panel (stored in your browser only — never commit it to GitHub).
