"""Scan Craigslist gigs listings and create reply-ready application folders."""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import date, datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_SEARCH_REGIONS: list[tuple[str, str]] = [
    ("LA Central gigs", "https://www.craigslist.org/search/subarea/lac?cat=ggg"),
    ("SF Bay Area gigs", "https://sfbay.craigslist.org/search/ggg"),
    ("San Diego gigs", "https://sandiego.craigslist.org/search/ggg"),
]

# Backward compat for callers/tests that referenced a single default URL.
DEFAULT_SEARCH_URL = DEFAULT_SEARCH_REGIONS[0][1]

CARY_KEYWORDS: list[tuple[str, int]] = [
    ("python", 10),
    ("automation", 10),
    ("web developer", 12),
    ("software", 10),
    ("crm", 8),
    ("api", 6),
    ("squarespace", 10),
    ("mailchimp", 8),
    ("wordpress", 6),
    ("subcontract", 8),
    ("sub contract", 8),
    ("integration", 8),
    ("computer", 6),
    ("tech", 5),
    ("property manager", 12),
    ("apartment manager", 12),
    ("resident manager", 12),
    ("onsite manager", 10),
    ("live-in", 8),
    ("appfolio", 10),
    ("document retrieval", 12),
    ("clerk", 6),
    ("due diligence", 8),
    ("acquisitions", 8),
    ("archive", 6),
    ("consultant", 5),
    ("backend", 8),
    ("developer", 6),
]

COUPLE_KEYWORDS: list[tuple[str, int]] = [
    ("live-in couple", 15),
    ("couple wanted", 12),
    ("couple needed", 12),
    ("two people", 8),
    ("deep clean", 10),
    ("deep cleaning", 10),
    ("housekeeper", 8),
    ("housekeeping", 8),
    ("property manager", 6),
    ("resident manager", 6),
]

YIN_CHEN_KEYWORDS: list[tuple[str, int]] = [
    ("cooking", 10),
    ("chef", 10),
    ("personal assistant", 8),
    ("cleaning", 8),
    ("housekeeping", 8),
    ("meal prep", 8),
    ("kitchen", 6),
]

SKIP_KEYWORDS = (
    "clinical trial",
    "sperm donor",
    "sperm ",
    "focus group",
    "mock jury",
    "anxiety study",
    "dental study",
    "paid clinical",
    "body double",
    "nudity",
    "content creator",
    "onlyfans",
    "actor needed",
    "actress",
    "model",
    "dancer",
    "bartender",
    "karaoke hostess",
    "earn up to",
    "smile fix",
    "schizophrenia",
    "film karol",
    "lawn care companies fill in",
)

SPAM_TITLE_RE = re.compile(
    r"earn \$|easy \$|\$0\s+(?:los angeles|orange|inglewood)",
    re.I,
)

LISTING_LINK_RE = re.compile(
    r'<a href="(https://[^"]+/view/d/[^"]+)"[^>]*>(.*?)</a>',
    re.I | re.S,
)


def repo_root() -> Path:
    for key in ("REPO_ROOT", "ASSETS_DIR"):
        val = os.environ.get(key, "").strip()
        if val:
            return Path(val)
    return Path(__file__).resolve().parents[2]


def search_regions() -> list[tuple[str, str]]:
    """Return (label, search_url) pairs. Override with CRAIGSLIST_SEARCH_URL (single URL)."""
    raw = os.environ.get("CRAIGSLIST_SEARCH_URL", "").strip()
    if raw:
        return [("Craigslist gigs", raw)]
    return list(DEFAULT_SEARCH_REGIONS)


def search_url() -> str:
    return search_regions()[0][1]


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


def _parse_search_listings(html: str) -> list[dict[str, str]]:
    listings: dict[str, dict[str, str]] = {}
    for match in LISTING_LINK_RE.finditer(html):
        url = match.group(1).split("#")[0].strip()
        title = unescape(re.sub(r"<[^>]+>", " ", match.group(2)))
        title = re.sub(r"\s+", " ", title).strip()
        if not title or len(title) < 8:
            continue
        if url not in listings:
            listings[url] = {"title": title, "url": url, "description": ""}
    return list(listings.values())


