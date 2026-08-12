"""Generate an application from manually pasted JD text."""

from __future__ import annotations

import json
import re
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import gcs_apps
from openai_tailor import generate_application, score_jd, slugify
from render_assets import render_application_files

_GMAIL_DIR = Path(__file__).resolve().parents[2] / "gmail"
if _GMAIL_DIR.is_dir() and str(_GMAIL_DIR) not in sys.path:
    sys.path.insert(0, str(_GMAIL_DIR))
from text_clean import clean_jd_text  # noqa: E402


def _extract_apply_url(body: str, apply_url: str | None) -> str | None:
    if apply_url:
        return apply_url.strip()
    for match in re.finditer(r"https?://[^\s<>\"']+", body):
        url = match.group(0).rstrip(").,]")
        host = urlparse(url).netloc.lower()
        if any(
            x in host
            for x in (
                "greenhouse.io",
                "ashbyhq.com",
                "jobs.ashbyhq.com",
                "linkedin.com/jobs",
                "indeed.com",
                "lever.co",
            )
        ):
            return url
    return None


def _merge_meta(
    generated: dict[str, Any],
    score_data: dict[str, Any],
    apply_url: str | None,
    *,
    source: str,
) -> dict[str, Any]:
    meta = generated.get("meta_json") or {}
    if not isinstance(meta, dict):
        meta = {}
    today = date.today().isoformat()
    slug_source = score_data.get("slug") or slugify(score_data.get("company") or "company")
    meta.setdefault("company", score_data.get("company"))
    meta.setdefault("client", None)
    meta.setdefault("role", score_data.get("role"))
    meta.setdefault("location", score_data.get("location"))
    meta.setdefault("match_score", score_data.get("match_score"))
    if score_data.get("raw_match_score") is not None:
        meta.setdefault("raw_match_score", score_data.get("raw_match_score"))
    meta.setdefault("status", "ready")
    meta.setdefault("created", today)
    meta.setdefault("updated", today)
    meta.setdefault("salary", score_data.get("salary"))
    meta.setdefault("styling_notes", score_data.get("styling_notes"))
    meta.setdefault("notes", f"Generated from manual JD ({source}) on {today}.")
    if apply_url:
        meta.setdefault("apply_url", apply_url)
    meta["_slug_hint"] = slug_source
    return meta


def run_manual_jd(
    jd_text: str,
    *,
    apply_url: str | None = None,
    subject: str = "Manual JD entry",
    force: bool = False,
) -> dict[str, Any]:
    """Score pasted JD and generate application files when above threshold."""
    jd_text = clean_jd_text(jd_text.strip())
    if len(jd_text) < 80:
        return {"phase": "manual_jd", "error": "JD text too short (need at least 80 characters)."}

    apply_url = _extract_apply_url(jd_text, apply_url)
    score_data = score_jd(jd_text, subject=subject, apply_url=apply_url)
    score = int(score_data.get("match_score") or 0)
    slug = slugify(score_data.get("slug") or score_data.get("company") or "company")

    if slug in gcs_apps.list_application_slugs() and not force:
        return {
            "phase": "manual_jd",
            "skipped": True,
            "slug": slug,
            "score": score,
            "reason": "application slug already exists (use force=true to overwrite meta/files)",
        }

    if not score_data.get("should_generate") and not force:
        return {
            "phase": "manual_jd",
            "skipped": True,
            "slug": slug,
            "score": score,
            "reason": "below match threshold",
            "score_data": score_data,
        }

    files = generate_application(jd_text, score_data, apply_url=apply_url)
    meta = _merge_meta(files, score_data, apply_url, source="admin dashboard")
    slug = slugify(meta.pop("_slug_hint", slug))

    jd_txt = files.get("jd_txt") or jd_text
    resume_html = files.get("resume_html") or ""
    cover_html = files.get("cover_letter_html") or ""
    reply_txt = files.get("reply_email_txt") or ""

    if not resume_html or not cover_html:
        return {"phase": "manual_jd", "error": "OpenAI returned empty resume or cover letter HTML"}

    gcs_apps.upload_application_file(slug, "jd.txt", jd_txt, "text/plain; charset=utf-8")
    gcs_apps.upload_application_file(
        slug,
        "meta.json",
        json.dumps(meta, indent=2) + "\n",
        "application/json",
    )
    gcs_apps.upload_application_file(slug, "resume.html", resume_html, "text/html; charset=utf-8")
    gcs_apps.upload_application_file(
        slug, "cover_letter.html", cover_html, "text/html; charset=utf-8"
    )
    if reply_txt:
        gcs_apps.upload_application_file(
            slug, "reply_email.txt", reply_txt, "text/plain; charset=utf-8"
        )

    with tempfile.TemporaryDirectory() as tmp:
        paths = render_application_files(resume_html, cover_html, Path(tmp))
        for name, path in paths.items():
            if name.endswith(".html"):
                continue
            data = path.read_bytes()
            ctype = (
                "application/pdf"
                if name.endswith(".pdf")
                else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            gcs_apps.upload_application_file(slug, name, data, ctype)

    return {
        "phase": "manual_jd",
        "generated": {
            "slug": slug,
            "score": score,
            "company": meta.get("company"),
            "role": meta.get("role"),
            "apply_url": meta.get("apply_url") or apply_url,
        },
    }
