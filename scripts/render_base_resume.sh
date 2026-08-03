#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
html="$root/base/cary_jones_resume.html"

if [[ ! -f "$html" ]]; then
  echo "Error: base resume not found: $html" >&2
  exit 1
fi

"$root/scripts/render_pdf.sh" "$html"
"$root/scripts/render_docx.sh" "$html"
