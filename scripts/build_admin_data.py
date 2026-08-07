#!/usr/bin/env python3
"""Build static admin dashboard data from local applications/ and optional GCS sync."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _cloud_run_path() -> Path:
    return repo_root() / "tools" / "cloud_run"


def display_match_score(meta: dict) -> int | None:
    cloud_run = _cloud_run_path()
    if str(cloud_run) not in sys.path:
        sys.path.insert(0, str(cloud_run))
    from location_score import display_match_score as _display

    return _display(meta)


def gmail_url(meta: dict) -> str | None:
    se = meta.get("source_email") or {}
    if isinstance(se, dict):
        mid = se.get("message_id")
        if mid:
            return f"https://mail.google.com/mail/u/0/#inbox/{mid}"
    return None


def build_links(slug: str, meta: dict, *, pages_base: str) -> list[dict[str, str]]:
    apply_url = meta.get("apply_url")
    interview_url = meta.get("interview_url")
    g_url = gmail_url(meta)
    app_base = f"{pages_base}/app.html?slug={slug}"
    links: list[dict[str, str]] = []
    if apply_url:
        links.append({"label": "Apply", "url": apply_url})
    if interview_url:
        links.append({"label": "Interview", "url": interview_url})
    if g_url:
        links.append({"label": "Gmail", "url": g_url})
    links.append({"label": "Resume", "url": f"{app_base}&doc=resume"})
    links.append({"label": "Cover", "url": f"{app_base}&doc=cover"})
    return links


def copy_app_assets(slug: str, app_dir: Path, dest_apps: Path) -> None:
    dest = dest_apps / slug
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("resume.html", "cover_letter.html", "jd.txt", "resume.pdf", "cover_letter.pdf", "resume.docx", "cover_letter.docx"):
        src = app_dir / name
        if src.is_file():
            shutil.copy2(src, dest / name)


    return 0


def write_admin_config(
    *,
    api_base: str = "",
    pages_base: str = ".",
    repo_base: str = "https://github.com/cgjonesdev/carygjones/tree/main/applications",
    admin_password: str = "",
) -> Path:
    admin_dir = repo_root() / "website" / "admin"
    admin_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "apiBase": api_base.rstrip("/"),
        "pagesBase": pages_base,
        "repoBase": repo_base,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    if admin_password:
        payload["passwordHash"] = hashlib.sha256(admin_password.encode("utf-8")).hexdigest()
    out = admin_dir / "config.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages-base",
        default=".",
        help="URL prefix for admin pages (default: . for relative links on Pages)",
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("ADMIN_API_BASE_URL", "").strip(),
        help="Cloud Run admin API URL (or set ADMIN_API_BASE_URL env var)",
    )
    parser.add_argument(
        "--admin-password",
        default=os.environ.get("ADMIN_PASSWORD", "").strip(),
        help="Admin page password (or set ADMIN_PASSWORD env var; stored as SHA-256 hash only)",
    )
    args = parser.parse_args()

    root = repo_root()
    apps_dir = root / "applications"
    admin_data = root / "website" / "admin" / "data"
    admin_apps = root / "website" / "admin" / "apps"
    admin_data.mkdir(parents=True, exist_ok=True)
    if admin_apps.exists():
        shutil.rmtree(admin_apps)
    admin_apps.mkdir(parents=True)

    rows: list[dict] = []
    for meta_path in sorted(apps_dir.glob("*/meta.json")):
        slug = meta_path.parent.name
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"skip invalid json: {meta_path}", file=sys.stderr)
            continue
        copy_app_assets(slug, meta_path.parent, admin_apps)
        rows.append(
            {
                "slug": slug,
                "company": meta.get("company"),
                "role": meta.get("role"),
                "location": meta.get("location"),
                "match_score": display_match_score(meta),
                "status": meta.get("status"),
                "updated": meta.get("updated"),
                "apply_url": meta.get("apply_url"),
                "apply_method": meta.get("apply_method"),
                "gmail_draft_id": meta.get("gmail_draft_id"),
                "interview_url": meta.get("interview_url"),
                "gmail_url": gmail_url(meta),
                "links": build_links(slug, meta, pages_base=args.pages_base),
            }
        )

    rows.sort(
        key=lambda r: (
            r.get("match_score") if r.get("match_score") is not None else -1,
            r.get("updated") or "",
            r.get("slug") or "",
        ),
        reverse=True,
    )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "applications": rows,
        "count": len(rows),
    }
    out = admin_data / "applications.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(rows)} applications)")
    print(f"Copied HTML assets to {admin_apps}/")

    cfg_path = write_admin_config(
        api_base=args.api_base,
        pages_base=args.pages_base,
        admin_password=args.admin_password,
    )
    if args.api_base:
        print(f"Wrote {cfg_path} (apiBase={args.api_base})")
    else:
        print(f"Wrote {cfg_path} (apiBase empty — set GitHub repo variable ADMIN_API_BASE_URL for Pages deploy)")
    if args.admin_password:
        print("Wrote passwordHash to config.json (from ADMIN_PASSWORD)")
    else:
        print("No ADMIN_PASSWORD — admin page will not require login until secret is set")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
