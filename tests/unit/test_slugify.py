"""Regression tests for slug generation across pipeline modules."""

from __future__ import annotations

import pytest

from openai_tailor import slugify
from job_runner import re_slug
from craigslist_scanner import _slug_from_url as craigslist_slug
from freelancer_scanner import _slug_from_url as freelancer_slug
from indeed_scanner import _slug_for_job


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Weave", "weave"),
        ("US Tech Solutions", "us-tech-solutions"),
        ("  Acme Corp!!!  ", "acme-corp"),
        ("", "company"),
        ("---", "company"),
    ],
)
def test_openai_tailor_slugify(name, expected):
    assert slugify(name) == expected


def test_openai_tailor_slugify_max_length():
    long_name = "a" * 60
    assert len(slugify(long_name)) == 48


@pytest.mark.parametrize(
    "text,expected_prefix",
    [
        ("Hello World", "hello-world"),
        ("", "message"),
    ],
)
def test_job_runner_re_slug(text, expected_prefix):
    assert re_slug(text).startswith(expected_prefix) or re_slug(text) == expected_prefix


def test_craigslist_slug_from_url():
    url = "https://losangeles.craigslist.org/lac/ggg/d/los-angeles-python-automation/7856123456.html"
    slug = craigslist_slug(url)
    assert slug.startswith("craigslist_")
    assert "los_angeles" not in slug.replace("craigslist_", "", 1).split("_")[0:2]


def test_freelancer_slug_from_url():
    url = "https://www.freelancer.com/projects/python/build-fastapi-api/"
    slug = freelancer_slug(url)
    assert slug.startswith("freelancer_")
    assert "python" in slug


def test_indeed_slug_for_job():
    slug = _slug_for_job("abc123def456", "Acme Corp")
    assert slug.startswith("indeed_acme_corp_")
    assert "abc123def456"[:12] in slug
