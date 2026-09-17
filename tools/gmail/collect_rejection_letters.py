#!/usr/bin/env python3
"""Search Gmail for job application rejection emails and collate into HTML/PDF."""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from auth import get_gmail_service

# Broad Gmail search covering common ATS / recruiter rejection phrasing.
SEARCH_QUERIES = [
    'newer_than:18m (subject:(update on your application OR application status OR application update OR regarding your application OR "thank you for applying" OR "thank you for your interest" OR "not moving forward" OR "decided to move forward" OR "other candidates" OR "not selected" OR "unfortunately" OR "position has been filled" OR "we have filled" OR "will not be moving forward" OR "no longer under consideration" OR "regret to inform"))',
    'newer_than:18m (subject:(rejection OR "not a fit" OR "not selected for" OR "after careful consideration") (job OR application OR position OR role OR interview OR hiring OR candidacy))',
    'newer_than:18m from:(noreply OR no-reply OR donotreply OR careers OR talent OR recruiting OR greenhouse OR lever OR workday OR ashby OR smartrecruiters OR jobvite OR icims OR breezy OR bamboo) (subject:(update OR thank OR unfortunately OR application OR interest OR status))',
]

REJECTION_SUBJECT = re.compile(
    r"(?:"
    r"update on your application|"
    r"application (?:status|update|decision)|"
    r"regarding your application|"
    r"thank you for (?:applying|your interest|your application)|"
    r"not moving forward|"
    r"decided to (?:move|pursue) (?:forward|other)|"
    r"other candidates|"
    r"not (?:selected|chosen|a (?:good )?fit)|"
    r"unfortunately|"
    r"position (?:has been |is )?filled|"
    r"we have filled|"
    r"will not be moving forward|"
    r"no longer under consideration|"
    r"regret to inform|"
    r"after careful consideration|"
    r"we(?:'ve| have) decided|"
    r"candidacy|"
    r"rejection"
    r")",
    re.I,
)

REJECTION_BODY = re.compile(
    r"(?:"
    r"not (?:moving|be moving) forward|"
    r"decided (?:to )?(?:move|pursue) (?:forward with|other)|"
    r"move forward with other|"
    r"other candidates|"
    r"other applicants|"
    r"not (?:selected|chosen|shortlisted|a (?:good )?fit)|"
    r"unfortunately.{0,120}(?:application|position|role|candidacy|filled|move)|"
    r"position (?:has been |is )?(?:filled|closed)|"
    r"will not be (?:filled|able to move)|"
    r"no longer (?:under consideration|pursuing|available)|"
    r"regret to inform|"
    r"will not be advancing|"
    r"not advancing|"
    r"after careful (?:review|consideration)|"
    r"we(?:'ve| have) (?:chosen|decided) (?:to go with |another|not to)|"
    r"selected another candidate|"
    r"going (?:in )?another direction|"
    r"not (?:the )?right (?:fit|match)|"
    r"unable to (?:offer|proceed|move forward)|"
    r"pursue other candidates|"
    r"qualifications better align|"
    r"will not be moving forward with your candidacy|"
    r"decided not to move forward|"
    r"won'?t be able to invite you"
    r")",
    re.I,
)

FALSE_POSITIVE = re.compile(
    r"(?:"
    r"unsubscribe|"
    r"job alert|"
    r"new jobs? (?:for you|matching)|"
    r"recommended jobs|"
    r"weekly digest|"
    r"interview (?:invite|invitation|scheduled|confirmed)|"
    r"next steps|"
    r"phone screen|"
    r"offer letter|"
    r"welcome to |"
    r"you(?:'re| are) hired|"
    r"start date|"
    r"background check"
    r")",
    re.I,
)

NOISE_SENDERS = re.compile(
    r"(?:"
    r"linkedin\.com|"
    r"indeed\.com|"
    r"dice\.com|"
    r"ziprecruiter|"
    r"glassdoor|"
    r"monster\.com|"
    r"ihire\.com|"
    r"newsletter|"
    r"marketing@"
    r")",
    re.I,
)


@dataclass
class RejectionEmail:
    message_id: str
    thread_id: str
    subject: str
    sender: str
    date: str
    date_iso: str
    snippet: str
    body_text: str
    gmail_url: str
    company_guess: str


