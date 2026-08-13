"""OpenAI scoring and application generation."""

from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

from openai import OpenAI

from prompts import GENERATE_SYSTEM, SCORE_SYSTEM
from location_score import apply_location_to_score_data

MATCH_THRESHOLD = int(os.environ.get("MATCH_THRESHOLD", "80"))


def assets_dir() -> Path:
    if os.environ.get("ASSETS_DIR"):
        return Path(os.environ["ASSETS_DIR"])
    return Path(__file__).resolve().parents[2]


def _load_context() -> str:
    root = assets_dir()
    base_resume = root / "base" / "cary_jones_resume.html"
    if not base_resume.exists():
        base_resume = root / "cary_jones_resume.html"
    contact_json = root / "website" / "contact.json"
    if not contact_json.exists():
        contact_json = root / "contact.json"
    example = root / "applications" / "weave" / "resume.html"
    if not example.exists():
        example = root / "examples" / "weave" / "resume.html"

    parts: list[str] = []
    if base_resume.exists():
        text = base_resume.read_text(encoding="utf-8")
        parts.append("BASE RESUME HTML (source of truth for experience):\n" + text[:120000])
    if contact_json.exists():
        parts.append("CONTACT JSON:\n" + contact_json.read_text(encoding="utf-8"))
    if example.exists():
        parts.append(
            "EXAMPLE TAILORED RESUME (style reference):\n"
            + example.read_text(encoding="utf-8")[:40000]
        )
    return "\n\n".join(parts)


def _client() -> OpenAI:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required for generation.")
    return OpenAI(api_key=key)


def _model(kind: str) -> str:
    if kind == "score":
        return os.environ.get("OPENAI_MODEL_SCORE", "gpt-4o-mini")
    return os.environ.get("OPENAI_MODEL_GENERATE", "gpt-4o")


def _parse_json(content: str) -> dict[str, Any]:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
    return json.loads(content)


def score_jd(jd_text: str, subject: str = "", apply_url: str | None = None) -> dict[str, Any]:
    user = f"Subject: {subject}\nApply URL: {apply_url or 'unknown'}\n\nJD:\n{jd_text[:60000]}"
    resp = _client().chat.completions.create(
        model=_model("score"),
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SCORE_SYSTEM + "\n\n" + _load_context()},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    data = _parse_json(resp.choices[0].message.content or "{}")
    return apply_location_to_score_data(data, threshold=MATCH_THRESHOLD)


def generate_application(
    jd_text: str,
    score_data: dict[str, Any],
    apply_url: str | None = None,
) -> dict[str, Any]:
    today = date.today().isoformat()
    user = json.dumps(
        {
            "today": today,
            "jd": jd_text[:60000],
            "score_result": score_data,
            "apply_url": apply_url,
        },
        indent=2,
    )
    resp = _client().chat.completions.create(
        model=_model("generate"),
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": GENERATE_SYSTEM + "\n\n" + _load_context()},
            {"role": "user", "content": user},
        ],
        temperature=0.4,
    )
    data = _parse_json(resp.choices[0].message.content or "{}")
    cover = data.get("cover_letter_html")
    if isinstance(cover, str) and cover.strip():
        from cover_letter_html import normalize_cover_letter_html

        data["cover_letter_html"] = normalize_cover_letter_html(cover)
    return data


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:48] or "company"
