"""Adjust match scores based on Cary's location preferences.

Policy (see also `.prompt` and `tools/cloud_run/README.md`):
- **Remote:** anywhere — no location penalty
- **Onsite / hybrid:** Los Angeles metro or San Francisco Bay Area only — no penalty
- **Onsite / hybrid outside those metros:** match_score × 0.1
"""

from __future__ import annotations

import re

LOCATION_PENALTY = 0.1

# Los Angeles metro + San Francisco Bay Area (incl. common suburbs seen in JDs)
_LA_SF_BAY_RE = re.compile(
    r"""
    los\s+angeles |
    greater\s+los\s+angeles |
    orange\s+county |
    \b(?:pasadena|glendale|burbank|long\s+beach|culver\s+city|santa\s+monica|
       torrance|temple\s+city|alhambra|pomona|irvine|costa\s+mesa|anaheim|
       el\s+segundo|playa\s+vista|west\s+hollywood|beverly\s+hills)\b |
    san\s+francisco |
    (?:^|[\s,/])sf(?:\s+bay|[\s,/]|$) |
    (?:san\s+francisco\s+)?bay\s+area |
    silicon\s+valley |
    \b(?:san\s+jose|oakland|berkeley|palo\s+alto|mountain\s+view|sunnyvale|
       san\s+ramon|fremont|menlo\s+park|redwood\s+city|south\s+san\s+francisco|
       santa\s+clara|cupertino|milpitas|hayward|san\s+mateo|walnut\s+creek|
       pleasanton|dublin|san\s+leandro)\b
    """,
    re.I | re.X,
)

_REMOTE_RE = re.compile(
    r"""
    \bremote\b |
    #LI-Remote |
    work\s+from\s+home |
    \bwfh\b |
    telecommute |
    work\s+anywhere |
    \banywhere\b |
    distributed\s+(?:team|work|workforce) |
    fully?\s+distributed
    """,
    re.I | re.X,
)


def is_la_or_sf_bay(location: str | None) -> bool:
    text = (location or "").strip()
    if not text:
        return False
    return bool(_LA_SF_BAY_RE.search(text))


def is_remote(location: str | None) -> bool:
    """True when the JD indicates remote work (any geography)."""
    text = (location or "").strip()
    if not text:
        return False
    return bool(_REMOTE_RE.search(text))


def is_acceptable_location(location: str | None) -> bool:
    """Remote anywhere, or onsite/hybrid in LA or SF Bay — no penalty."""
    if is_remote(location):
        return True
    return is_la_or_sf_bay(location)


def adjust_match_score(match_score: int | float | None, location: str | None) -> int:
    """Return display/threshold score; penalize onsite/hybrid outside LA or SF Bay."""
    score = int(match_score or 0)
    if is_acceptable_location(location):
        return score
    return max(0, int(round(score * LOCATION_PENALTY)))


def apply_location_to_score_data(
    score_data: dict,
    *,
    threshold: int,
) -> dict:
    """Apply location penalty to OpenAI score payload; keep raw score when adjusted."""
    data = dict(score_data)
    raw = int(data.get("match_score") or 0)
    location = data.get("location") or ""
    adjusted = adjust_match_score(raw, location)
    if adjusted != raw:
        data["raw_match_score"] = raw
    data["match_score"] = adjusted
    data["should_generate"] = adjusted >= threshold
    return data


def display_match_score(meta: dict) -> int | None:
    """Score for admin lists; uses stored adjusted value or recomputes legacy rows."""
    if meta.get("match_score") is None:
        return None
    if meta.get("raw_match_score") is not None:
        return int(meta.get("match_score") or 0)
    return adjust_match_score(meta.get("match_score"), meta.get("location"))