def _header(headers: list[dict[str, str]], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _decode_body(payload: dict[str, Any]) -> str:
    plain_parts: list[str] = []
    html_parts: list[str] = []

    def walk(part: dict[str, Any]) -> None:
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")
        if data and mime in ("text/plain", "text/html"):
            raw = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")
            if mime == "text/html":
                html_parts.append(raw)
            else:
                plain_parts.append(raw)
        for child in part.get("parts", []) or []:
            walk(child)

    if payload.get("body", {}).get("data"):
        walk(payload)
    else:
        for child in payload.get("parts", []) or []:
            walk(child)

    plain = "\n".join(plain_parts).strip()
    if len(plain) >= 80:
        return _strip_noise(plain)

    if html_parts:
        text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", "\n".join(html_parts))
        text = re.sub(r"(?is)<br\s*/?>", "\n", text)
        text = re.sub(r"(?is)</p>", "\n\n", text)
        text = re.sub(r"(?is)<[^>]+>", " ", text)
        text = html.unescape(text)
        return _strip_noise(text)
    return _strip_noise(plain)


def _strip_noise(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Drop common email footers / tracking
    cut = re.search(
        r"(?im)^(unsubscribe|view this email in|this email was sent|privacy policy|"
        r"manage preferences|click here to|sent via |powered by )",
        text,
    )
    if cut and cut.start() > 200:
        text = text[: cut.start()].rstrip()
    return text.strip()


def _parse_date(raw: str) -> tuple[str, str]:
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%b %d, %Y"), dt.astimezone().date().isoformat()
    except Exception:
        return raw or "Unknown date", "1970-01-01"


def _guess_company(sender: str, subject: str, body: str) -> str:
    # From: "Company Careers <jobs@company.com>"
    m = re.match(r'"?([^"<@]+?)"?\s*<', sender)
    if m:
        name = m.group(1).strip()
        name = re.sub(
            r"(?i)\b(careers?|recruiting|talent|hiring|team|noreply|no-?reply|"
            r"donotreply|do-?not-?reply|notifications?|jobs?|hr)\b",
            "",
            name,
        ).strip(" -–—|,")
        if len(name) >= 2 and not re.fullmatch(r"(?i)via .*", name):
            return name[:80]

    # Domain root
    dm = re.search(r"@([a-z0-9.-]+)", sender, re.I)
    if dm:
        host = dm.group(1).lower()
        host = re.sub(
            r"^(mail|email|e|noreply|no-reply|donotreply|jobs|careers|talent|"
            r"recruiting|notifications?|updates?)\.",
            "",
            host,
        )
        parts = [p for p in host.split(".") if p not in ("com", "io", "co", "net", "org", "us", "ai")]
        if parts:
            brand = parts[0].replace("-", " ").title()
            if brand.lower() not in ("gmail", "google", "yahoo", "outlook", "hotmail"):
                return brand

    sm = re.search(
        r"(?i)(?:at|with|from|for)\s+([A-Z][A-Za-z0-9&.' -]{1,40})",
        subject,
    )
    if sm:
        return sm.group(1).strip()[:80]

    return "Unknown company"


ACKNOWLEDGMENT_ONLY = re.compile(
    r"(?i)("
    r"we(?:'ve| have) received your application|"
    r"application has been received|"
    r"will review (?:it|your application)|"
    r"will be in touch if|"
    r"if (?:it|your application) seems like a good fit|"
    r"you have new application updates this week"
    r")"
)

STRONG_REJECTION = re.compile(
    r"(?i)("
    r"not (?:moving|be moving) forward|"
    r"move forward with other|"
    r"other candidates|"
    r"other applicants|"
    r"not (?:selected|shortlisted)|"
    r"regret to inform|"
    r"position (?:has been |is )?(?:filled|closed)|"
    r"will not be (?:filled|able to move)|"
    r"decided not to move forward|"
    r"pursue other candidates|"
    r"qualifications better align|"
    r"after careful consideration|"
    r"will not be moving forward with your candidacy"
    r")"
)


def _is_rejection(subject: str, sender: str, body: str, snippet: str) -> bool:
    """Same criteria as the Aug 21 successful 16-letter packet."""
    blob = f"{subject}\n{snippet}\n{body[:2500]}"
    if re.search(r"(?i)you have new application updates this week", subject):
        return False
    if FALSE_POSITIVE.search(subject) and not REJECTION_BODY.search(blob):
        return False
    if not REJECTION_BODY.search(blob):
        return False
    if ACKNOWLEDGMENT_ONLY.search(blob) and not STRONG_REJECTION.search(blob):
        return False
    # Drop pure LinkedIn digests
    if "linkedin.com" in sender.lower() and "application updates this week" in subject.lower():
        return False
    # Same manual drops as Aug 21 final PDF (ack-only that slipped through)
    blob_l = f"{subject} {sender}".lower()
    if "zenbusiness" in blob_l or re.search(r"\bartera\b", blob_l):
        return False
    return True


def _list_ids(service, query: str, max_results: int) -> list[str]:
    ids: list[str] = []
    page_token = None
    while len(ids) < max_results:
        kwargs: dict[str, Any] = {
            "userId": "me",
            "q": query,
            "maxResults": min(100, max_results - len(ids)),
        }
        if page_token:
            kwargs["pageToken"] = page_token
        resp = service.users().messages().list(**kwargs).execute()
        for msg in resp.get("messages", []) or []:
            ids.append(msg["id"])
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids


def fetch_rejections(service, *, max_per_query: int = 200) -> list[RejectionEmail]:
    seen: set[str] = set()
    results: list[RejectionEmail] = []

    for query in SEARCH_QUERIES:
        print(f"Searching: {query[:90]}...", flush=True)
        ids = _list_ids(service, query, max_per_query)
        print(f"  → {len(ids)} candidate message(s)", flush=True)
        for mid in ids:
            if mid in seen:
                continue
            seen.add(mid)
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=mid, format="full")
                .execute()
            )
            headers = msg.get("payload", {}).get("headers", [])
            subject = _header(headers, "Subject")
            sender = _header(headers, "From")
            date_raw = _header(headers, "Date")
            date_fmt, date_iso = _parse_date(date_raw)
            snippet = msg.get("snippet", "")
            body = _decode_body(msg.get("payload", {}) or {})
            if not _is_rejection(subject, sender, body, snippet):
                continue
            results.append(
                RejectionEmail(
                    message_id=mid,
                    thread_id=msg.get("threadId", mid),
                    subject=subject or "(no subject)",
                    sender=sender or "(unknown)",
                    date=date_fmt,
                    date_iso=date_iso,
                    snippet=snippet,
                    body_text=body[:4000],
                    gmail_url=f"https://mail.google.com/mail/u/0/#inbox/{mid}",
                    company_guess=_guess_company(sender, subject, body),
                )
            )

    # Dedupe by (company_guess.lower(), date_iso, normalized subject)
    deduped: list[RejectionEmail] = []
    keys: set[str] = set()
    for r in sorted(results, key=lambda x: x.date_iso, reverse=True):
        key = f"{r.company_guess.lower()}|{r.date_iso}|{re.sub(r'\W+', ' ', r.subject.lower())[:60]}"
        if key in keys:
            continue
        keys.add(key)
        deduped.append(r)
    return deduped


