"""Create Gmail draft replies for job applications."""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import date
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr
from pathlib import Path

from reply_generator import is_noreply_address, repo_root, write_reply_file

SUBJECT_RE = re.compile(r"^Subject:\s*(.+)$", re.M)
DEFAULT_DRAFT_STATUSES = frozenset({"ready"})


@dataclass
class DraftResult:
    slug: str
    outcome: str  # created | sent | skipped | error
    detail: str = ""
    to_addr: str = ""
    subject: str = ""
    draft_id: str = ""
    message_id: str = ""


def parse_reply_file(path: Path) -> tuple[str, str]:
    text = path.read_text()
    match = SUBJECT_RE.search(text)
    if not match:
        raise ValueError(f"No Subject line found in {path}")
    subject = match.group(1).strip()
    body = SUBJECT_RE.sub("", text, count=1).strip()
    return subject, body


def apply_url_from_source(source: dict | None) -> str:
    if not source:
        return ""
    body = source.get("body_text", "") or source.get("jd_excerpt", "")
    match = re.search(r"Apply now:\s*(https://\S+)", body, re.I)
    if match:
        return match.group(1).rstrip(")")
    match = re.search(r"View job:\s*(https://\S+)", body, re.I)
    if match:
        return match.group(1).rstrip(")")
    return ""


def reply_to_address(source: dict | None, meta: dict) -> str:
    if source:
        _, addr = parseaddr(source.get("sender", ""))
        if addr and not is_noreply_address(addr):
            return addr
        if source.get("reply_to"):
            return source["reply_to"]

    notes = meta.get("notes", "")
    match = re.search(r"Recruiter:\s*[^@\n]*<([^>]+)>", notes, re.I)
    if match:
        return match.group(1)
    match = re.search(r"Recruiter:\s*(\S+@\S+)", notes, re.I)
    if match:
        return match.group(1)
    match = re.search(r"(\S+@\S+\.\S+)", notes)
    if match and not is_noreply_address(match.group(1)):
        return match.group(1)
    return ""


def find_inbox_json(root: Path, message_id: str) -> Path | None:
    if not message_id:
        return None
    inbox = root / "inbox" / "recruiter"
    if not inbox.is_dir():
        return None
    short = message_id[:8]
    matches = sorted(inbox.glob(f"*_{short}.json"))
    return matches[0] if matches else None


def load_source(meta: dict, *, inbox_json: Path | None, root: Path) -> dict | None:
    if inbox_json and inbox_json.exists():
        return json.loads(inbox_json.read_text())
    source = meta.get("source_email")
    if not source:
        return None
    message_id = source.get("message_id", "")
    path = find_inbox_json(root, message_id)
    if path:
        return json.loads(path.read_text())
    return source


def iter_application_slugs(root: Path | None = None) -> list[str]:
    root = root or repo_root()
    apps = root / "applications"
    return sorted(
        path.name
        for path in apps.iterdir()
        if path.is_dir() and (path / "meta.json").is_file()
    )


def attachment_part(path: Path, filename: str) -> MIMEApplication:
    data = path.read_bytes()
    subtype = "pdf" if path.suffix.lower() == ".pdf" else "octet-stream"
    part = MIMEApplication(data, _subtype=subtype)
    part.add_header("Content-Disposition", "attachment", filename=filename)
    return part


def build_mime_message(
    *,
    to_addr: str,
    subject: str,
    body: str,
    attachments: list[tuple[Path, str]],
    in_reply_to: str = "",
    references: str = "",
) -> MIMEMultipart:
    message = MIMEMultipart()
    message["To"] = to_addr
    message["Subject"] = subject
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
    if references:
        message["References"] = references
    message.attach(MIMEText(body, "plain"))

    for path, filename in attachments:
        message.attach(attachment_part(path, filename))

    return message


def fetch_rfc_message_id(service, message_id: str) -> tuple[str, str]:
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="metadata", metadataHeaders=["Message-ID"])
        .execute()
    )
    headers = msg.get("payload", {}).get("headers", [])
    rfc_id = next((h["value"] for h in headers if h.get("name", "").lower() == "message-id"), "")
    return rfc_id, msg.get("threadId", "")


def create_draft_or_send(
    service,
    mime_message: MIMEMultipart,
    *,
    thread_id: str = "",
    send: bool = False,
) -> dict:
    raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
    payload: dict = {"raw": raw}
    if thread_id:
        payload["threadId"] = thread_id

    if send:
        return service.users().messages().send(userId="me", body=payload).execute()

    return service.users().drafts().create(userId="me", body={"message": payload}).execute()


