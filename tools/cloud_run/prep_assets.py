"""Interview prep HTML discovery — bundled in container or repo, stored in GCS."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import gcs_apps

PREP_SLUG_SOURCES: dict[str, list[str]] = {
    "ltimindtree": ["ltimindtree", "paramount"],
    "ustechsolutions": ["nextera"],
    "ustech": ["nextera"],
}

PREP_FILES = (
    ("prep.html", "{slug}.html", "Prep guide"),
    ("prep_cram.html", "{slug}_cram.html", "Cram sheet"),
)
CHEAT_FILE = ("interview_cheat_sheet.html", "interview_cheat_sheet.html", "Cheat sheet")


def bundled_prep_dir() -> Path:
    for candidate in (
        Path(os.environ.get("INTERVIEW_PREP_DIR", "")),
        Path("/app/interview/prep"),
        Path(__file__).resolve().parents[2] / "interview" / "prep",
    ):
        if candidate.is_dir():
            return candidate
    return Path(__file__).resolve().parents[2] / "interview" / "prep"


def prep_source_slugs(slug: str, meta: dict | None = None) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    if meta:
        explicit = str(meta.get("prep_slug") or "").strip()
        if explicit and explicit not in seen:
            seen.add(explicit)
            ordered.append(explicit)
    for candidate in [slug, *PREP_SLUG_SOURCES.get(slug, [])]:
        if candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def discover_interview_prep(slug: str, meta: dict | None = None) -> list[dict[str, str]]:
    prep_dir = bundled_prep_dir()
    items: list[dict[str, str]] = []
    seen: set[str] = set()

    for source_slug in prep_source_slugs(slug, meta):
        for dest_name, src_pattern, label in PREP_FILES:
            if dest_name in seen:
                continue
            src = prep_dir / src_pattern.format(slug=source_slug)
            gcs_path = f"{gcs_apps.APPS_PREFIX}/{slug}/{dest_name}"
            if src.is_file() or gcs_apps.download_text(gcs_path):
                seen.add(dest_name)
                items.append({"file": dest_name, "label": label})

    cheat_dest, _, cheat_label = CHEAT_FILE
    if cheat_dest not in seen:
        gcs_cheat = f"{gcs_apps.APPS_PREFIX}/{slug}/{cheat_dest}"
        if gcs_apps.download_text(gcs_cheat):
            items.append({"file": cheat_dest, "label": cheat_label})
    return items


def read_prep_file(slug: str, filename: str, meta: dict | None = None) -> str | None:
    allowed = {item["file"] for item in discover_interview_prep(slug, meta)}
    if filename not in allowed and filename not in {d for d, _, _ in PREP_FILES} | {CHEAT_FILE[0]}:
        return None

    gcs_path = f"{gcs_apps.APPS_PREFIX}/{slug}/{filename}"
    text = gcs_apps.download_text(gcs_path)
    if text:
        return text

    prep_dir = bundled_prep_dir()
    for source_slug in prep_source_slugs(slug, meta):
        if filename == "prep.html":
            src = prep_dir / f"{source_slug}.html"
        elif filename == "prep_cram.html":
            src = prep_dir / f"{source_slug}_cram.html"
        else:
            src = None
        if src and src.is_file():
            content = src.read_text(encoding="utf-8")
            gcs_apps.upload_application_file(slug, filename, content, "text/html; charset=utf-8")
            return content
    return None


def ensure_prep_in_gcs(slug: str, meta: dict | None = None) -> list[dict[str, str]]:
    """Upload bundled prep HTML to GCS if missing; return discover list."""
    prep_dir = bundled_prep_dir()
    for source_slug in prep_source_slugs(slug, meta):
        for dest_name, src_pattern, _label in PREP_FILES:
            gcs_path = f"{gcs_apps.APPS_PREFIX}/{slug}/{dest_name}"
            if gcs_apps.download_text(gcs_path):
                continue
            src = prep_dir / src_pattern.format(slug=source_slug)
            if src.is_file():
                gcs_apps.upload_application_file(
                    slug,
                    dest_name,
                    src.read_text(encoding="utf-8"),
                    "text/html; charset=utf-8",
                )
    return discover_interview_prep(slug, meta)