def _fetch_listing_body(url: str) -> tuple[str, str]:
    html = _fetch(url)
    title_match = re.search(r'id="postingtitletext"[^>]*>(.*?)</span>', html, re.S)
    if not title_match:
        title_match = re.search(r"<span id=\"titletextonly\">(.*?)</span>", html, re.S)
    title = ""
    if title_match:
        title = unescape(re.sub(r"<[^>]+>", " ", title_match.group(1)))
        title = re.sub(r"\s+", " ", title).strip()
    body_match = re.search(r'id="postingbody"[^>]*>(.*?)</section>', html, re.S)
    body = ""
    if body_match:
        body = unescape(re.sub(r"<[^>]+>", " ", body_match.group(1)))
        body = re.sub(r"\s+", " ", body).strip()
    return title, body


def _slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    tail = path.split("/d/")[-1].split("/")[0] if "/d/" in path else path
    base = re.sub(r"[^a-z0-9]+", "_", tail.lower()).strip("_")
    base = re.sub(r"^(los_angeles|los-angeles|central_la|la)_+", "", base)
    base = base[:55] or "gig"
    return f"craigslist_{base}"


def _parse_price(text: str) -> str | None:
    amounts = re.findall(r"\$(\d[\d,]*)", text.replace(",", ""))
    if not amounts:
        return None
    nums = [int(a) for a in amounts if int(a) > 0]
    if not nums:
        return None
    if len(nums) >= 2 and "hour" in text.lower():
        return f"${nums[0]}/hr (from listing)"
    return f"${max(nums)}"


def _score_listing(title: str, body: str) -> tuple[int, str]:
    blob = f"{title} {body}".lower()
    if SPAM_TITLE_RE.search(blob):
        return 0, "cary"
    for bad in SKIP_KEYWORDS:
        if bad in blob:
            return max(0, 25), "cary"

    cary = 35
    couple = 30
    yin = 30
    for keyword, weight in CARY_KEYWORDS:
        if keyword in blob:
            cary += weight
    for keyword, weight in COUPLE_KEYWORDS:
        if keyword in blob:
            couple += weight
    for keyword, weight in YIN_CHEN_KEYWORDS:
        if keyword in blob:
            yin += weight

    if "english speaking only" in blob and ("clean" in blob or "cooking" in blob):
        yin += 5

    scores = {"cary": min(92, cary), "couple": min(92, couple), "yin-chen": min(92, yin)}
    profile = max(scores, key=scores.get)
    return scores[profile], profile


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


def _location_from_title(title: str) -> str:
    parts = title.rsplit("$", 1)
    if len(parts) == 2 and parts[1].strip():
        loc = parts[1].strip()
        if len(loc) <= 80:
            return loc
    lower = title.lower()
    if "san diego" in lower:
        return "San Diego area"
    if any(
        token in lower
        for token in ("san francisco", "sf bay", "bay area", "oakland", "berkeley", "peninsula")
    ):
        return "SF Bay Area"
    if "los angeles" in lower:
        return "Los Angeles area"
    return "Southern California (in-person likely)"


def _role_from_title(title: str) -> str:
    role = title.split("$")[0].strip()
    role = re.sub(r"^\W+|\W+$", "", role)
    return role[:120] or "Craigslist gig"


