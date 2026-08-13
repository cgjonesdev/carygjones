"""Create a Gmail draft for an application stored in GCS."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import gcs_apps

_GMAIL_DIR = Path(__file__).resolve().parents[2] / "gmail"
if _GMAIL_DIR.is_dir() and str(_GMAIL_DIR) not in sys.path:
    sys.path.insert(0, str(_GMAIL_DIR))

from auth import SCOPES_COMPOSE, get_gmail_service  # noqa: E402
from draft_reply import draft_application  # noqa: E402
from reply_generator import write_reply_file  # noqa: E402

MANUAL_DRAFT_STATUSES = frozenset(
    {
        "ready",
        "application_in_progress",
        "applied",
        "waiting_on_response",
        "needs_rate_confirmation",
        "interview",
        "screening_interview_complete",
        "in_technical_interviews",
        "technical_interviews_complete",
        "in_final_interviews",
        "final_interviews_complete",
    }
)


def _ensure_rendered_pdfs(slug: str, app_dir: Path) -> str | None:
    """Render PDF attachments from HTML in GCS when missing."""
    resume_pdf = app_dir / "resume.pdf"
    cover_pdf = app_dir / "cover_letter.pdf"
    if resume_pdf.is_file() and cover_pdf.is_file():
        return None

    resume_html = app_dir / "resume.html"
    cover_html = app_dir / "cover_letter.html"
    if not resume_html.is_file() or not cover_html.is_file():
        missing = [p.name for p in (resume_pdf, cover_pdf) if not p.is_file()]
        return f"missing {', '.join(missing)} — generate application first"

    cloud_run = Path(__file__).resolve().parents[1]
    if str(cloud_run) not in sys.path:
        sys.path.insert(0, str(cloud_run))
    from render_assets import render_application_files

    render_application_files(
        resume_html.read_text(encoding="utf-8"),
        cover_html.read_text(encoding="utf-8"),
        app_dir,
    )

    for name, ctype in (
        ("resume.pdf", "application/pdf"),
        ("cover_letter.pdf", "application/pdf"),
        ("resume.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("cover_letter.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ):
        path = app_dir / name
        if path.is_file():
            gcs_apps.upload_application_file(slug, name, path.read_bytes(), ctype)

    if not resume_pdf.is_file() or not cover_pdf.is_file():
        missing = [p.name for p in (resume_pdf, cover_pdf) if not p.is_file()]
        return f"missing {', '.join(missing)} after render"
    return None


def _materialize_application(slug: str, root: Path) -> Path:
    meta = gcs_apps.load_app_meta(slug)
    if not meta:
        raise FileNotFoundError(f"Application not found: {slug}")

    app_dir = root / "applications" / slug
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    for filename in (
        "reply_email.txt",
        "resume.pdf",
        "cover_letter.pdf",
        "cover_letter.html",
        "resume.html",
    ):
        data = gcs_apps.download_bytes(f"{gcs_apps.APPS_PREFIX}/{slug}/{filename}")
        if data:
            (app_dir / filename).write_bytes(data)

    return app_dir


def _persist_meta_from_local(slug: str, root: Path) -> None:
    meta_path = root / "applications" / slug / "meta.json"
    if not meta_path.exists():
        return
    meta = json.loads(meta_path.read_text())
    gcs_apps.save_app_meta(slug, meta)


def run_gmail_draft(
    slug: str,
    *,
    regenerate: bool = False,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Build a Gmail draft reply with resume and cover letter attachments."""
    meta = gcs_apps.load_app_meta(slug)
    if not meta:
        return {"phase": "gmail_draft", "error": f"Application not found: {slug}"}

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        app_dir = _materialize_application(slug, root)

        if regenerate or not (app_dir / "reply_email.txt").exists():
            if not (app_dir / "cover_letter.html").exists():
                return {
                    "phase": "gmail_draft",
                    "error": "Missing cover_letter.html — regenerate application first.",
                }
            write_reply_file(slug, inbox_json=None, root=root)
            reply_text = (root / "applications" / slug / "reply_email.txt").read_text()
            gcs_apps.upload_application_file(
                slug,
                "reply_email.txt",
                reply_text,
                "text/plain; charset=utf-8",
            )
            _materialize_application(slug, root)

        try:
            service = None if dry_run else get_gmail_service(scopes=SCOPES_COMPOSE)
        except RuntimeError as exc:
            return {"phase": "gmail_draft", "error": str(exc)}

        render_err = _ensure_rendered_pdfs(slug, app_dir)
        if render_err:
            return {"phase": "gmail_draft", "error": render_err}

        result = draft_application(
            service,
            slug,
            regenerate=False,
            send=False,
            dry_run=dry_run,
            force=force,
            statuses=MANUAL_DRAFT_STATUSES,
            root=root,
        )

        if result.outcome in {"created", "sent"} and not dry_run:
            _persist_meta_from_local(slug, root)

        return {
            "phase": "gmail_draft",
            "slug": slug,
            "outcome": result.outcome,
            "detail": result.detail,
            "to_addr": result.to_addr,
            "subject": result.subject,
            "draft_id": result.draft_id,
        }
