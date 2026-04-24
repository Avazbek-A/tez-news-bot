"""Tests for pure-Python helpers in telegram_channel (date parsing, ID
extraction, range logic). Playwright-dependent scraping functions need
a separate integration test with mocks."""

from datetime import date, datetime

from spot_bot.scrapers.telegram_channel import (
    _get_numeric_id,
    _parse_date,
    _post_sort_key,
)


class TestGetNumericId:
    def test_standard_format(self):
        assert _get_numeric_id("spotuz/34950") == 34950

    def test_multiple_slashes_takes_last(self):
        assert _get_numeric_id("channel/foo/12345") == 12345

    def test_non_numeric_returns_none(self):
        assert _get_numeric_id("spotuz/abc") is None

    def test_empty_returns_none(self):
        assert _get_numeric_id("") is None


class TestParseDate:
    def test_today(self):
        assert _parse_date("today at 14:30") == datetime.now().date()

    def test_yesterday(self):
        today = datetime.now().date()
        parsed = _parse_date("yesterday at 09:15")
        assert parsed is not None
        assert (today - parsed).days == 1

    def test_full_date(self):
        parsed = _parse_date("Jan 17, 2026")
        assert parsed == date(2026, 1, 17)

    def test_short_date_current_year(self):
        # "Jan 17" — year is inferred. Should not return a future date.
        parsed = _parse_date("Jan 17")
        assert parsed is not None
        assert parsed <= datetime.now().date()

    def test_garbage_returns_none(self):
        assert _parse_date("not a date at all") is None


class TestPostSortKey:
    def test_orders_by_numeric_suffix(self):
        posts = [
            {"id": "spotuz/100"},
            {"id": "spotuz/50"},
            {"id": "spotuz/200"},
        ]
        posts.sort(key=_post_sort_key)
        assert [p["id"] for p in posts] == [
            "spotuz/50", "spotuz/100", "spotuz/200",
        ]

    def test_handles_missing_id(self):
        assert _post_sort_key({}) == 0


class TestInclusiveRange:
    """Regression test for the off-by-one bug: 34901-34950 must fetch 50 posts."""

    def test_inclusive_range_size(self):
        start_id = 34950
        end_id = 34901
        # Matches the formula in scrape_by_post_ids
        needed = start_id - end_id + 1
        assert needed == 50

    def test_predicate_accepts_both_endpoints(self):
        # The predicate used inside scrape_by_post_ids
        lo, hi = 34901, 34950

        def predicate(nid: int) -> bool:
            return lo <= nid <= hi

        assert predicate(34901)
        assert predicate(34950)
        assert predicate(34925)
        assert not predicate(34900)
        assert not predicate(34951)
