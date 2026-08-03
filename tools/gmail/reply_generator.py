"""Generate recruiter reply text from an application folder."""

from __future__ import annotations

import json
import re
from email.utils import parseaddr
from html import unescape
from pathlib import Path

TAG_RE = re.compile(r"<[^>]+>")
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


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def extract_bullets(cover_html: Path, *, max_bullets: int = 4) -> list[str]:
    if not cover_html.exists():
        return []

    bullets: list[str] = []
    for match in re.finditer(r"<li[^>]*>(.*?)</li>", cover_html.read_text(), re.S):
        text = TAG_RE.sub("", match.group(1))
        text = unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            bullets.append(text)
        if len(bullets) >= max_bullets:
            break
    return bullets


def recruiter_first_name(sender: str, *, company: str) -> str:
    name, addr = parseaddr(sender)
    if not sender or is_noreply_address(addr):
        return f"{company} team" if company else "there"

    if name:
        token = name.split()[0].strip(",")
        if token and token.lower() not in {"recruiting", "talent", "hiring", "jobs"}:
            return token
    return "there"


def reply_subject(meta: dict, source: dict | None) -> str:
    if source and source.get("subject"):
        subject = source["subject"]
        if not subject.lower().startswith("re:"):
            return f"Re: {subject}"
        return subject

    role = meta.get("role", "the role")
    company = meta.get("company", "your company")
    return f"Re: {role} — {company}"


def build_reply_body(
    *,
    greeting: str,
    meta: dict,
    contact: dict,
    bullets: list[str],
) -> str:
    company = meta.get("company", "your company")
    role = meta.get("role", "this opportunity")
    location = meta.get("location", "remote")
    salary = meta.get("salary")

    lines = [
        f"Hi {greeting},",
        "",
        f"Thank you for reaching out about the {role} opportunity"
        + (f" with {company}" if company else "")
        + ". I'm very interested and would welcome the chance to move forward.",
        "",
    ]

    if bullets:
        lines.append("A quick summary of my fit:")
        lines.append("")
        for bullet in bullets:
            lines.append(f"• {bullet}")
        lines.append("")
    else:
        lines.extend(
            [
                "I'm a senior Python backend engineer with 15+ years building production APIs, "
                "distributed systems, and cloud-native services on AWS.",
                "",
            ]
        )

    location = meta.get("location", "")
    if location:
        availability = (
            f"I'm based in Temple City (Los Angeles area), available for {location}"
        )
    else:
        availability = "I'm based in Temple City (Los Angeles area), available for remote work"
    if salary:
        availability += f", and the {salary} range aligns with my expectations"
    availability += ". I'd love to learn more about the team and next steps when you have a moment."
    lines.append(availability)
    lines.append("")
    lines.append(
        "Resume and cover letter are attached. Happy to jump on a call this week — "
        "just let me know what works."
    )
    lines.append("")
    lines.extend(
        [
            "Best regards,",
            contact.get("name", "Cary Jones"),
            contact.get("phone", ""),
            contact.get("email", ""),
            contact.get("linkedin", ""),
            contact.get("website", ""),
        ]
    )
    return "\n".join(line for line in lines if line is not None)


def generate_reply_text(
    slug: str,
    *,
    inbox_json: Path | None = None,
) -> str:
    root = repo_root()
    app_dir = root / "applications" / slug
    meta = load_json(app_dir / "meta.json")
    contact = load_json(root / "website" / "contact.json")

    source: dict | None = None
    if inbox_json and inbox_json.exists():
        source = load_json(inbox_json)
    elif meta.get("source_email"):
        source = meta["source_email"]

    sender = (source or {}).get("sender", "")
    company = meta.get("company", "")
    greeting = recruiter_first_name(sender, company=company.split("(")[0].strip())
    bullets = extract_bullets(app_dir / "cover_letter.html")
    subject = reply_subject(meta, source)
    body = build_reply_body(
        greeting=greeting,
        meta=meta,
        contact=contact,
        bullets=bullets,
    )
    return f"Subject: {subject}\n\n{body}\n"


def write_reply_file(slug: str, *, inbox_json: Path | None = None) -> Path:
    app_dir = repo_root() / "applications" / slug
    path = app_dir / "reply_email.txt"
    path.write_text(generate_reply_text(slug, inbox_json=inbox_json))
    return path
