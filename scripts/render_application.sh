#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 company_slug" >&2
  exit 1
fi

slug="$1"
root="$(cd "$(dirname "$0")/.." && pwd)"
render="$root/scripts/render_pdf.sh"
app="$root/applications/$slug"

resume_html="$app/resume.html"
cover_html="$app/cover_letter.html"

if [[ ! -d "$app" ]]; then
  echo "Error: application directory not found: $app" >&2
  exit 1
fi

if [[ ! -f "$resume_html" ]]; then
  echo "Error: expected file not found: $resume_html" >&2
  exit 1
fi

"$render" "$resume_html" "$app/resume.pdf"

if [[ -f "$cover_html" ]]; then
  "$render" "$cover_html" "$app/cover_letter.pdf"
else
  echo "Note: no cover letter found at $cover_html" >&2
fi

gmail_python="$root/tools/gmail/.venv/bin/python"
gmail_reply="$root/tools/gmail/generate_recruiter_reply.py"
if [[ -f "$gmail_reply" ]]; then
  if [[ -x "$gmail_python" ]]; then
    "$gmail_python" "$gmail_reply" "$slug"
  else
    python3 "$gmail_reply" "$slug"
  fi
fi
