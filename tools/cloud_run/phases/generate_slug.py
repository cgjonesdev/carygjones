"""Generate tailored application files for an existing applications/{slug}/ folder."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

_GMAIL_DIR = Path(__file__).resolve().parents[2] / "gmail"
if _GMAIL_DIR.is_dir() and str(_GMAIL_DIR) not in sys.path:
    sys.path.insert(0, str(_GMAIL_DIR))
from text_clean import clean_jd_text  # noqa: E402


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _merge_generated_meta(
    existing: dict[str, Any],
    generated: dict[str, Any],
    score_data: dict[str, Any],
) -> dict[str, Any]:
    out = dict(existing)
    gen_meta = generated.get("meta_json") if isinstance(generated.get("meta_json"), dict) else {}
    for key in ("company", "client", "role", "location", "salary", "styling_notes"):
        val = gen_meta.get(key)
        if val not in (None, ""):
            out[key] = val
    if score_data.get("match_score") is not None:
        out["match_score"] = score_data["match_score"]
    if score_data.get("raw_match_score") is not None:
        out["raw_match_score"] = score_data.get("raw_match_score")
    out["updated"] = date.today().isoformat()
    if out.get("status") == "ready":
        out["status"] = "application_in_progress"
    stamp = f"Generated application files on {date.today().isoformat()}."
    notes = (out.get("notes") or "").strip()
    if stamp not in notes:
        out["notes"] = f"{notes} {stamp}".strip() if notes else stamp
    return out


def _upload_app_dir_to_gcs(slug: str, app_dir: Path) -> bool:
    if not os.environ.get("GCS_BUCKET", "").strip():
        return False
    try:
        import gcs_apps
    except Exception:
        return False

    text_names = ("jd.txt", "meta.json", "resume.html", "cover_letter.html", "reply_email.txt")
    binary_names = ("resume.pdf", "cover_letter.pdf", "resume.docx", "cover_letter.docx")
    for name in text_names:
        path = app_dir / name
        if not path.is_file():
            continue
        ctype = "application/json" if name.endswith(".json") else "text/plain; charset=utf-8"
        if name.endswith(".html"):
            ctype = "text/html; charset=utf-8"
        gcs_apps.upload_application_file(slug, name, path.read_text(encoding="utf-8"), ctype)
    for name in binary_names:
        path = app_dir / name
        if not path.is_file():
            continue
        ctype = (
            "application/pdf"
            if name.endswith(".pdf")
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        gcs_apps.upload_application_file(slug, name, path.read_bytes(), ctype)
    return True


def _refresh_admin_assets(slug: str) -> None:
    """Copy applications/{slug}/ into website/admin/apps/ so the UI can load HTML immediately."""
    build_script = repo_root() / "scripts" / "build_admin_data.py"
    spec = importlib.util.spec_from_file_location("build_admin_data", build_script)
    if spec is None or spec.loader is None:
        return
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    app_dir = repo_root() / "applications" / slug
    admin_apps = repo_root() / "website" / "admin" / "apps"
    mod.copy_app_assets(slug, app_dir, admin_apps)


def _render_outputs(slug: str, app_dir: Path, resume_html: str, cover_html: str) -> None:
    root = repo_root()
    render_script = root / "scripts" / "render_application.sh"
    if render_script.is_file():
        proc = subprocess.run(
            [str(render_script), slug],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return
    cloud_run = Path(__file__).resolve().parents[1]
    if str(cloud_run) not in sys.path:
        sys.path.insert(0, str(cloud_run))
    from render_assets import render_application_files

    render_application_files(resume_html, cover_html, app_dir)


def run_generate_for_slug(
    slug: str,
    *,
    repo: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Create resume/cover (and PDF/DOCX) from applications/{slug}/jd.txt."""
    if os.environ.get("JOB_MODE") == "cloud" and repo is None:
        return run_generate_for_slug_gcs(slug, force=force)
    return _run_generate_for_slug_local(slug, repo=repo, force=force)


