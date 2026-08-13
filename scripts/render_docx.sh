#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 input.html [output.docx]" >&2
  exit 1
}

[[ $# -lt 1 || $# -gt 2 ]] && usage

root="$(cd "$(dirname "$0")/.." && pwd)"
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

venv="$root/scripts/.venv"
python="$venv/bin/python"
render_py="$root/scripts/render_docx.py"

if [[ ! -x "$python" ]] || ! "$python" -c "import html2docx" 2>/dev/null; then
  echo "Setting up scripts/.venv for DOCX export..." >&2
  python3 -m venv "$venv"
  "$venv/bin/pip" install -q -r "$root/scripts/requirements.txt"
fi

"$python" "$render_py" "$html" "$docx"
