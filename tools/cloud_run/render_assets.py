"""Render HTML to PDF (Playwright) and DOCX (html2docx)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from html2docx import html2docx


def html_to_docx(html: str, out_path: Path) -> Path:
    buf = html2docx(html, title=out_path.stem)
    out_path.write_bytes(buf.getvalue())
    return out_path


def html_to_pdf(html: str, out_path: Path) -> Path:
    from playwright.sync_api import sync_playwright

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(html)
        tmp_path = Path(tmp.name)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(tmp_path.as_uri(), wait_until="networkidle")
            page.pdf(path=str(out_path), format="Letter", print_background=True)
            browser.close()
    finally:
        tmp_path.unlink(missing_ok=True)
    return out_path


def render_application_files(
    resume_html: str,
    cover_html: str,
    work_dir: Path,
) -> dict[str, Path]:
    from cover_letter_html import normalize_cover_letter_html

    cover_html = normalize_cover_letter_html(cover_html)
    work_dir.mkdir(parents=True, exist_ok=True)
    resume_html_path = work_dir / "resume.html"
    cover_html_path = work_dir / "cover_letter.html"
    resume_html_path.write_text(resume_html, encoding="utf-8")
    cover_html_path.write_text(cover_html, encoding="utf-8")

    resume_pdf = work_dir / "resume.pdf"
    cover_pdf = work_dir / "cover_letter.pdf"
    resume_docx = work_dir / "resume.docx"
    cover_docx = work_dir / "cover_letter.docx"

    html_to_pdf(resume_html, resume_pdf)
    html_to_pdf(cover_html, cover_pdf)
    html_to_docx(resume_html, resume_docx)
    html_to_docx(cover_html, cover_docx)

    return {
        "resume.html": resume_html_path,
        "cover_letter.html": cover_html_path,
        "resume.pdf": resume_pdf,
        "cover_letter.pdf": cover_pdf,
        "resume.docx": resume_docx,
        "cover_letter.docx": cover_docx,
    }