def save_meta(app_dir: Path, meta: dict) -> None:
    (app_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")


def draft_application(
    service,
    slug: str,
    *,
    to_override: str = "",
    inbox_json: Path | None = None,
    message_id_override: str = "",
    regenerate: bool = False,
    send: bool = False,
    dry_run: bool = False,
    force: bool = False,
    statuses: frozenset[str] = DEFAULT_DRAFT_STATUSES,
    root: Path | None = None,
) -> DraftResult:
    root = root or repo_root()
    app_dir = root / "applications" / slug
    if not app_dir.is_dir():
        return DraftResult(slug, "error", f"application not found: {app_dir}")

    meta_path = app_dir / "meta.json"
    meta = json.loads(meta_path.read_text())

    if meta.get("gmail_draft_id") and not force:
        return DraftResult(slug, "skipped", "draft already recorded in meta.json (use --force)")

    app_status = meta.get("status", "ready")
    if app_status not in statuses:
        return DraftResult(slug, "skipped", f"status={app_status!r}")

    source = load_source(meta, inbox_json=inbox_json, root=root)
    reply_path = app_dir / "reply_email.txt"
    if regenerate or not reply_path.exists():
        if dry_run:
            if not reply_path.exists():
                return DraftResult(slug, "skipped", "missing reply_email.txt")
        else:
            write_reply_file(slug, inbox_json=inbox_json)

    if not reply_path.exists():
        return DraftResult(
            slug,
            "skipped",
            "missing reply_email.txt (run scripts/render_application.sh)",
        )

    try:
        subject, body = parse_reply_file(reply_path)
    except ValueError as exc:
        return DraftResult(slug, "error", str(exc))

    to_addr = to_override or reply_to_address(source, meta)
    if not to_addr:
        apply_url = meta.get("apply_url") or apply_url_from_source(source)
        detail = "no human recruiter address (Indeed/LinkedIn noreply or missing email in meta)"
        if apply_url:
            detail += f"; apply via {apply_url}"
        return DraftResult(slug, "skipped", detail)

    resume = app_dir / "resume.pdf"
    cover = app_dir / "cover_letter.pdf"
    missing = [p.name for p in (resume, cover) if not p.exists()]
    if missing:
        return DraftResult(
            slug,
            "skipped",
            f"missing {', '.join(missing)} (run scripts/render_application.sh {slug})",
        )

    if dry_run:
        return DraftResult(
            slug,
            "created",
            "dry run",
            to_addr=to_addr,
            subject=subject,
        )

    company = meta.get("company", slug).replace(" ", "_")
    attachments = [
        (resume, "Cary_Jones_Resume.pdf"),
        (cover, f"Cary_Jones_Cover_Letter_{company}.pdf"),
    ]

    message_id = message_id_override or (source or {}).get("message_id", "")
    thread_id = (source or {}).get("thread_id", "")
    in_reply_to = references = ""

    if message_id:
        in_reply_to, fetched_thread = fetch_rfc_message_id(service, message_id)
        references = in_reply_to
        thread_id = thread_id or fetched_thread

    mime = build_mime_message(
        to_addr=to_addr,
        subject=subject,
        body=body,
        attachments=attachments,
        in_reply_to=in_reply_to,
        references=references,
    )

    try:
        result = create_draft_or_send(service, mime, thread_id=thread_id, send=send)
    except Exception as exc:  # noqa: BLE001 — surface Gmail API errors to CLI
        return DraftResult(slug, "error", str(exc))

    today = date.today().isoformat()
    if send:
        meta["gmail_sent_message_id"] = result.get("id", "")
        meta["status"] = "applied"
    else:
        meta["gmail_draft_id"] = result.get("id", "")
    meta["updated"] = today
    save_meta(app_dir, meta)

    outcome = "sent" if send else "created"
    return DraftResult(
        slug,
        outcome,
        to_addr=to_addr,
        subject=subject,
        draft_id=result.get("id", ""),
        message_id=result.get("message", {}).get("id", "") if send else "",
    )


def draft_all_pending(
    service,
    *,
    regenerate: bool = False,
    send: bool = False,
    dry_run: bool = False,
    force: bool = False,
    statuses: frozenset[str] = DEFAULT_DRAFT_STATUSES,
    root: Path | None = None,
) -> list[DraftResult]:
    results: list[DraftResult] = []
    for slug in iter_application_slugs(root):
        results.append(
            draft_application(
                service,
                slug,
                regenerate=regenerate,
                send=send,
                dry_run=dry_run,
                force=force,
                statuses=statuses,
                root=root,
            )
        )
    return results
