"""Normalize cover letter HTML layout (block sender lines, no justified headers)."""

from __future__ import annotations

import re

CSS_MARKER = "/* cover-letter-block-layout */"

BLOCK_CLASSES = ("sender", "meta", "subject", "closing")

INJECTED_CSS = f"""
      {CSS_MARKER}
      .sender,
      .meta,
      .subject,
      .closing {{
        text-align: left;
      }}
"""


def _split_pipe_lines(segment: str) -> str:
    if " | " not in segment:
        return segment
    parts = [part.strip() for part in segment.split(" | ") if part.strip()]
    if len(parts) <= 1:
        return segment
    return "<br>\n    ".join(parts)


def _normalize_block_inner(html: str) -> str:
    chunks = re.split(r"(<br\s*/?>)", html, flags=re.IGNORECASE)
    out: list[str] = []
    for chunk in chunks:
        if re.fullmatch(r"<br\s*/?>", chunk, flags=re.IGNORECASE):
            out.append(chunk)
        else:
            out.append(_split_pipe_lines(chunk))
    return "".join(out)


def _normalize_block_paragraphs(html: str) -> str:
    for cls in BLOCK_CLASSES:
        pattern = rf'(<p class="{cls}"[^>]*>)(.*?)(</p>)'

        def repl(match: re.Match[str]) -> str:
            return match.group(1) + _normalize_block_inner(match.group(2)) + match.group(3)

        html = re.sub(pattern, repl, html, flags=re.DOTALL | re.IGNORECASE)
    return html


def _inject_block_css(html: str) -> str:
    if CSS_MARKER in html:
        return html
    if "</style>" not in html:
        return html
    return html.replace("</style>", INJECTED_CSS + "    </style>", 1)


def normalize_cover_letter_html(html: str) -> str:
    """Ensure sender/meta blocks are left-aligned with one contact item per line."""
    if not html or not html.strip():
        return html
    normalized = _normalize_block_paragraphs(html)
    return _inject_block_css(normalized)