def run_generate_for_slug_gcs(slug: str, *, force: bool = False) -> dict[str, Any]:
    """GCS-only generate path for Cloud Run admin API."""
    import tempfile

    import gcs_apps
    from render_assets import render_application_files

    cloud_run = Path(__file__).resolve().parents[1]
    if str(cloud_run) not in sys.path:
        sys.path.insert(0, str(cloud_run))
    from openai_tailor import generate_application, score_jd

    meta = gcs_apps.load_app_meta(slug)
    if not meta:
        return {"error": f"unknown slug {slug}"}

    jd_raw = gcs_apps.download_text(f"{gcs_apps.APPS_PREFIX}/{slug}/jd.txt")
    if not jd_raw:
        return {"error": f"missing applications/{slug}/jd.txt in GCS"}

    if (
        gcs_apps.download_text(f"{gcs_apps.APPS_PREFIX}/{slug}/resume.html")
        and gcs_apps.download_text(f"{gcs_apps.APPS_PREFIX}/{slug}/cover_letter.html")
        and not force
    ):
        return {
            "status": "ok",
            "skipped": True,
            "slug": slug,
            "reason": "resume.html and cover_letter.html already exist in GCS",
        }

    jd_text = clean_jd_text(jd_raw)
    if len(jd_text) < 80:
        return {"error": "JD text too short (need at least 80 characters)."}

    apply_url = meta.get("apply_url")
    subject = meta.get("role") or meta.get("company") or slug
    score_data = score_jd(jd_text, subject=str(subject), apply_url=apply_url)
    if meta.get("match_score") is not None and not force:
        score_data["match_score"] = meta["match_score"]

    files = generate_application(jd_text, score_data, apply_url=apply_url)
    resume_html = files.get("resume_html") or ""
    cover_html = files.get("cover_letter_html") or ""
    reply_txt = files.get("reply_email_txt") or ""
    jd_out = files.get("jd_txt") or jd_text
    if not resume_html or not cover_html:
        return {"error": "OpenAI returned empty resume or cover letter HTML"}

    meta = _merge_generated_meta(meta, files, score_data)
    gcs_apps.upload_application_file(slug, "jd.txt", jd_out.strip() + "\n", "text/plain; charset=utf-8")
    gcs_apps.upload_application_file(slug, "resume.html", resume_html, "text/html; charset=utf-8")
    gcs_apps.upload_application_file(slug, "cover_letter.html", cover_html, "text/html; charset=utf-8")
    if reply_txt:
        gcs_apps.upload_application_file(slug, "reply_email.txt", reply_txt, "text/plain; charset=utf-8")
    gcs_apps.save_app_meta(slug, meta)

    render_warning = None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            rendered = render_application_files(resume_html, cover_html, work)
            for name, path in rendered.items():
                if name.endswith((".pdf", ".docx")):
                    gcs_apps.upload_application_file(
                        slug,
                        name,
                        path.read_bytes(),
                        "application/pdf"
                        if name.endswith(".pdf")
                        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
    except Exception as exc:
        render_warning = str(exc)

    result: dict[str, Any] = {
        "status": "ok",
        "generated": {
            "slug": slug,
            "score": meta.get("match_score"),
            "company": meta.get("company"),
            "role": meta.get("role"),
        },
        "uploaded_to_gcs": True,
    }
    if render_warning:
        result["render_warning"] = render_warning
    return result


def _run_generate_for_slug_local(
    slug: str,
    *,
    repo: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    root = repo or repo_root()
    app_dir = root / "applications" / slug
    jd_path = app_dir / "jd.txt"
    meta_path = app_dir / "meta.json"

    if not jd_path.is_file():
        return {"error": f"missing applications/{slug}/jd.txt"}

    resume_path = app_dir / "resume.html"
    cover_path = app_dir / "cover_letter.html"
    if resume_path.is_file() and cover_path.is_file() and not force:
        return {
            "status": "ok",
            "skipped": True,
            "slug": slug,
            "reason": "resume.html and cover_letter.html already exist",
        }

    meta: dict[str, Any] = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return {"error": f"invalid json in applications/{slug}/meta.json: {exc}"}

    jd_text = clean_jd_text(jd_path.read_text(encoding="utf-8"))
    if len(jd_text) < 80:
        return {"error": "JD text too short (need at least 80 characters)."}

    apply_url = meta.get("apply_url")
    subject = meta.get("role") or meta.get("company") or slug

    cloud_run = Path(__file__).resolve().parents[1]
    if str(cloud_run) not in sys.path:
        sys.path.insert(0, str(cloud_run))
    from openai_tailor import generate_application, score_jd

    score_data = score_jd(jd_text, subject=str(subject), apply_url=apply_url)
    if meta.get("match_score") is not None and not force:
        score_data["match_score"] = meta["match_score"]

    files = generate_application(jd_text, score_data, apply_url=apply_url)
    resume_html = files.get("resume_html") or ""
    cover_html = files.get("cover_letter_html") or ""
    reply_txt = files.get("reply_email_txt") or ""
    jd_txt = files.get("jd_txt") or jd_text

    if not resume_html or not cover_html:
        return {"error": "OpenAI returned empty resume or cover letter HTML"}

    meta = _merge_generated_meta(meta, files, score_data)

    app_dir.mkdir(parents=True, exist_ok=True)
    jd_path.write_text(jd_txt.strip() + "\n", encoding="utf-8")
    resume_path.write_text(resume_html, encoding="utf-8")
    cover_path.write_text(cover_html, encoding="utf-8")
    if reply_txt:
        (app_dir / "reply_email.txt").write_text(reply_txt, encoding="utf-8")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    _refresh_admin_assets(slug)

    render_warning = None
    try:
        _render_outputs(slug, app_dir, resume_html, cover_html)
    except Exception as exc:
        render_warning = str(exc)

    uploaded = _upload_app_dir_to_gcs(slug, app_dir)
    _refresh_admin_assets(slug)

    result: dict[str, Any] = {
        "status": "ok",
        "generated": {
            "slug": slug,
            "score": meta.get("match_score"),
            "company": meta.get("company"),
            "role": meta.get("role"),
        },
        "uploaded_to_gcs": uploaded,
    }
    if render_warning:
        result["render_warning"] = render_warning
    return result
