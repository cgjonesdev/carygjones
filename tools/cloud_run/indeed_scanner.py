"""Scan Indeed job listings via mobile GraphQL API and create triage application folders."""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

import requests

from location_score import adjust_match_score

INDEED_GRAPHQL_URL = "https://apis.indeed.com/graphql"

INDEED_API_HEADERS = {
    "Host": "apis.indeed.com",
    "content-type": "application/json",
    "indeed-api-key": "161092c2017b5bbab13edb12461a62d5a833871e7cad6d9d475304573de67ac8",
    "accept": "application/json",
    "indeed-locale": "en-US",
    "accept-language": "en-US,en;q=0.9",
    "user-agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Indeed App 193.1"
    ),
    "indeed-app-info": "appv=193.1; appid=com.indeed.jobsearch; osv=16.6.1; os=ios; dtype=phone",
    "indeed-co": "US",
}

JOB_SEARCH_QUERY = """
query GetJobData {{
  jobSearch(
    {what}
    {location}
    limit: {limit}
    {cursor}
    sort: RELEVANCE
    {filters}
  ) {{
    pageInfo {{ nextCursor }}
    results {{
      job {{
        key
        title
        datePublished
        description {{ html }}
        location {{
          city
          admin1Code
          countryCode
          formatted {{ short long }}
        }}
        compensation {{
          estimated {{
            currencyCode
            baseSalary {{
              unitOfWork
              range {{ ... on Range {{ min max }} }}
            }}
          }}
        }}
        attributes {{ key label }}
        employer {{ name }}
      }}
    }}
  }}
}}
"""

SCORE_KEYWORDS: list[tuple[str, int]] = [
    ("python", 10),
    ("django", 10),
    ("fastapi", 10),
    ("backend", 8),
    ("software engineer", 10),
    ("full stack", 8),
    ("microservice", 8),
    ("aws", 8),
    ("kubernetes", 6),
    ("postgresql", 6),
    ("llm", 8),
    ("langchain", 8),
    ("machine learning", 6),
    ("api", 4),
    ("remote", 6),
    ("hybrid", 4),
    ("senior", 4),
    ("staff", 4),
    ("principal", 4),
]

SKIP_KEYWORDS = (
    "warehouse",
    "driver",
    "cdl ",
    "nurse",
    "dental assistant",
    "retail",
    "cashier",
    "security guard",
    "forklift",
    "cleaning",
    "housekeeper",
    "sales associate",
)


def repo_root() -> Path:
    for key in ("REPO_ROOT", "ASSETS_DIR"):
        val = os.environ.get(key, "").strip()
        if val:
            return Path(val)
    return Path(__file__).resolve().parents[2]


def _search_query() -> str:
    return os.environ.get("INDEED_SEARCH_QUERY", "python developer").strip()


def _search_location() -> str:
    return os.environ.get("INDEED_SEARCH_LOCATION", "Los Angeles, CA").strip()


def _search_radius() -> int:
    return int(os.environ.get("INDEED_SEARCH_RADIUS", "25"))


def _days_old() -> str:
    days = os.environ.get("INDEED_DAYS_OLD", "7").strip()
    return f"{days}d" if days.isdigit() else days


def _strip_html(html: str) -> str:
    text = unescape(re.sub(r"<[^>]+>", " ", html or ""))
    return re.sub(r"\s+", " ", text).strip()


def _format_location(job: dict[str, Any]) -> str:
    loc = job.get("location") or {}
    formatted = loc.get("formatted") or {}
    short = (formatted.get("short") or formatted.get("long") or "").strip()
    if short:
        return short
    parts = [loc.get("city"), loc.get("admin1Code"), loc.get("countryCode")]
    return ", ".join(p for p in parts if p)


