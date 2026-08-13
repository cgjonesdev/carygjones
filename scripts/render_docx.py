#!/usr/bin/env python3
"""Convert application HTML to DOCX without macOS textutil (sandbox-safe)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from html2docx import html2docx


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path, help="Input HTML file")
    parser.add_argument("docx", type=Path, nargs="?", help="Output DOCX (default: same name .docx)")
    args = parser.parse_args()

    html_path = args.html.resolve()
    if not html_path.is_file():
        print(f"Error: HTML file not found: {html_path}", file=sys.stderr)
        return 1

    docx_path = args.docx.resolve() if args.docx else html_path.with_suffix(".docx")

    html = html_path.read_text(encoding="utf-8")
    buf = html2docx(html, title=html_path.stem)
    docx_path.write_bytes(buf.getvalue())
    print(f"Wrote {docx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
