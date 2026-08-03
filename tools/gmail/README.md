# Gmail recruiter scanner

Read-only scan of `cgjonesdev@gmail.com` (or whichever account you authorize) for recruiter mail with job-description signals.

**Agent instructions:** `tools/gmail/.prompt` (GCloud email parser agent). Root `.prompt` is for new JDs / tailored applications only.

## One-time Google setup (~5 min)

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (or reuse one) → **APIs & Services** → **Library** → enable **Gmail API**.
3. **APIs & Services** → **OAuth consent screen**:
   - User type: **External**
   - App name: anything (e.g. `job_search`)
   - Add your email under **Developer contact information**
   - Save
   - On the same screen, open **Audience** (or **Test users** on older UI)
   - Click **Add users** → add **`cgjonesdev@gmail.com`** exactly
   - Publishing status must stay **Testing** (not Production — verification takes weeks)
4. **Credentials** → **Create credentials** → **OAuth client ID** → **Desktop app**.
5. Download JSON → save as:

   `tools/gmail/credentials.json`

## Fix: `Error 403: access_denied` / "has not completed the Google verification process"

This is normal for personal projects. Google blocks everyone except **test users** you explicitly add.

1. Open [OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent) for your project.
2. Confirm **Publishing status** = **Testing** (not In production).
3. Go to **Audience** → **Test users** → **Add users**.
4. Add **`cgjonesdev@gmail.com`** (must match the account you sign in with).
5. Wait 1–2 minutes, then retry auth in an **incognito** window.
6. When Google asks "Choose an account", pick **cgjonesdev@gmail.com** only.

Still blocked?

- You created the OAuth client in a **different** GCP project than the consent screen — use one project for both.
- Browser is signed into a different Google account — sign out or use incognito.
- Delete stale token and retry:
  ```bash
  rm tools/gmail/token.json
  python scan_recruiter_mail.py
  ```

You do **not** need Google verification for personal use — Testing mode + test user is enough.

## Install & authorize

```bash
cd tools/gmail
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scan_recruiter_mail.py
```

First run opens a browser to sign in to Google. A `token.json` is saved locally for later runs.

## Usage

```bash
# Summary in terminal
python scan_recruiter_mail.py

# Save JSON payloads to inbox/recruiter/
python scan_recruiter_mail.py --save

# Custom Gmail query
python scan_recruiter_mail.py --query 'is:unread newer_than:7d subject:python'

# Full JSON stdout
python scan_recruiter_mail.py --json
```

## Recruiter reply flow

After rendering an application (`scripts/render_application.sh honor`), a `reply_email.txt` is generated automatically with resume/cover-letter bullets.

```bash
# Regenerate reply text only
python generate_recruiter_reply.py honor

# Tie reply to a scanned inbox message (subject + greeting)
python generate_recruiter_reply.py honor \
  --inbox-json ../../inbox/recruiter/senior-backend-engineer-honor_19fb74df.json

# Create Gmail draft with resume.pdf + cover_letter.pdf attached
python draft_recruiter_reply.py honor \
  --inbox-json ../../inbox/recruiter/senior-backend-engineer-honor_19fb74df.json

# Create drafts for every ready application with a human recruiter address
python draft_all_recruiter_replies.py
python draft_all_recruiter_replies.py --dry-run --verbose

# Send immediately (default is draft-only — review in Gmail first)
python draft_recruiter_reply.py honor --send --inbox-json ../../inbox/recruiter/....json
```

Link a source email in `applications/{slug}/meta.json` so you don't need `--inbox-json` every time:

```json
"source_email": {
  "message_id": "19fb74df...",
  "thread_id": "...",
  "subject": "Senior Backend Engineer @ Honor",
  "sender": "Indeed <noreply@indeedemail.com>"
}
```

**Draft scope:** Creating drafts requires `gmail.compose`. If you only authorized readonly before, delete `token.json` and run `draft_recruiter_reply.py` once to re-auth in the browser.

## Cloud Run (every 10 minutes)

Automated scanning on GCP: Cloud Scheduler → Cloud Run Job → Gmail → GCS bucket.

See **[cloud/README.md](cloud/README.md)** for deploy steps. Quick path:

```bash
cp cloud/config.env.example cloud/config.env   # set GCP_PROJECT, GCS_BUCKET
./cloud/setup_secrets.sh                        # OAuth → Secret Manager
./cloud/deploy.sh                               # job + */10 cron

# Pull new scans into this repo
GCS_BUCKET=your-bucket python sync_gcs_inbox.py
```

## Scoring

Messages get a score from sender patterns, subject keywords, and JD phrases (`responsibilities`, `requirements`, `job description`, etc.). Default `--min-score 3` filters noise.

## Security

- `credentials.json` and `token.json` are gitignored — never commit them.
- Scanning uses **readonly** Gmail access; draft creation adds **compose** (drafts only unless you pass `--send`).
