"""Unit tests for the title-anchor match helpers.

/scrape from "<title>" depends on these helpers normalizing query and
candidate consistently. Tests pin: HTML stripping, punctuation drop,
case-insensitivity, Cyrillic, and substring containment.
"""
from spot_bot.scrapers.telegram_channel import (
    _normalize_for_match,
    _post_match_text,
    _post_first_line,
)


def test_normalize_strips_html():
    assert _normalize_for_match("<b>Hello</b> world") == "hello world"


def test_normalize_unescapes_entities():
    assert "amp" not in _normalize_for_match("Foo &amp; Bar")
    assert _normalize_for_match("Foo &amp; Bar") == "foo bar"


def test_normalize_lowercases():
    assert _normalize_for_match("HELLO WORLD") == "hello world"


def test_normalize_drops_punctuation():
    out = _normalize_for_match("Hello, World! foo.")
    assert "," not in out
    assert "!" not in out
    assert "." not in out


def test_normalize_collapses_whitespace():
    assert _normalize_for_match("foo    bar\n\nbaz") == "foo bar baz"


def test_cyrillic_preserved():
    assert _normalize_for_match("ПРЕЗИДЕНТ ПОДПИСАЛ") == "президент подписал"


def test_substring_match_via_normalize():
    needle = _normalize_for_match("президент подписал")
    haystack = _post_match_text({
        "text_html": "<b>Президент подписал</b> закон о чём-то"
    })
    assert needle in haystack


def test_post_first_line_truncates_long_titles():
    long_text = "<b>" + ("a " * 200) + "</b>"
    out = _post_first_line({"text_html": long_text})
    assert len(out) <= 121  # 120 + "…"


def test_empty_post_returns_empty():
    assert _post_match_text({"text_html": ""}) == ""
    assert _post_first_line({}) == ""
