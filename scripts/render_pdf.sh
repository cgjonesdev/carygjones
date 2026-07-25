#!/usr/bin/env bash
set -euo pipefail

CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

usage() {
  echo "Usage: $0 input.html [output.pdf]" >&2
  exit 1
}

[[ $# -lt 1 || $# -gt 2 ]] && usage

html="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
if [[ ! -f "$html" ]]; then
  echo "Error: HTML file not found: $1" >&2
  exit 1
fi

if [[ $# -eq 2 ]]; then
  pdf="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
else
  pdf="${html%.html}.pdf"
fi

if [[ ! -x "$CHROME" ]]; then
  echo "Error: Chrome not found at $CHROME" >&2
  exit 1
fi

"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$pdf" "file://$html"

echo "Wrote $pdf"
