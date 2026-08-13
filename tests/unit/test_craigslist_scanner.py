"""Regression tests for Craigslist scanner parsing and scoring."""

from __future__ import annotations

from craigslist_scanner import (
    DEFAULT_SEARCH_REGIONS,
    _location_from_title,
    _parse_price,
    _parse_search_listings,
    _role_from_title,
    _score_listing,
    _slug_from_url,
    search_regions,
)


SAMPLE_SEARCH_HTML = """
<a href="https://losangeles.craigslist.org/lac/ggg/view/d/los-angeles-python-web-dev/7856123456.html">
  Python web developer for CRM automation $50/hr (Los Angeles)
</a>
<a href="https://losangeles.craigslist.org/lac/ggg/view/d/los-angeles-spam/1111111111.html">
  earn $5000/week easy money
</a>
"""


def test_parse_search_listings():
    listings = _parse_search_listings(SAMPLE_SEARCH_HTML)
    assert len(listings) >= 1
    assert listings[0]["url"].endswith(".html")
    assert "Python" in listings[0]["title"]


def test_score_listing_python_favors_cary():
    score, profile = _score_listing(
        "Python web developer CRM automation",
        "Need python automation for Squarespace and Mailchimp integration",
    )
    assert score >= 60
    assert profile == "cary"


def test_score_listing_spam_zero():
    score, profile = _score_listing(
        "earn $5000/week easy money",
        "Make money fast",
    )
    assert score == 0
    assert profile == "cary"


def test_parse_price_hourly_requires_hour_keyword():
    assert _parse_price("$50 per hour and $75 per hour available") == "$50/hr (from listing)"


def test_parse_price_multiple_amounts_without_hour():
    assert _parse_price("$50/hr and $75/hr available") == "$75"


def test_parse_price_single():
    assert _parse_price("Budget $500") == "$500"


def test_location_from_title_after_dollar_sign():
    title = "Python dev (West LA) $50"
    assert _location_from_title(title) == "50"


def test_location_from_title_defaults_to_socal():
    assert _location_from_title("Python automation gig") == "Southern California (in-person likely)"


def test_location_from_title_san_diego():
    assert _location_from_title("Python dev (San Diego)") == "San Diego area"


def test_location_from_title_sf_bay():
    assert _location_from_title("Automation help (Oakland)") == "SF Bay Area"


def test_search_regions_default_includes_la_sf_sd():
    regions = search_regions()
    labels = [label for label, _url in regions]
    assert labels == [label for label, _url in DEFAULT_SEARCH_REGIONS]
    assert "SF Bay Area gigs" in labels
    assert "San Diego gigs" in labels


def test_role_from_title():
    assert _role_from_title("Python dev $50/hr (West LA)") == "Python dev"