def render_html(rejections: list[RejectionEmail], generated_at: str) -> str:
    rows = []
    for i, r in enumerate(rejections, 1):
        body_html = html.escape(r.body_text).replace("\n", "<br>\n")
        rows.append(
            f"""
            <article class="letter" id="r{i}">
              <header>
                <div class="meta-row">
                  <span class="num">#{i}</span>
                  <span class="company">{html.escape(r.company_guess)}</span>
                  <span class="date">{html.escape(r.date)}</span>
                </div>
                <h2>{html.escape(r.subject)}</h2>
                <p class="from">From: {html.escape(r.sender)}</p>
              </header>
              <div class="body">{body_html}</div>
            </article>
            """
        )

    toc = "\n".join(
        f'<li><a href="#r{i}"><strong>{html.escape(r.company_guess)}</strong> — '
        f'{html.escape(r.date)} — {html.escape(r.subject[:80])}</a></li>'
        for i, r in enumerate(rejections, 1)
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Job Application Rejection Letters — Cary Jones</title>
  <style>
    :root {{
      --text: #1e293b;
      --muted: #64748b;
      --accent: #0f766e;
      --rule: #e2e8f0;
      --bg-soft: #f8fafc;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      color: var(--text);
      font-size: 10.5pt;
      line-height: 1.45;
      margin: 0;
      background: #fff;
    }}
    main {{
      max-width: 8.5in;
      margin: 0 auto;
      padding: 0.55in 0.65in;
    }}
    .cover {{
      border-bottom: 3px solid var(--accent);
      padding-bottom: 1rem;
      margin-bottom: 1.25rem;
    }}
    .cover h1 {{
      font-size: 1.55rem;
      margin: 0 0 0.35rem;
      color: var(--text);
    }}
    .cover .subtitle {{
      color: var(--muted);
      margin: 0 0 0.75rem;
      font-size: 0.95rem;
    }}
    .cover .stats {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem 1.5rem;
      font-size: 0.9rem;
    }}
    .cover .stats strong {{ color: var(--accent); }}
    .purpose {{
      background: var(--bg-soft);
      border-left: 3px solid var(--accent);
      padding: 0.65rem 0.85rem;
      margin: 1rem 0 1.25rem;
      font-size: 0.92rem;
      color: var(--muted);
    }}
    h2.section {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--accent);
      border-bottom: 1px solid var(--rule);
      padding-bottom: 0.25rem;
      margin: 1.5rem 0 0.75rem;
    }}
    .toc {{
      columns: 1;
      padding-left: 1.1rem;
      margin: 0 0 1.5rem;
    }}
    .toc li {{ margin-bottom: 0.35rem; font-size: 0.88rem; break-inside: avoid; }}
    .toc a {{ color: var(--text); text-decoration: none; }}
    .letter {{
      break-inside: avoid;
      page-break-inside: avoid;
      border: 1px solid var(--rule);
      border-radius: 6px;
      padding: 0.85rem 1rem;
      margin: 0 0 1.1rem;
      background: #fff;
    }}
    .letter header {{ margin-bottom: 0.65rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--rule); }}
    .meta-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem 1rem;
      align-items: baseline;
      margin-bottom: 0.35rem;
      font-size: 0.82rem;
    }}
    .num {{
      background: var(--accent);
      color: #fff;
      border-radius: 999px;
      padding: 0.1rem 0.55rem;
      font-weight: 600;
      font-size: 0.75rem;
    }}
    .company {{ font-weight: 700; color: var(--accent); font-size: 1rem; }}
    .date {{ color: var(--muted); margin-left: auto; }}
    .letter h2 {{
      font-size: 0.98rem;
      margin: 0.2rem 0 0.25rem;
      font-weight: 600;
    }}
    .from {{ margin: 0; color: var(--muted); font-size: 0.82rem; }}
    .body {{
      white-space: normal;
      font-size: 0.88rem;
      color: #334155;
      max-height: none;
    }}
    @media print {{
      main {{ padding: 0.4in 0.45in; }}
      .letter {{ break-inside: avoid; page-break-inside: avoid; }}
      a {{ color: inherit; text-decoration: none; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="cover">
      <h1>Job Application Rejection Letters</h1>
      <p class="subtitle">Cary Jones · cgjonesdev@gmail.com · Compiled {html.escape(generated_at)}</p>
      <div class="stats">
        <span><strong>{len(rejections)}</strong> rejection letters</span>
        <span>Date range:
          <strong>{html.escape(rejections[-1].date if rejections else "—")}</strong>
          →
          <strong>{html.escape(rejections[0].date if rejections else "—")}</strong>
        </span>
      </div>
      <p class="purpose">
        This packet collates employer / ATS messages declining my candidacy after I applied
        or interviewed. It is intended as documentation of an active, recent job search.
        Messages were exported from Gmail; marketing digests and job alerts were filtered out
        where possible.
      </p>
    </section>

    <h2 class="section">Table of contents</h2>
    <ol class="toc">
      {toc}
    </ol>

    <h2 class="section">Letters</h2>
    {"".join(rows)}
  </main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "interview" / "job_search_evidence",
        help="Directory for HTML/PDF/JSON outputs",
    )
    parser.add_argument("--max-per-query", type=int, default=250)
    parser.add_argument("--json-only", action="store_true")
    parser.add_argument("--skip-pdf", action="store_true")
    args = parser.parse_args()

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    service = get_gmail_service()
    rejections = fetch_rejections(service, max_per_query=args.max_per_query)
    print(f"\nKept {len(rejections)} rejection letter(s) after filtering/dedupe.", flush=True)

    payload = [asdict(r) for r in rejections]
    json_path = out_dir / "rejection_letters.json"
    json_path.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {json_path}", flush=True)

    if args.json_only:
        return 0

    generated_at = datetime.now().astimezone().strftime("%B %d, %Y %I:%M %p %Z")
    html_doc = render_html(rejections, generated_at)
    html_path = out_dir / "rejection_letters.html"
    html_path.write_text(html_doc)
    print(f"Wrote {html_path}", flush=True)

    if args.skip_pdf:
        return 0

    pdf_path = out_dir / "rejection_letters.pdf"
    _write_pdf(rejections, pdf_path, generated_at)
    print(f"Wrote {pdf_path}", flush=True)
    return 0


def _write_pdf(rejections: list[RejectionEmail], pdf_path: Path, generated_at: str) -> None:
    """Render a clean multi-page PDF via reportlab (Chrome headless is unreliable here)."""
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer

    styles = getSampleStyleSheet()
    accent = HexColor("#0f766e")
    muted = HexColor("#64748b")
    title = ParagraphStyle("T", parent=styles["Heading1"], fontSize=18, spaceAfter=6)
    h_co = ParagraphStyle(
        "C", parent=styles["Heading2"], fontSize=12, textColor=accent, spaceBefore=4, spaceAfter=4
    )
    subj = ParagraphStyle("S", parent=styles["Normal"], fontSize=10, leading=13, spaceAfter=2)
    meta = ParagraphStyle("M", parent=styles["Normal"], fontSize=8, textColor=muted, spaceAfter=6)
    body = ParagraphStyle(
        "B", parent=styles["Normal"], fontSize=9, leading=12, textColor=HexColor("#334155")
    )
    cover = ParagraphStyle(
        "P", parent=styles["Normal"], fontSize=9, leading=12, textColor=muted, spaceBefore=8, spaceAfter=12
    )

    def esc(s: str) -> str:
        return html.escape(s or "")

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    story: list = []
    date_lo = rejections[-1].date if rejections else "—"
    date_hi = rejections[0].date if rejections else "—"
    story.append(Paragraph("Job Application Rejection Letters", title))
    story.append(Paragraph(f"Cary Jones · cgjonesdev@gmail.com · Compiled {esc(generated_at)}", meta))
    story.append(
        Paragraph(f"<b>{len(rejections)}</b> rejection letters · {esc(date_lo)} → {esc(date_hi)}", meta)
    )
    story.append(
        Paragraph(
            "This packet collates employer and ATS messages declining my candidacy after I applied "
            "or interviewed. It documents an active, recent job search. Application receipts, job "
            "alerts, and LinkedIn digests were excluded.",
            cover,
        )
    )
    story.append(Paragraph("<b>Contents</b>", h_co))
    for i, r in enumerate(rejections, 1):
        story.append(
            Paragraph(
                f'{i}. <b>{esc(r.company_guess)}</b> — {esc(r.date)} — {esc(r.subject[:90])}',
                meta,
            )
        )
    if rejections:
        story.append(PageBreak())

    for i, r in enumerate(rejections, 1):
        block = [
            Paragraph(f"#{i} · {esc(r.company_guess)} · {esc(r.date)}", h_co),
            Paragraph(esc(r.subject), subj),
            Paragraph(f"From: {esc(r.sender)}", meta),
            Paragraph(esc(r.body_text[:3200]).replace("\n", "<br/>"), body),
        ]
        story.append(KeepTogether(block))
        if i < len(rejections):
            story.append(Spacer(1, 14))
            if i % 2 == 0:
                story.append(PageBreak())

    doc.build(story)


if __name__ == "__main__":
    raise SystemExit(main())
