"""HTTP API for admin dashboard — protocol runs, manual JD, application browsing."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gcs_apps  # noqa: E402
from app_settings import apply_settings_update, settings_from_meta  # noqa: E402
from orchestrator import run_all, run_generate, run_gmail, run_linkedin, run_phases  # noqa: E402
from phases.gmail_draft import run_gmail_draft  # noqa: E402
from phases.manual_jd import run_manual_jd  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_STATIC = Path(
    os.environ.get("ADMIN_STATIC_DIR", REPO_ROOT / "website" / "admin")
)
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "ADMIN_CORS_ORIGINS",
        "https://cgjonesdev.github.io,http://localhost:8080,http://127.0.0.1:8080",
    ).split(",")
    if o.strip()
]


class ManualJdRequest(BaseModel):
    jd_text: str = Field(..., min_length=80)
    apply_url: str | None = None
    subject: str = "Manual JD entry"
    force: bool = False


class RunRequest(BaseModel):
    parallel: bool = False


class ApplicationSettingsUpdate(BaseModel):
    recruiter_email: str | None = None
    recruiter_name: str | None = None
    apply_url: str | None = None
    gmail_message_id: str | None = None
    email_subject: str | None = None
    status: str | None = None
    notes: str | None = None


class GmailDraftRequest(BaseModel):
    regenerate: bool = False
    force: bool = False
    dry_run: bool = False


def _require_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("ADMIN_API_KEY", "").strip()
    if not expected:
        return
    if x_admin_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Key")


def _gmail_url(meta: dict[str, Any]) -> str | None:
    se = meta.get("source_email") or {}
    if isinstance(se, dict):
        mid = se.get("message_id")
        if mid:
            return f"https://mail.google.com/mail/u/0/#inbox/{mid}"
    return None


def _application_row(slug: str, meta: dict[str, Any]) -> dict[str, Any]:
    apply_url = meta.get("apply_url")
    interview_url = meta.get("interview_url")
    gmail_url = _gmail_url(meta)
    app_base = f"app.html?slug={slug}"
    links = []
    if apply_url:
        links.append({"label": "Apply", "url": apply_url})
    if interview_url:
        links.append({"label": "Interview", "url": interview_url})
    if gmail_url:
        links.append({"label": "Gmail", "url": gmail_url})
    links.extend(
        [
            {"label": "Resume", "url": f"{app_base}&doc=resume"},
            {"label": "Cover", "url": f"{app_base}&doc=cover"},
            {"label": "JD", "url": f"{app_base}&doc=jd"},
            {"label": "Settings", "url": app_base},
        ]
    )
    return {
        "slug": slug,
        "company": meta.get("company"),
        "role": meta.get("role"),
        "location": meta.get("location"),
        "match_score": meta.get("match_score"),
        "status": meta.get("status"),
        "updated": meta.get("updated"),
        "apply_url": apply_url,
        "interview_url": interview_url,
        "gmail_url": gmail_url,
        "links": links,
    }


app = FastAPI(title="Job Search Admin API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/applications")
def list_applications(_: None = Depends(_require_admin_key)) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for slug in sorted(gcs_apps.list_application_slugs()):
        meta = gcs_apps.load_app_meta(slug)
        if not meta:
            continue
        rows.append(_application_row(slug, meta))
    rows.sort(key=lambda r: (r.get("updated") or "", r.get("slug") or ""), reverse=True)
    return {"applications": rows, "count": len(rows)}


@app.get("/api/applications/{slug}")
def get_application(slug: str, _: None = Depends(_require_admin_key)) -> dict[str, Any]:
    meta = gcs_apps.load_app_meta(slug)
    if not meta:
        raise HTTPException(status_code=404, detail="Application not found")
    row = _application_row(slug, meta)
    row["settings"] = settings_from_meta(meta)
    return row


@app.patch("/api/applications/{slug}")
def update_application(
    slug: str,
    body: ApplicationSettingsUpdate,
    _: None = Depends(_require_admin_key),
) -> dict[str, Any]:
    meta = gcs_apps.load_app_meta(slug)
    if not meta:
        raise HTTPException(status_code=404, detail="Application not found")
    try:
        updated = apply_settings_update(meta, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    gcs_apps.save_app_meta(slug, updated)
    row = _application_row(slug, updated)
    row["settings"] = settings_from_meta(updated)
    return row


@app.post("/api/applications/{slug}/gmail-draft")
def create_gmail_draft(
    slug: str,
    body: GmailDraftRequest,
    _: None = Depends(_require_admin_key),
) -> dict[str, Any]:
    result = run_gmail_draft(
        slug,
        regenerate=body.regenerate,
        force=body.force,
        dry_run=body.dry_run,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    if result.get("outcome") == "skipped":
        raise HTTPException(status_code=400, detail=result.get("detail") or "Draft skipped")
    return result


@app.get("/api/applications/{slug}/{filename}")
def get_application_file(
    slug: str,
    filename: str,
    _: None = Depends(_require_admin_key),
):
    allowed = {
        "meta.json": "application/json",
        "jd.txt": "text/plain; charset=utf-8",
        "resume.html": "text/html; charset=utf-8",
        "cover_letter.html": "text/html; charset=utf-8",
        "reply_email.txt": "text/plain; charset=utf-8",
        "resume.pdf": "application/pdf",
        "cover_letter.pdf": "application/pdf",
        "resume.docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "cover_letter.docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    if filename not in allowed:
        raise HTTPException(status_code=404, detail="File not found")

    path = f"applications/{slug}/{filename}"
    media = allowed[filename]
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

    if filename.endswith((".pdf", ".docx")):
        raw = gcs_apps.download_bytes(path)
        if raw is None:
            raise HTTPException(status_code=404, detail="File not found")
        return Response(content=raw, media_type=media, headers=headers)

    text = gcs_apps.download_text(path)
    if text is None:
        raise HTTPException(status_code=404, detail="File not found")
    if filename == "meta.json":
        return JSONResponse(content=json.loads(text))
    if filename.endswith(".html"):
        return HTMLResponse(content=text, media_type=media)
    return Response(content=text, media_type=media)


@app.get("/api/protocols/latest")
def latest_protocols(_: None = Depends(_require_admin_key)) -> dict[str, Any]:
    raw = gcs_apps.download_text(f"{gcs_apps.STATE_PREFIX}/latest_protocol_run.json")
    if not raw:
        return {"phases": [], "empty": True}
    return json.loads(raw)


@app.post("/api/run/gmail")
def api_run_gmail(_: None = Depends(_require_admin_key)) -> dict[str, Any]:
    result = run_phases([("gmail_scan", run_gmail)])
    return result


@app.post("/api/run/generate")
def api_run_generate(_: None = Depends(_require_admin_key)) -> dict[str, Any]:
    result = run_phases([("triage_generate", run_generate)])
    return result


@app.post("/api/run/linkedin")
def api_run_linkedin(_: None = Depends(_require_admin_key)) -> dict[str, Any]:
    result = run_phases([("linkedin", run_linkedin)])
    return result


@app.post("/api/run/all")
def api_run_all(body: RunRequest, _: None = Depends(_require_admin_key)) -> dict[str, Any]:
    return run_all(parallel=body.parallel)


@app.post("/api/jd/manual")
def api_manual_jd(body: ManualJdRequest, _: None = Depends(_require_admin_key)) -> dict[str, Any]:
    return run_manual_jd(
        body.jd_text,
        apply_url=body.apply_url,
        subject=body.subject,
        force=body.force,
    )


if ADMIN_STATIC.is_dir():
    app.mount("/admin", StaticFiles(directory=str(ADMIN_STATIC), html=True), name="admin")


@app.get("/")
def root_redirect() -> HTMLResponse:
    return HTMLResponse('<meta http-equiv="refresh" content="0;url=/admin/">')
