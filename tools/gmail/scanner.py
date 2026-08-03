"""Scan Gmail for recruiter messages and extract likely job descriptions."""

from __future__ import annotations

import base64
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any

RECRUITER_FROM_PATTERNS = re.compile(
    r"(recruit|talent|hiring|career|staffing|linkedin|indeed|greenhouse|lever\.co|"
    r"workday|icims|smartrecruiters|jobvite|tcs\.com|cisco\.com|"
    r"noreply@|jobs@|hr@|humanresources)",
    re.I,
)

SUBJECT_PATTERNS = re.compile(
    r"(job|opportunity|position|role|opening|interview|hiring|engineer|developer|"
    r"application|recruiter|contract|remote|onsite)",
    re.I,
)

JD_BODY_PATTERNS = re.compile(
    r"(?:"
    r"job description|"
    r"about the role|about this role|"
    r"responsibilities|requirements|qualifications|"
    r"must have|nice to have|"
    r"what you(?:'ll| will) do|what we(?:'re| are) looking for|"
    r"years of experience|"
    r"pay range|salary range|compensation"
    r")",
    re.I,
)

TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class RecruiterEmail:
    message_id: str
    thread_id: str
    subject: str
    sender: str
    date: str
    snippet: str
    score: int
    signals: list[str]
    body_text: str
    jd_excerpt: str


def _decode_body(payload: dict[str, Any]) -> str:
    parts: list[str] = []

    def walk(part: dict[str, Any]) -> None:
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")
        if data and mime in ("text/plain", "text/html"):
            raw = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")
            if mime == "text/html":
                raw = TAG_RE.sub(" ", unescape(raw))
            parts.append(raw)
        for child in part.get("parts", []) or []:
            walk(child)

    if payload.get("body", {}).get("data"):
        walk(payload)
    else:
        for child in payload.get("parts", []) or []:
            walk(child)

    text = "\n".join(parts)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _header(headers: list[dict[str, str]], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _score_message(subject: str, sender: str, body: str) -> tuple[int, list[str]]:
    score = 0
    signals: list[str] = []

    if RECRUITER_FROM_PATTERNS.search(sender):
        score += 2
        signals.append("recruiter_sender")

    if SUBJECT_PATTERNS.search(subject):
        score += 2
        signals.append("job_subject")

    jd_hits = JD_BODY_PATTERNS.findall(body)
    if jd_hits:
        score += min(4, len(set(h.lower() for h in jd_hits)))
        signals.append(f"jd_keywords:{len(set(h.lower() for h in jd_hits))}")

    if len(body) > 800:
        score += 1
        signals.append("long_body")

    return score, signals


def _extract_jd_excerpt(body: str, limit: int = 2500) -> str:
    if not body:
        return ""

    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    start = 0
    for i, line in enumerate(lines):
        if JD_BODY_PATTERNS.search(line):
            start = max(0, i - 1)
            break

    excerpt = "\n".join(lines[start:])
    if len(excerpt) > limit:
        excerpt = excerpt[:limit].rstrip() + "\n…"
    return excerpt


def _parse_date(raw: str) -> str:
    if not raw:
        return ""
    try:
        return parsedate_to_datetime(raw).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return raw


def fetch_recruiter_emails(
    service,
    *,
    query: str,
    max_results: int = 25,
    min_score: int = 3,
) -> list[RecruiterEmail]:
    response = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    messages = response.get("messages", [])
    results: list[RecruiterEmail] = []

    for item in messages:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=item["id"], format="full")
            .execute()
        )
        headers = msg.get("payload", {}).get("headers", [])
        subject = _header(headers, "Subject")
        sender = _header(headers, "From")
        date = _parse_date(_header(headers, "Date"))
        body = _decode_body(msg.get("payload", {}))
        score, signals = _score_message(subject, sender, body)

        if score < min_score:
            continue

        results.append(
            RecruiterEmail(
                message_id=msg.get("id", ""),
                thread_id=msg.get("threadId", ""),
                subject=subject,
                sender=sender,
                date=date,
                snippet=msg.get("snippet", ""),
                score=score,
                signals=signals,
                body_text=body,
                jd_excerpt=_extract_jd_excerpt(body),
            )
        )

    results.sort(key=lambda r: (r.score, r.date), reverse=True)
    return results


def to_export_dict(email: RecruiterEmail) -> dict[str, Any]:
    data = asdict(email)
    data["gmail_url"] = f"https://mail.google.com/mail/u/0/#inbox/{email.message_id}"
    data["scanned_at"] = datetime.now(timezone.utc).isoformat()
    return data
