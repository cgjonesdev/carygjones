#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
port="${1:-8080}"

echo "Serving portfolio at http://localhost:${port}"
echo "Add your photo to website/headshot.jpg"
exec python3 -m http.server "$port" --directory "$root/website"