def _format_salary(job: dict[str, Any]) -> str | None:
    comp = job.get("compensation") or {}
    est = comp.get("estimated") or {}
    base = est.get("baseSalary") or {}
    rng = base.get("range") or {}
    unit = base.get("unitOfWork") or ""
    currency = est.get("currencyCode") or "USD"
    min_val = rng.get("min")
    max_val = rng.get("max")
    if min_val and max_val:
        return f"${min_val:,.0f}–${max_val:,.0f} {currency} ({unit})".replace("  ", " ")
    if min_val:
        return f"${min_val:,.0f}+ {currency} ({unit})".replace("  ", " ")
    return None


def _heuristic_score(title: str, description: str) -> int:
    blob = f"{title} {description}".lower()
    for bad in SKIP_KEYWORDS:
        if bad in blob:
            return max(0, 30)
    score = 45
    for keyword, weight in SCORE_KEYWORDS:
        if keyword in blob:
            score += weight
    if "remote" in blob:
        score += 4
    return min(92, score)


def _graphql_search(*, cursor: str | None = None, limit: int = 25) -> dict[str, Any]:
    term = _search_query().replace('"', '\\"')
    location = _search_location().replace('"', '\\"')
    query = JOB_SEARCH_QUERY.format(
        what=f'what: "{term}"' if term else "",
        location=(
            f'location: {{where: "{location}", radius: {_search_radius()}, radiusUnit: MILES}}'
            if location
            else ""
        ),
        limit=limit,
        cursor=f'cursor: "{cursor}"' if cursor else "",
        filters=f"""
        filters: {{
          date: {{
            field: "dateOnIndeed",
            start: "{_days_old()}"
          }}
        }}
        """,
    )
    headers = {**INDEED_API_HEADERS, "indeed-co": "US"}
    resp = requests.post(
        INDEED_GRAPHQL_URL,
        headers=headers,
        json={"query": query},
        timeout=45,
    )
    if not resp.ok:
        raise RuntimeError(f"Indeed GraphQL HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    if data.get("errors"):
        raise RuntimeError(f"Indeed GraphQL error: {data['errors']}")
    return data["data"]["jobSearch"]


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
            jk = re.search(r"[?&]jk=([a-f0-9]+)", url)
            if jk:
                urls.add(f"https://www.indeed.com/viewjob?jk={jk.group(1)}")
    return urls


def _slug_for_job(job_key: str, company: str) -> str:
    co = re.sub(r"[^a-z0-9]+", "_", (company or "unknown").lower()).strip("_")[:30]
    return f"indeed_{co}_{job_key[:12]}" if co else f"indeed_{job_key}"


def _write_application(
    apps_dir: Path,
    *,
    slug: str,
    job: dict[str, Any],
    score: int,
    apply_url: str,
) -> None:
    today = date.today().isoformat()
    app_dir = apps_dir / slug
    app_dir.mkdir(parents=True, exist_ok=True)

    title = job.get("title") or "Indeed job"
    company = (job.get("employer") or {}).get("name") or "Unknown"
    location = _format_location(job)
    salary = _format_salary(job)
    description = _strip_html((job.get("description") or {}).get("html") or "")

    jd = f"""{title}
{company}

Source: {apply_url}

Location: {location}
Compensation: {salary or "Not listed"}

{description}
"""
    meta = {
        "company": company,
        "client": None,
        "role": title,
        "location": location,
        "match_score": score,
        "status": "ready",
        "created": today,
        "updated": today,
        "salary": salary,
        "styling_notes": None,
        "notes": (
            f"Created by Indeed scan ({_search_query()} · {_search_location()}). "
            f"Score {score}%. Promote to full application manually or via Generate when ≥80%."
        ),
        "apply_url": apply_url,
        "apply_method": "indeed",
        "indeed_job_id": job.get("key"),
    }

    (app_dir / "jd.txt").write_text(jd.strip() + "\n", encoding="utf-8")
    (app_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def _upload_to_gcs(slug: str, app_dir: Path) -> None:
    if not os.environ.get("GCS_BUCKET", "").strip():
        return
    try:
        import gcs_apps
    except Exception:
        return
    for name in ("jd.txt", "meta.json"):
        path = app_dir / name
        if path.is_file():
            gcs_apps.upload_application_file(
                slug,
                name,
                path.read_text(encoding="utf-8"),
                "text/plain; charset=utf-8" if name.endswith(".txt") else "application/json",
            )


def run_indeed_scan(
    *,
    repo: Path | None = None,
    max_new: int | None = None,
    min_score: int | None = None,
    max_results: int | None = None,
    upload_gcs: bool | None = None,
) -> dict[str, Any]:
    root = repo or repo_root()
    apps_dir = root / "applications"
    apps_dir.mkdir(parents=True, exist_ok=True)

    max_new = max_new if max_new is not None else int(os.environ.get("INDEED_MAX_PER_RUN", "5"))
    min_score = min_score if min_score is not None else int(os.environ.get("INDEED_MATCH_THRESHOLD", "70"))
    max_results = max_results if max_results is not None else int(os.environ.get("INDEED_MAX_RESULTS", "50"))
    if upload_gcs is None:
        upload_gcs = bool(os.environ.get("GCS_BUCKET", "").strip())

    existing_urls = _existing_apply_urls(apps_dir)
    existing_slugs = {p.name for p in apps_dir.iterdir() if p.is_dir()}

    ranked: list[tuple[int, dict[str, Any], str]] = []
    fetch_errors: list[str] = []
    cursor: str | None = None
    fetched = 0

    while fetched < max_results:
        try:
            page = _graphql_search(cursor=cursor, limit=min(25, max_results - fetched))
        except Exception as exc:
            fetch_errors.append(str(exc))
            break

        results = page.get("results") or []
        if not results:
            break
        fetched += len(results)

        for row in results:
            job = row.get("job") or {}
            key = job.get("key")
            if not key:
                continue
            apply_url = f"https://www.indeed.com/viewjob?jk={key}"
            if apply_url.rstrip("/") in existing_urls:
                continue
            title = job.get("title") or ""
            description = _strip_html((job.get("description") or {}).get("html") or "")
            raw_score = _heuristic_score(title, description)
            location = _format_location(job)
            score = adjust_match_score(raw_score, location)
            if score >= min_score:
                ranked.append((score, job, apply_url))

        cursor = (page.get("pageInfo") or {}).get("nextCursor")
        if not cursor:
            break

    ranked.sort(key=lambda x: (-x[0], x[1].get("title") or ""))

    generated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for score, job, apply_url in ranked:
        if len(generated) >= max_new:
            skipped.append(
                {
                    "slug": _slug_for_job(job.get("key", ""), (job.get("employer") or {}).get("name") or ""),
                    "score": score,
                    "reason": f"cap reached ({max_new}/run)",
                    "apply_url": apply_url,
                }
            )
            continue

        company = (job.get("employer") or {}).get("name") or "Unknown"
        slug = _slug_for_job(job.get("key", ""), company)
        url_norm = apply_url.rstrip("/")

        if url_norm in existing_urls or slug in existing_slugs:
            skipped.append(
                {"slug": slug, "score": score, "reason": "already tracked", "apply_url": apply_url}
            )
            continue

        try:
            _write_application(apps_dir, slug=slug, job=job, score=score, apply_url=apply_url)
            if upload_gcs:
                _upload_to_gcs(slug, apps_dir / slug)
            generated.append(
                {
                    "slug": slug,
                    "score": score,
                    "company": company,
                    "role": job.get("title"),
                    "apply_url": apply_url,
                    "reason": _format_location(job) or "Indeed",
                }
            )
            existing_urls.add(url_norm)
            existing_slugs.add(slug)
        except Exception as exc:
            errors.append({"slug": slug, "error": str(exc), "apply_url": apply_url})

    return {
        "phase": "indeed_scan",
        "jobs_found": fetched,
        "search_query": _search_query(),
        "search_location": _search_location(),
        "min_score": min_score,
        "generated": generated,
        "skipped": skipped[:40],
        "errors": errors,
        "fetch_errors": fetch_errors,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
