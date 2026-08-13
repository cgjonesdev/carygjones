"""Parse and merge admin-editable application settings into meta.json."""

from __future__ import annotations

import re
from datetime import date
from email.utils import parseaddr
from typing import Any

GMAIL_ID_RE = re.compile(r"(?:[#/]([0-9a-f]{10,}))", re.I)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
NOREPLY_LOCAL_RE = re.compile(
    r"(^noreply$|^no-reply$|^donotreply$|^do-not-reply$|mailer-daemon|notifications?)",
    re.I,
)
NOREPLY_DOMAINS = {
    "match.indeed.com",
    "indeedemail.com",
    "linkedin.com",
    "updates.linkedin.com",
}


def is_noreply_address(addr: str) -> bool:
    if not addr:
        return True
    local, _, domain = addr.partition("@")
    local = local.lower()
    domain = domain.lower()
    if NOREPLY_LOCAL_RE.search(local):
        return True
    if domain in NOREPLY_DOMAINS:
        return True
    return any(token in local for token in ("noreply", "no-reply", "donotreply", "do-not-reply"))


def parse_sender_fields(sender: str) -> tuple[str, str]:
    name, addr = parseaddr(sender or "")
    return name.strip().strip('"'), addr.strip()


def recruiter_email_from_meta(meta: dict[str, Any]) -> str:
    direct = (meta.get("recruiter_email") or "").strip()
    if direct:
        return direct

    source = meta.get("source_email")
    if isinstance(source, dict):
        _, addr = parseaddr(source.get("sender") or "")
        if addr and not is_noreply_address(addr):
            return addr
        reply_to = (source.get("reply_to") or "").strip()
        if reply_to and not is_noreply_address(reply_to):
            return reply_to

    notes = meta.get("notes") or ""
    match = re.search(r"Recruiter:\s*[^@\n]*<([^>]+)>", notes, re.I)
    if match:
        return match.group(1).strip()
    match = re.search(r"Recruiter:\s*(\S+@\S+)", notes, re.I)
    if match:
        return match.group(1).strip()
    return ""


def recruiter_name_from_meta(meta: dict[str, Any]) -> str:
    direct = (meta.get("recruiter_name") or "").strip()
    if direct:
        return direct

    source = meta.get("source_email")
    if isinstance(source, dict):
        name, addr = parse_sender_fields(source.get("sender") or "")
        if name and "@" not in name:
            token = name.split()[0].strip(",")
            if token.lower() not in {"recruiting", "talent", "hiring", "jobs"}:
                return token

    return ""


def apply_source_email_to_meta(meta: dict[str, Any], msg: dict[str, Any]) -> dict[str, Any]:
    """Attach Gmail source fields and populate recruiter contact when sender is human."""
    meta = dict(meta)
    meta["source_email"] = {
        "message_id": msg.get("message_id"),
        "thread_id": msg.get("thread_id"),
        "subject": msg.get("subject"),
        "sender": msg.get("sender"),
    }
    if msg.get("reply_to"):
        meta["source_email"]["reply_to"] = msg.get("reply_to")

    sender = msg.get("sender") or ""
    name, addr = parse_sender_fields(sender)
    if addr and not is_noreply_address(addr):
        meta.setdefault("recruiter_email", addr)
        if name:
            token = name.split()[0].strip(",")
            if token and token.lower() not in {"recruiting", "talent", "hiring", "jobs"}:
                meta.setdefault("recruiter_name", token)
    return meta


def parse_gmail_message_id(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if "mail.google.com" in raw or raw.startswith("http"):
        matches = GMAIL_ID_RE.findall(raw)
        return matches[-1] if matches else ""
    return raw


ALLOWED_STATUSES = frozenset(
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
        "offer",
        "rejected",
        "skipped",
    }
)

# Logical pipeline order for UI and error messages.
STATUS_ORDER: tuple[str, ...] = (
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
    "offer",
    "rejected",
    "skipped",
)


def normalize_status(value: str | None, *, fallback: str = "ready") -> str:
    status = (value or fallback).strip().lower().replace(" ", "_")
    if status not in ALLOWED_STATUSES:
        raise ValueError(
            f"Invalid status {value!r}. Allowed: {', '.join(STATUS_ORDER)}"
        )
    return status


def settings_from_meta(meta: dict[str, Any]) -> dict[str, Any]:
    source = meta.get("source_email") if isinstance(meta.get("source_email"), dict) else {}

    return {
        "recruiter_email": recruiter_email_from_meta(meta),
        "recruiter_name": recruiter_name_from_meta(meta),
        "apply_url": meta.get("apply_url") or "",
        "gmail_message_id": source.get("message_id") or "",
        "email_subject": source.get("subject") or "",
        "status": meta.get("status") or "ready",
        "notes": meta.get("notes") or "",
        "interview_notes": meta.get("interview_notes") or "",
        "gmail_draft_id": meta.get("gmail_draft_id") or "",
        "gmail_sent_message_id": meta.get("gmail_sent_message_id") or "",
    }


def apply_settings_update(meta: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Merge admin form fields into meta; returns updated meta."""
    meta = dict(meta)
    today = date.today().isoformat()

    recruiter_email = (payload.get("recruiter_email") or "").strip()
    if recruiter_email and not EMAIL_RE.match(recruiter_email):
        raise ValueError("Recruiter email looks invalid.")

    recruiter_name = (payload.get("recruiter_name") or "").strip()
    apply_url = (payload.get("apply_url") or "").strip()
    gmail_message_id = parse_gmail_message_id(payload.get("gmail_message_id") or "")
    email_subject = (payload.get("email_subject") or "").strip()
    status = (payload.get("status") or meta.get("status") or "ready").strip()
    status = status.lower().replace(" ", "_")
    if status not in ALLOWED_STATUSES:
        raise ValueError(
            f"Invalid status {payload.get('status')!r}. "
            f"Allowed: {', '.join(STATUS_ORDER)}"
        )
    notes = payload.get("notes")
    if notes is not None:
        meta["notes"] = str(notes).strip()
    if "interview_notes" in payload:
        meta["interview_notes"] = str(payload.get("interview_notes") or "").strip()

    if recruiter_email:
        meta["recruiter_email"] = recruiter_email
    elif "recruiter_email" in payload and not recruiter_email:
        meta.pop("recruiter_email", None)

    if recruiter_name:
        meta["recruiter_name"] = recruiter_name
    elif "recruiter_name" in payload and not recruiter_name:
        meta.pop("recruiter_name", None)

    if apply_url:
        meta["apply_url"] = apply_url
    elif "apply_url" in payload and not apply_url:
        meta.pop("apply_url", None)

    meta["status"] = status
    meta["updated"] = today

    source = meta.get("source_email")
    if not isinstance(source, dict):
        source = {}
    if gmail_message_id:
        source["message_id"] = gmail_message_id
        source.setdefault("thread_id", gmail_message_id)
    if email_subject:
        source["subject"] = email_subject
    if recruiter_email:
        sender = f"{recruiter_name} <{recruiter_email}>" if recruiter_name else recruiter_email
        source["sender"] = sender
    if source:
        meta["source_email"] = source
    elif meta.get("source_email") == {}:
        meta.pop("source_email", None)

    return meta
