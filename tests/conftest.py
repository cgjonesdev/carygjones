"""Shared pytest fixtures and import path setup."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLOUD_RUN = ROOT / "tools" / "cloud_run"
GMAIL = ROOT / "tools" / "gmail"
SCRIPTS = ROOT / "scripts"

for path in (CLOUD_RUN, GMAIL, SCRIPTS):
    entry = str(path)
    if entry not in sys.path:
        sys.path.insert(0, entry)


@pytest.fixture
def repo_root() -> Path:
    return ROOT


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def load_fixture(fixtures_dir):
    def _load(*parts: str) -> str:
        return (fixtures_dir.joinpath(*parts)).read_text(encoding="utf-8")

    return _load


@pytest.fixture
def load_json_fixture(fixtures_dir):
    def _load(*parts: str) -> dict:
        text = fixtures_dir.joinpath(*parts).read_text(encoding="utf-8")
        return json.loads(text)

    return _load
