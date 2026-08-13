#!/usr/bin/env python3
"""Normalize cover_letter.html files in applications/ (block sender lines, left-align headers)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help="cover_letter.html paths or application slugs (default: all applications)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report files that would change without writing",
    )
    args = parser.parse_args()

    root = repo_root()
    cloud_run = root / "tools" / "cloud_run"
    if str(cloud_run) not in sys.path:
        sys.path.insert(0, str(cloud_run))
    from cover_letter_html import normalize_cover_letter_html

    targets: list[Path] = []
    if args.paths:
        for item in args.paths:
            path = Path(item)
            if path.is_file():
                targets.append(path)
                continue
            slug = item.strip("/")
            targets.append(root / "applications" / slug / "cover_letter.html")
    else:
        targets = sorted((root / "applications").glob("*/cover_letter.html"))

    changed = 0
    missing = 0
    for path in targets:
        if not path.is_file():
            missing += 1
            print(f"skip missing: {path}", file=sys.stderr)
            continue
        original = path.read_text(encoding="utf-8")
        normalized = normalize_cover_letter_html(original)
        if normalized == original:
            continue
        changed += 1
        rel = path.relative_to(root)
        if args.dry_run:
            print(f"would update {rel}")
        else:
            path.write_text(normalized, encoding="utf-8")
            print(f"updated {rel}")

    print(f"done: {changed} updated, {missing} missing, {len(targets)} checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