def _generate_reply(job: dict[str, str], score: int, profile: str) -> str:
    role = job.get("title") or job.get("role") or "your posting"
    price = job.get("price") or "your stated rate"

    if profile == "couple":
        return f"""Subject: {role} — live-in couple available immediately

Dear Hiring Manager,

We are Cary and Yin-Chen Jones, a professional live-in couple based in the Los Angeles area (Temple City). Your posting for {role} looks like a strong fit for how we work together.

Yin-Chen brings Culinary Institute of America training, Michelin-level kitchen experience, and meticulous interior/housekeeping standards. Cary handles exterior/grounds coordination, maintenance triage, AppFolio-style property workflows, and reliable on-site reporting. Together we have 20+ completed live-in house sits and 17+ five-star TrustedHousesitters reviews.

Portfolio: https://housesitting.onrender.com/
TrustedHousesitters: https://www.trustedhousesitters.com/house-and-pet-sitters/united-states/california/pasadena/l/2258552/

We are non-smokers, have no pets, communicate clearly, and leave homes cleaner than we found them. Available live-in immediately.

Happy to meet, walk the property, and discuss {price} and scope at your convenience.

Cary Jones & Yin-Chen Jones
(626) 272-2567 · cgjonesdev@gmail.com
"""

    if profile == "yin-chen":
        return f"""Subject: {role} — household / culinary support

Dear Hiring Manager,

I am Yin-Chen Jones, a CIA-trained chef with a B.S. in Hospitality Management (Cal Poly Pomona) and extensive experience in private households, luxury hospitality, and meticulous cleaning/organization. I am interested in your Craigslist posting for {role}.

I bring professional kitchen skills, reliable household standards, and calm, discreet communication with residents. I am based in the Los Angeles area with reliable transportation and can discuss on-site availability and {price} before we start.

Happy to share more detail and meet at your convenience.

Yin-Chen Jones
(626) 272-2567 · cgjonesdev@gmail.com
"""

    return f"""Subject: {role} — interested, available in LA area

Dear Hiring Manager,

I am interested in your Craigslist posting for {role}.

I am Cary Jones, a senior software engineer and independent consultant in Temple City (Los Angeles County) with 15+ years of professional experience. Relevant background includes Python/automation, web and CRM integrations, AppFolio property workflows, real-estate acquisitions/due diligence, and reliable on-site work when needed.

I communicate promptly, follow direction well, and am comfortable discussing scope and {price} before starting. Based in Temple City with valid driver's license and reliable transportation.

Happy to talk through details and next steps at your convenience.

Cary Jones
(626) 272-2567
cgjonesdev@gmail.com
https://www.linkedin.com/in/cary-g-jones/

(Estimated fit score for my profile: {score}% — side-gig/consulting ~$100/hr when scope is open-ended.)
"""


