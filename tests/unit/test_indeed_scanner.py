"""Regression tests for Indeed scanner helpers."""

from __future__ import annotations

from indeed_scanner import _format_location, _format_salary, _heuristic_score, _strip_html


def test_strip_html():
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_format_location_formatted_short():
    job = {"location": {"formatted": {"short": "Los Angeles, CA"}}}
    assert _format_location(job) == "Los Angeles, CA"


def test_format_location_parts_fallback():
    job = {"location": {"city": "Los Angeles", "admin1Code": "CA", "countryCode": "US"}}
    assert _format_location(job) == "Los Angeles, CA, US"


def test_format_salary_range():
    job = {
        "compensation": {
            "estimated": {
                "currencyCode": "USD",
                "baseSalary": {
                    "unitOfWork": "YEAR",
                    "range": {"min": 150000, "max": 180000},
                },
            }
        }
    }
    salary = _format_salary(job)
    assert "$150,000" in salary
    assert "$180,000" in salary


def test_heuristic_score_python_remote():
    score = _heuristic_score(
        "Senior Python Backend Engineer",
        "Remote role building APIs with Django and AWS",
    )
    assert score >= 70


def test_heuristic_score_skip_keyword():
    score = _heuristic_score("Warehouse associate", "Forklift and warehouse duties")
    assert score == 30
