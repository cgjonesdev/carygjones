#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 input.html [output.docx]" >&2
  exit 1
}

[[ $# -lt 1 || $# -gt 2 ]] && usage

html="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
if [[ ! -f "$html" ]]; then
  echo "Error: HTML file not found: $1" >&2
  exit 1
fi

if [[ $# -eq 2 ]]; then
  docx="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
else
  docx="${html%.html}.docx"
fi

if ! command -v textutil >/dev/null 2>&1; then
  echo "Error: textutil not found (macOS required for DOCX export)" >&2
  exit 1
fi

textutil -convert docx -output "$docx" "$html"
echo "Wrote $docx"
