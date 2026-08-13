"""Regression tests for OpenAI JSON parsing helper."""

from __future__ import annotations

import pytest

from openai_tailor import _parse_json


def test_parse_json_plain():
    assert _parse_json('{"match_score": 85}') == {"match_score": 85}


def test_parse_json_fenced():
    content = '```json\n{"company": "Weave"}\n```'
    assert _parse_json(content) == {"company": "Weave"}


def test_parse_json_invalid_raises():
    with pytest.raises(Exception):
        _parse_json("not json")