def _write_application(
    apps_dir: Path,
    *,
    slug: str,
    job: dict[str, str],
    score: int,
    profile: str,
    region_label: str = "LA Central gigs",
) -> None:
    today = date.today().isoformat()
    app_dir = apps_dir / slug
    app_dir.mkdir(parents=True, exist_ok=True)

    role = _role_from_title(job.get("title") or "")
    location = _location_from_title(job.get("title") or "")
    price = _parse_price(f"{job.get('title') or ''} {job.get('description') or ''}")

    jd = f"""{role}

Source: {job.get('url')}

Compensation: {price or 'Not stated on listing'}

{job.get('description') or job.get('title') or ''}
"""
    meta = {
        "company": f"Craigslist — private ({region_label})",
        "client": None,
        "role": role,
        "location": location,
        "match_score": score,
        "match_profile": profile,
        "status": "ready",
        "created": today,
        "updated": today,
        "salary": price,
        "styling_notes": None,
        "notes": f"Created by Craigslist {region_label} scan. Paste craigslist_reply.txt into Craigslist reply. Review and personalize before sending.",
        "apply_url": job.get("url"),
        "apply_method": "craigslist",
    }
    reply = _generate_reply({**job, "role": role, "price": price or "your budget"}, score, profile)

    (app_dir / "jd.txt").write_text(jd.strip() + "\n", encoding="utf-8")
    (app_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    (app_dir / "craigslist_reply.txt").write_text(reply, encoding="utf-8")


def _upload_to_gcs(slug: str, app_dir: Path) -> None:
    if not os.environ.get("GCS_BUCKET", "").strip():
        return
    try:
        import gcs_apps
    except Exception:
        return
    for name in ("jd.txt", "meta.json", "craigslist_reply.txt"):
        path = app_dir / name
        if not path.is_file():
            continue
        gcs_apps.upload_application_file(
            slug,
            name,
            path.read_text(encoding="utf-8"),
            "text/plain; charset=utf-8",
        )


def run_craigslist_scan(
    *,
    repo: Path | None = None,
    max_new: int | None = None,
    min_score: int | None = None,
    max_detail_fetches: int | None = None,
    upload_gcs: bool | None = None,
) -> dict[str, Any]:
    root = repo or repo_root()
    apps_dir = root / "applications"
    apps_dir.mkdir(parents=True, exist_ok=True)

    max_new = max_new if max_new is not None else int(os.environ.get("CRAIGSLIST_MAX_PER_RUN", "5"))
    min_score = min_score if min_score is not None else int(os.environ.get("CRAIGSLIST_MATCH_THRESHOLD", "60"))
    max_detail_fetches = max_detail_fetches if max_detail_fetches is not None else int(
        os.environ.get("CRAIGSLIST_MAX_DETAIL_FETCHES", "35")
    )
    if upload_gcs is None:
        upload_gcs = bool(os.environ.get("GCS_BUCKET", "").strip())

    url = search_url()
    regions = search_regions()
    fetch_errors: list[str] = []
    listings: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for region_label, region_url in regions:
        try:
            html = _fetch(region_url)
            for job in _parse_search_listings(html):
                url_norm = job["url"].rstrip("/")
                if url_norm in seen_urls:
                    continue
                seen_urls.add(url_norm)
                listings.append({**job, "region": region_label})
        except Exception as exc:
            fetch_errors.append(f"{region_label} ({region_url}): {exc}")

    existing_urls = _existing_apply_urls(apps_dir)
    existing_slugs = {p.name for p in apps_dir.iterdir() if p.is_dir()}

    title_ranked: list[tuple[int, dict[str, str], str]] = []
    for job in listings:
        score, profile = _score_listing(job["title"], "")
        if score >= 40:
            title_ranked.append((score, job, profile))
    title_ranked.sort(key=lambda x: (-x[0], x[1].get("title") or ""))

    detailed: list[tuple[int, dict[str, str], str]] = []
    fetches = 0
    for score, job, profile in title_ranked:
        if fetches >= max_detail_fetches:
            break
        url_norm = job["url"].rstrip("/")
        if url_norm in existing_urls:
            continue
        try:
            detail_title, body = _fetch_listing_body(job["url"])
            if detail_title:
                job = {**job, "title": detail_title}
            job["description"] = body[:2000]
            score, profile = _score_listing(job["title"], body)
            fetches += 1
        except Exception as exc:
            fetch_errors.append(f"{job['url']}: {exc}")
            continue
        if score >= min_score:
            detailed.append((score, job, profile))

    detailed.sort(key=lambda x: (-x[0], x[1].get("title") or ""))

    generated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for score, job, profile in detailed:
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
            _write_application(
                apps_dir,
                slug=slug,
                job=job,
                score=score,
                profile=profile,
                region_label=job.get("region") or "Craigslist gigs",
            )
            if upload_gcs:
                _upload_to_gcs(slug, apps_dir / slug)
            generated.append(
                {
                    "slug": slug,
                    "score": score,
                    "company": "Craigslist",
                    "role": _role_from_title(job.get("title") or ""),
                    "apply_url": job["url"],
                    "reason": profile,
                }
            )
            existing_urls.add(url_norm)
            existing_slugs.add(slug)
        except Exception as exc:
            errors.append({"slug": slug, "error": str(exc), "apply_url": job["url"]})

    for score, job, profile in title_ranked:
        if score < min_score:
            skipped.append(
                {
                    "slug": _slug_from_url(job["url"]),
                    "score": score,
                    "reason": "below threshold (title-only)",
                    "apply_url": job["url"],
                }
            )

    return {
        "phase": "craigslist_scan",
        "jobs_found": len(listings),
        "search_url": url,
        "search_regions": [{"label": label, "url": region_url} for label, region_url in regions],
        "min_score": min_score,
        "generated": generated,
        "skipped": skipped[:40],
        "errors": errors,
        "fetch_errors": fetch_errors,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
