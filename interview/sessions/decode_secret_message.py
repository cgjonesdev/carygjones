#!/usr/bin/env python3
"""Decode a secret message from a published Google Doc of (x, y, character) points."""

from __future__ import annotations

import re
import sys
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADER_TOKENS = frozenset({"x-coordinate", "character", "y-coordinate"})


def _fetch_html(url: str) -> str:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def _doc_id_from_url(url: str) -> str | None:
    # Standard edit/share URL: /document/d/DOC_ID/...
    match = re.search(r"/document/d/([a-zA-Z0-9_-]+)", url)
    if match and not match.group(1).startswith("e/"):
        return match.group(1)
    return None


def _fetch_export_text(url: str) -> str:
    doc_id = _doc_id_from_url(url)
    if not doc_id:
        raise ValueError("Could not extract document id from URL")
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    response = requests.get(export_url, timeout=30)
    response.raise_for_status()
    return response.text


def _parse_table(soup: BeautifulSoup) -> list[tuple[int, str, int]]:
    points: list[tuple[int, str, int]] = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header = [cell.get_text(strip=True).lower() for cell in rows[0].find_all(["td", "th"])]
        if header[:3] != ["x-coordinate", "character", "y-coordinate"]:
            continue
        for row in rows[1:]:
            cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
            if len(cells) < 3:
                continue
            try:
                x = int(cells[0])
                char = cells[1]
                y = int(cells[2])
            except ValueError:
                continue
            points.append((x, char, y))
        if points:
            return points
    return points


def _parse_text_lines(text: str) -> list[tuple[int, str, int]]:
    points: list[tuple[int, str, int]] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    i = 0
    while i + 2 < len(lines):
        if lines[i].lower() in HEADER_TOKENS:
            i += 1
            continue
        try:
            x = int(lines[i])
            char = lines[i + 1]
            y = int(lines[i + 2])
        except ValueError:
            i += 1
            continue
        if lines[i + 1].lower() in HEADER_TOKENS:
            i += 1
            continue
        points.append((x, char, y))
        i += 3
    return points


def _parse_document(url: str) -> list[tuple[int, str, int]]:
    if "/pub" in url or "pub?" in url:
        soup = BeautifulSoup(_fetch_html(url), "html.parser")
        points = _parse_table(soup)
        if points:
            return points
        text = soup.get_text("\n")
        return _parse_text_lines(text)

    # Standard Google Doc URL → plain-text export
    return _parse_text_lines(_fetch_export_text(url))


def _render_grid(points: list[tuple[int, str, int]]) -> None:
    if not points:
        return
    max_x = max(x for x, _, _ in points)
    max_y = max(y for _, _, y in points)
    grid = [[" " for _ in range(max_x + 1)] for _ in range(max_y + 1)]
    for x, char, y in points:
        grid[y][x] = char
    for row in grid:
        print("".join(row))


def print_secret_message(url: str) -> None:
    """Fetch a Google Doc URL, decode its coordinate grid, and print the message."""
    points = _parse_document(url)
    _render_grid(points)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python decode_secret_message.py <google_doc_url>", file=sys.stderr)
        raise SystemExit(1)
    print_secret_message(sys.argv[1])
