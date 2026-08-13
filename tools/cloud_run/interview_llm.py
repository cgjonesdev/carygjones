"""Interview prep LLM — context from GCS application artifacts."""

from __future__ import annotations

import os
from typing import Any

import gcs_apps
from openai_tailor import _client, _model

MODES = frozenset({"assistant", "mock_question", "expand_notes", "debrief"})

SYSTEM = """You are Cary Jones's interview prep assistant. Cary is a senior Python/AWS engineer.

Use the job description, resume excerpt, and existing interview notes as context.
Be concise and actionable. For mock questions, ask ONE question at a time unless the user requests a list.
For expand_notes, polish and structure Cary's rough notes without inventing facts he did not mention.
For debrief, highlight strengths, gaps, and follow-up actions after an interview round."""


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _load_context(slug: str) -> tuple[dict[str, Any], str]:
    meta = gcs_apps.load_app_meta(slug)
    if not meta:
        raise ValueError(f"Application not found: {slug}")

    jd = gcs_apps.download_text(f"{gcs_apps.APPS_PREFIX}/{slug}/jd.txt") or ""
    resume = gcs_apps.download_text(f"{gcs_apps.APPS_PREFIX}/{slug}/resume.html") or ""
    notes = str(meta.get("interview_notes") or "").strip()

    company = meta.get("company") or slug
    role = meta.get("role") or ""
    status = meta.get("status") or ""

    context = (
        f"Company: {company}\n"
        f"Role: {role}\n"
        f"Status: {status}\n"
        f"Interview URL: {meta.get('interview_url') or 'n/a'}\n\n"
        f"JD excerpt:\n{_truncate(jd, 12000)}\n\n"
        f"Resume excerpt:\n{_truncate(resume, 12000)}\n\n"
        f"Interview notes:\n{_truncate(notes, 8000) or '(none yet)'}"
    )
    return meta, context


def run_interview_chat(slug: str, message: str, *, mode: str = "assistant") -> dict[str, Any]:
    mode = (mode or "assistant").strip().lower()
    if mode not in MODES:
        return {"error": f"Invalid mode {mode!r}. Allowed: {', '.join(sorted(MODES))}"}

    message = (message or "").strip()
    if not message:
        return {"error": "Message is required."}

    try:
        _, context = _load_context(slug)
    except ValueError as exc:
        return {"error": str(exc)}

    mode_hint = {
        "assistant": "Answer Cary's question using the context.",
        "mock_question": "Ask the next realistic interview question for this role. One question only.",
        "expand_notes": "Rewrite Cary's notes into clear bullet sections (questions asked, my answers, follow-ups).",
        "debrief": "Summarize how the interview likely went and what to review before the next round.",
    }[mode]

    model = os.environ.get("OPENAI_MODEL_INTERVIEW", _model("score"))
    resp = _client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"{context}\n\n---\nMode: {mode}\n{mode_hint}\n\nCary: {message}"},
        ],
        temperature=0.4,
    )
    reply = (resp.choices[0].message.content or "").strip()
    if not reply:
        return {"error": "Empty response from model."}
    return {"reply": reply, "mode": mode, "model": model, "slug": slug}
