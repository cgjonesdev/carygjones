"""Scan Freelancer.com job listings and create bid-ready application folders."""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import date, datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_CATEGORIES = (
    "python",
    "artificial-intelligence",
    "automation",
    "api",
    "data-processing",
)

SCORE_KEYWORDS: list[tuple[str, int]] = [
    ("fastapi", 12),
    ("django", 10),
    ("flask", 8),
    ("python", 8),
    ("llm", 10),
    ("langchain", 10),
    ("rag", 10),
    ("openai", 6),
    ("automation", 8),
    ("integration", 8),
    ("microservice", 8),
    ("postgresql", 8),
    ("aws", 8),
    ("docker", 6),
    ("backend", 8),
    ("api", 5),
    ("etl", 8),
    ("scraping", 5),
    ("healthcare", 6),
    ("hipaa", 6),
    ("rest", 4),
    ("selenium", 4),
]

SKIP_KEYWORDS = (
    "eldorado.gg",
    "gambling",
    "crypto bot",
    "homework",
    "student",
    "logo design",
    "graphic design only",
    "video edit",
    "data entry",
    "typing",
    "android only",
    "ios only",
    "compactlogix",
    "plc ",
    "wordpress theme",
)

SPAM_TITLE_RE = re.compile(
    r"earn \$|easy \$|reddit comment|app install|\$10 per|affiliate|signup",
    re.I,
)


class _JobCardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.jobs: list[dict[str, str]] = []
        self._in_card = False
        self._in_title_link = False
        self._in_desc = False
        self._href = ""
        self._title = ""
        self._desc_parts: list[str] = []
        self._budget = ""
        self._capture_budget = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "div" and attr.get("class") == "JobSearchCard-item-inner":
            self._in_card = True
            self._href = ""
            self._title = ""
            self._desc_parts = []
            self._budget = ""
        if not self._in_card:
            return
        if tag == "a" and "JobSearchCard-primary-heading-link" in (attr.get("class") or ""):
            href = attr.get("href") or ""
            if "/projects/" in href:
                self._in_title_link = True
                self._href = href
        if tag == "p" and "JobSearchCard-primary-description" in (attr.get("class") or ""):
            self._in_desc = True
        if tag == "span" and self._in_card:
            cls = attr.get("class") or ""
            self._capture_budget = "JobSearchCard-secondary-price" in cls or "JobSearchCard-primary-price" in cls

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_title_link:
            self._in_title_link = False
        if tag == "p" and self._in_desc:
            self._in_desc = False
        if tag == "div" and self._in_card:
            title = re.sub(r"\s+", " ", self._title).strip()
            desc = re.sub(r"\s+", " ", " ".join(self._desc_parts)).strip()
            if title and self._href:
                url = self._href
                if url.startswith("/"):
                    url = f"https://www.freelancer.com{url}"
                self.jobs.append(
                    {
                        "title": unescape(title),
                        "url": url,
                        "description": unescape(desc)[:1200],
                        "budget": self._budget,
                    }
                )
            self._in_card = False

    def handle_data(self, data: str) -> None:
        if self._in_title_link:
            self._title += data
        if self._in_desc:
            self._desc_parts.append(data)
        if self._capture_budget and data.strip().startswith("$"):
            self._budget = data.strip()


def repo_root() -> Path:
    for key in ("REPO_ROOT", "ASSETS_DIR"):
        val = os.environ.get(key, "").strip()
        if val:
            return Path(val)
    return Path(__file__).resolve().parents[2]


def _categories() -> tuple[str, ...]:
    raw = os.environ.get("FREELANCER_CATEGORIES", "")
    if raw.strip():
        return tuple(c.strip() for c in raw.split(",") if c.strip())
    return DEFAULT_CATEGORIES


def _fetch(url: str) -> str:
    proc = subprocess.run(
        ["curl", "-sL", "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", url],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"curl failed ({proc.returncode}) for {url}")
    return proc.stdout


def _parse_cards(html: str) -> list[dict[str, str]]:
    parser = _JobCardParser()
    parser.feed(html)
    return parser.jobs


