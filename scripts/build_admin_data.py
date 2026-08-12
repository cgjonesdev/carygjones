#!/usr/bin/env python3
"""Build static admin dashboard data from local applications/ and optional GCS sync."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
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
    links.append({"label": "Prep", "url": f"{app_base}#interview-prep"})
    return links


PREP_SLUG_SOURCES: dict[str, list[str]] = {
    "ltimindtree": ["ltimindtree", "paramount"],
}


def prep_source_slugs(slug: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for candidate in [slug, *PREP_SLUG_SOURCES.get(slug, [])]:
        if candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def discover_interview_prep(slug: str) -> list[dict[str, str]]:
    root = repo_root()
    prep_dir = root / "interview" / "prep"
    app_dir = root / "applications" / slug
    items: list[dict[str, str]] = []
    seen_files: set[str] = set()

    for source_slug in prep_source_slugs(slug):
        candidates = [
            (prep_dir / f"{source_slug}.html", "prep.html", "Prep guide"),
            (prep_dir / f"{source_slug}_cram.html", "prep_cram.html", "Cram sheet"),
        ]
        for src, dest_name, label in candidates:
            if dest_name in seen_files or not src.is_file():
                continue
            seen_files.add(dest_name)
            items.append({"file": dest_name, "label": label})

    cheat = app_dir / "interview_cheat_sheet.html"
    if cheat.is_file() and "interview_cheat_sheet.html" not in seen_files:
        items.append({"file": "interview_cheat_sheet.html", "label": "Cheat sheet"})
    return items


def copy_app_assets(slug: str, app_dir: Path, dest_apps: Path) -> None:
    dest = dest_apps / slug
    dest.mkdir(parents=True, exist_ok=True)
    for name in (
        "resume.html",
        "cover_letter.html",
        "jd.txt",
        "freelancer_bid.txt",
        "craigslist_reply.txt",
        "reply_email.txt",
        "resume.pdf",
        "cover_letter.pdf",
        "resume.docx",
        "cover_letter.docx",
    ):
        src = app_dir / name
        if src.is_file():
            shutil.copy2(src, dest / name)

    prep_dir = repo_root() / "interview" / "prep"
    copied_prep: set[str] = set()
    for source_slug in prep_source_slugs(slug):
        for src_name, dest_name in (
            (f"{source_slug}.html", "prep.html"),
            (f"{source_slug}_cram.html", "prep_cram.html"),
        ):
            if dest_name in copied_prep:
                continue
            src = prep_dir / src_name
            if src.is_file():
                shutil.copy2(src, dest / dest_name)
                copied_prep.add(dest_name)

    cheat = app_dir / "interview_cheat_sheet.html"
    if cheat.is_file():
        shutil.copy2(cheat, dest / "interview_cheat_sheet.html")


def sync_applications_from_gcs(root: Path) -> None:
    sync_script = root / "tools" / "gmail" / "sync_gcs_inbox.py"
    if not sync_script.is_file():
        raise FileNotFoundError(f"missing {sync_script}")
    subprocess.run(
        [sys.executable, str(sync_script), "--applications"],
        cwd=str(root),
        check=True,
    )


def export_protocol_run_from_gcs(admin_data: Path) -> None:
    cloud_run = _cloud_run_path()
    if str(cloud_run) not in sys.path:
        sys.path.insert(0, str(cloud_run))
    import gcs_apps

    raw = gcs_apps.download_text(f"{gcs_apps.STATE_PREFIX}/latest_protocol_run.json")
    if not raw:
        return
    (admin_data / "latest_protocol_run.json").write_text(raw, encoding="utf-8")
    print(f"Wrote {admin_data / 'latest_protocol_run.json'} from GCS")


def _admin_api_get(api_base: str, admin_key: str, path: str) -> dict | None:
    url = f"{api_base.rstrip('/')}{path}"
    req = urllib.request.Request(url, headers={"X-Admin-Key": admin_key})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(
            f"Admin API GET {path} failed ({exc.code}): {body[:300]}",
            file=sys.stderr,
        )
        if exc.code == 401:
            print(
                "Hint: Cloud Run secret admin-api-key must match GitHub secret ADMIN_PASSWORD "
                "(same value you use to sign in on Pages).",
                file=sys.stderr,
            )
        return None
    except Exception as exc:
        print(f"Admin API GET {path} failed: {exc}", file=sys.stderr)
        return None


def export_from_admin_api(
    admin_data: Path,
    *,
    api_base: str,
    admin_password: str,
) -> tuple[int, int]:
    """Overwrite static snapshot from live Cloud Run (GCS-backed) data."""
    apps_payload = _admin_api_get(api_base, admin_password, "/api/applications")
    if not apps_payload:
        return 0, 0

    apps = apps_payload.get("applications") or []
    out = admin_data / "applications.json"
    out.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source": "cloud_run_api",
                "applications": apps,
                "count": len(apps),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {out} from Cloud Run API ({len(apps)} applications)")

    protocol = _admin_api_get(api_base, admin_password, "/api/protocols/latest")
    if protocol and not protocol.get("empty"):
        proto_out = admin_data / "latest_protocol_run.json"
        proto_out.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {proto_out} from Cloud Run API")

    return len(apps), 0


def write_admin_config(
    *,
    api_base: str = "",
    pages_base: str = ".",
    repo_base: str = "https://github.com/cgjonesdev/carygjones/tree/main/applications",
    admin_password: str = "",
) -> Path:
    admin_dir = repo_root() / "website" / "admin"
    admin_dir.mkdir(parents=True, exist_ok=True)
    out = admin_dir / "config.json"
    existing_api_base = ""
    if out.exists():
        try:
            existing = json.loads(out.read_text(encoding="utf-8"))
            existing_api_base = str(existing.get("apiBase") or "").strip()
        except (json.JSONDecodeError, OSError):
            pass
    resolved_api_base = (api_base or existing_api_base).rstrip("/")
    payload = {
        "apiBase": resolved_api_base,
        "pagesBase": pages_base,
        "repoBase": repo_base,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    if admin_password:
        payload["passwordHash"] = hashlib.sha256(admin_password.encode("utf-8")).hexdigest()
    out = admin_dir / "config.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out


def build_application_row(slug: str, meta: dict, *, pages_base: str) -> dict:
    return {
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
        "interview_prep": discover_interview_prep(slug),
        "gmail_url": gmail_url(meta),
        "links": build_links(slug, meta, pages_base=pages_base),
    }


def refresh_single_application(
    slug: str,
    *,
    pages_base: str = ".",
) -> tuple[bool, str]:
    """Fast path: update one row in applications.json and copy that app's assets."""
    root = repo_root()
    meta_path = root / "applications" / slug / "meta.json"
    if not meta_path.is_file():
        return False, f"missing applications/{slug}/meta.json"

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"invalid json in {meta_path}: {exc}"

    admin_data = root / "website" / "admin" / "data"
    admin_apps = root / "website" / "admin" / "apps"
    admin_data.mkdir(parents=True, exist_ok=True)
    admin_apps.mkdir(parents=True, exist_ok=True)

    copy_app_assets(slug, meta_path.parent, admin_apps)
    row = build_application_row(slug, meta, pages_base=pages_base)

    apps_json = admin_data / "applications.json"
    payload: dict
    if apps_json.is_file():
        payload = json.loads(apps_json.read_text(encoding="utf-8"))
        rows = payload.get("applications") or []
        rows = [r for r in rows if r.get("slug") != slug]
        rows.append(row)
    else:
        rows = [row]

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
    apps_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return True, f"Updated {apps_json} ({slug})"


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
    parser.add_argument(
        "--slug",
        default="",
        help="Fast path: refresh only this application in admin data (skip full rebuild)",
    )
    args = parser.parse_args()

    if args.slug:
        ok, message = refresh_single_application(args.slug, pages_base=args.pages_base)
        if not ok:
            print(message, file=sys.stderr)
            return 1
        print(message)
        return 0

    root = repo_root()
    if os.environ.get("SYNC_GCS_BEFORE_BUILD", "0") == "1":
        try:
            sync_applications_from_gcs(root)
            print("Synced applications/ from GCS")
        except Exception as exc:
            print(f"GCS sync skipped: {exc}", file=sys.stderr)

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
        rows.append(build_application_row(slug, meta, pages_base=args.pages_base))

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
    print(f"Wrote {out} ({len(rows)} applications from repo)")
    print(f"Copied HTML assets to {admin_apps}/")

    if args.api_base and args.admin_password:
        api_count, _ = export_from_admin_api(
            admin_data,
            api_base=args.api_base,
            admin_password=args.admin_password,
        )
        if api_count == 0:
            print(
                "WARNING: Cloud Run export failed — Pages will only show repo applications "
                "until admin-api-key matches ADMIN_PASSWORD.",
                file=sys.stderr,
            )
    else:
        try:
            export_protocol_run_from_gcs(admin_data)
        except Exception as exc:
            print(f"Protocol run export skipped: {exc}", file=sys.stderr)

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
