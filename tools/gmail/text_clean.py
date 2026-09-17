"""Normalize recruiter email bodies and job description text."""

from __future__ import annotations

import re
from html import unescape

TAG_RE = re.compile(r"<[^>]+>")
STYLE_BLOCK_RE = re.compile(r"<style[^>]*>.*?</style>", re.I | re.S)
SCRIPT_BLOCK_RE = re.compile(r"<script[^>]*>.*?</script>", re.I | re.S)
NBSP_ARTIFACT_RE = re.compile(r"(?<=[A-Za-z])a0(?=[A-Za-z])")
CSS_LINE_RE = re.compile(
    r"^\s*("
    r"@import\b|"
    r"@media\b|"
    r"@keyframes\b|"
    r"[\w.#][\w\s\-.,#'\"():/]*\{[^}]*\}|"
    r"[\w.#][\w\s\-.,#'\"():/]*,\s*[\w.#][\w\s\-.,#'\"():/]*\{"
    r")",
    re.I,
)
UNSUBSCRIBE_RE = re.compile(
    r"\n\s*to unsubscribe from future emails.*$",
    re.I | re.S,
)
JD_START_RE = re.compile(
    r"(?:"
    r"hello\b|"
    r"hi\b|"
    r"dear\b|"
    r"subject:|"
    r"position:|"
    r"job description|"
    r"about the role|"
    r"responsibilities|"
    r"requirements|"
    r"qualifications|"
    r"location:|"
    r"duration:|"
    r"source:"
    r")",
    re.I,
)


def html_to_plain_text(raw: str) -> str:
    if not raw:
        return ""
    text = SCRIPT_BLOCK_RE.sub(" ", raw)
    text = STYLE_BLOCK_RE.sub(" ", text)
    text = TAG_RE.sub(" ", unescape(text))
    return normalize_whitespace(text)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\u00a0", " ")
    text = NBSP_ARTIFACT_RE.sub(" ", text)
    text = text.replace("a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_email_boilerplate(text: str) -> str:
    if not text:
        return ""
    text = UNSUBSCRIBE_RE.sub("", text)
    lines = [ln.strip() for ln in text.splitlines()]
    kept: list[str] = []
    started = False
    for line in lines:
        if not line:
            if started and kept and kept[-1]:
                kept.append("")
            continue
        if line.lower().startswith("your email title"):
            continue
        if not started:
            if CSS_LINE_RE.match(line):
                continue
            if line.lower().startswith("your email title"):
                continue
            if JD_START_RE.search(line):
                started = True
            elif len(line) > 120 and "{" in line and ";" in line:
                continue
            else:
                started = True
        if CSS_LINE_RE.match(line):
            continue
        kept.append(line)
    text = "\n".join(kept).strip()
    return normalize_whitespace(text)


def clean_email_body(text: str) -> str:
    if not text:
        return ""
    if "<" in text and ">" in text:
        text = html_to_plain_text(text)
    text = normalize_whitespace(text)
    return strip_email_boilerplate(text)


def clean_jd_text(text: str) -> str:
    return clean_email_body(text)