def _slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    tail = path.split("/projects/")[-1] if "/projects/" in path else path
    tail = tail.split("?")[0].strip("/")
    base = re.sub(r"[^a-z0-9]+", "_", tail.lower()).strip("_")
    base = base[:60] or "project"
    return f"freelancer_{base}"


def _score_job(job: dict[str, str]) -> int:
    blob = " ".join(
        [job.get("title") or "", job.get("description") or "", job.get("budget") or ""]
    ).lower()
    if SPAM_TITLE_RE.search(blob):
        return 0
    for bad in SKIP_KEYWORDS:
        if bad in blob:
            return max(0, 35)
    score = 45
    for keyword, weight in SCORE_KEYWORDS:
        if keyword in blob:
            score += weight
    budget = _parse_budget(job.get("budget") or "")
    if budget >= 500:
        score += 5
    elif budget and budget < 75:
        score -= 12
    return min(92, max(0, score))


def _parse_budget(text: str) -> int:
    m = re.search(r"\$([\d,]+)", text.replace(",", ""))
    if not m:
        return 0
    try:
        return int(m.group(1))
    except ValueError:
        return 0


def _existing_apply_urls(apps_dir: Path) -> set[str]:
    urls: set[str] = set()
    if not apps_dir.is_dir():
        return urls
    for meta_path in apps_dir.glob("*/meta.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        url = (meta.get("apply_url") or "").strip()
        if url:
            urls.add(url.rstrip("/"))
    return urls


def _generate_bid(job: dict[str, str], score: int) -> str:
    title = job.get("title") or "your project"
    budget = job.get("budget") or "your stated budget"
    return f"""Hi — I'm Cary Jones, a senior Python/backend engineer in Los Angeles (Pacific time). {title} is a strong match for my background: FastAPI/Django microservices, AWS/GCP, LLM integrations, and automation/API work.

Relevant experience:
• Production Python backends at 99.99% uptime (Disney financial reporting; ECS/Fargate microservices)
• ETL/automation pipelines — 2.5M+ daily transactions; PostgreSQL, Redis, external APIs
• LLM/RAG integrations (LangChain, OpenAI/Anthropic) and workflow automation for enterprise clients
• HIPAA-aware API design (Alan Health) — security and auditability for sensitive data

I'd start with a short scope call, then deliver in milestones with clear acceptance criteria. For fixed-price work I need bounded scope — happy to discuss whether {budget} fits after we align on hours and deliverables.

Questions I have:
• What is the target timeline and preferred stack beyond what's in the posting?
• Do you have existing code/repo access ready, or is this greenfield?

I can start within a few days and communicate daily on Freelancer chat.

Cary Jones
cgjonesdev@gmail.com | (626) 272-2567
https://www.linkedin.com/in/cary-g-jones/
https://github.com/cgjonesdev

(Estimated fit score for my profile: {score}% — side-gig/consulting rate ~$100/hr for open-ended work.)
"""


def _write_application(
    apps_dir: Path,
    *,
    slug: str,
    job: dict[str, str],
    score: int,
) -> None:
    today = date.today().isoformat()
    app_dir = apps_dir / slug
    app_dir.mkdir(parents=True, exist_ok=True)

    jd = f"""{job.get('title') or 'Freelancer project'}

Source: {job.get('url')}

Budget: {job.get('budget') or 'Not listed on listing page'}

{job.get('description') or ''}
"""
    meta = {
        "company": "Freelancer",
        "client": None,
        "role": job.get("title") or "Freelancer project",
        "location": "Remote",
        "match_score": score,
        "status": "ready",
        "created": today,
        "updated": today,
        "salary": job.get("budget") or None,
        "styling_notes": None,
        "notes": "Created by Freelancer scan protocol. Paste freelancer_bid.txt into Freelancer proposal. Side-gig/consulting — no full resume unless promoted manually.",
        "apply_url": job.get("url"),
        "apply_method": "freelancer",
    }
    bid = _generate_bid(job, score)

    (app_dir / "jd.txt").write_text(jd.strip() + "\n", encoding="utf-8")
    (app_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    (app_dir / "freelancer_bid.txt").write_text(bid, encoding="utf-8")


def _upload_to_gcs(slug: str, app_dir: Path) -> None:
    if not os.environ.get("GCS_BUCKET", "").strip():
        return
    try:
        import gcs_apps
    except Exception:
        return
    for name in ("jd.txt", "meta.json", "freelancer_bid.txt"):
        path = app_dir / name
        if not path.is_file():
            continue
        gcs_apps.upload_application_file(
            slug,
            name,
            path.read_text(encoding="utf-8"),
            "text/plain; charset=utf-8",
        )


def run_freelancer_scan(
    *,
    repo: Path | None = None,
    max_new: int | None = None,
    min_score: int | None = None,
    upload_gcs: bool | None = None,
) -> dict[str, Any]:
    """Scan Freelancer categories; create application folders for strong matches."""
    root = repo or repo_root()
    apps_dir = root / "applications"
    apps_dir.mkdir(parents=True, exist_ok=True)

    max_new = max_new if max_new is not None else int(os.environ.get("FREELANCER_MAX_PER_RUN", "5"))
    min_score = min_score if min_score is not None else int(os.environ.get("FREELANCER_MATCH_THRESHOLD", "70"))
    if upload_gcs is None:
        upload_gcs = bool(os.environ.get("GCS_BUCKET", "").strip())

    existing_urls = _existing_apply_urls(apps_dir)
    existing_slugs = {p.name for p in apps_dir.iterdir() if p.is_dir()}

    all_jobs: dict[str, dict[str, str]] = {}
    fetch_errors: list[str] = []

    for cat in _categories():
        url = f"https://www.freelancer.com/jobs/{cat}/"
        try:
            html = _fetch(url)
            for job in _parse_cards(html):
                key = job["url"].rstrip("/")
                if key not in all_jobs:
                    all_jobs[key] = job
        except Exception as exc:
            fetch_errors.append(f"{cat}: {exc}")

    ranked: list[tuple[int, dict[str, str]]] = []
    for job in all_jobs.values():
        score = _score_job(job)
        if score >= min_score:
            ranked.append((score, job))
    ranked.sort(key=lambda x: (-x[0], x[1].get("title") or ""))

    generated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for score, job in ranked:
        if len(generated) >= max_new:
            skipped.append(
                {
                    "slug": _slug_from_url(job["url"]),
                    "score": score,
                    "reason": f"cap reached ({max_new}/run)",
                    "apply_url": job["url"],
                }
            )
            continue

        slug = _slug_from_url(job["url"])
        url_norm = job["url"].rstrip("/")

        if url_norm in existing_urls or slug in existing_slugs:
            skipped.append(
                {
                    "slug": slug,
                    "score": score,
                    "reason": "already tracked",
                    "apply_url": job["url"],
                }
            )
            continue

        try:
            _write_application(apps_dir, slug=slug, job=job, score=score)
            if upload_gcs:
                _upload_to_gcs(slug, apps_dir / slug)
            generated.append(
                {
                    "slug": slug,
                    "score": score,
                    "company": "Freelancer",
                    "role": job.get("title"),
                    "apply_url": job["url"],
                    "reason": job.get("budget") or "Remote",
                }
            )
            existing_urls.add(url_norm)
            existing_slugs.add(slug)
        except Exception as exc:
            errors.append({"slug": slug, "error": str(exc), "apply_url": job["url"]})

    for score, job in ranked:
        if score < min_score:
            skipped.append(
                {
                    "slug": _slug_from_url(job["url"]),
                    "score": score,
                    "reason": "below threshold",
                    "apply_url": job["url"],
                }
            )

    return {
        "phase": "freelancer_scan",
        "jobs_found": len(all_jobs),
        "categories": list(_categories()),
        "min_score": min_score,
        "generated": generated,
        "skipped": skipped[:40],
        "errors": errors,
        "fetch_errors": fetch_errors,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
