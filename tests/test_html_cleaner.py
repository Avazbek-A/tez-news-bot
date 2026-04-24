"""Tests for html_cleaner — selector fallback, auth-wall detection,
image extraction."""

from bs4 import BeautifulSoup

from spot_bot.cleaners.html_cleaner import (
    clean_html,
    clean_telegram_text,
    extract_images,
)


def test_returns_empty_when_no_body_container():
    html = "<html><body><p>Just stray text</p></body></html>"
    headline, body, images = clean_html(html)
    assert body is None
    assert images == []


def test_extracts_body_from_articleContent():
    html = """
    <html><body>
      <h1>The Headline</h1>
      <div class="articleContent">
        <p>First paragraph of real content.</p>
        <p>Second paragraph.</p>
      </div>
    </body></html>
    """
    headline, body, _ = clean_html(html)
    assert headline == "The Headline"
    assert "First paragraph" in body
    assert "Second paragraph" in body


def test_selector_fallback_to_contentBox():
    html = """
    <html><body>
      <div class="contentBox">
        <p>Content via fallback selector.</p>
      </div>
    </body></html>
    """
    _, body, _ = clean_html(html)
    assert body is not None
    assert "fallback selector" in body


def test_auth_wall_returns_none_body():
    html = """
    <html><body>
      <div class="articleContent">
        <p>Вы не авторизованы. Войдите на сайт</p>
      </div>
    </body></html>
    """
    _, body, _ = clean_html(html)
    assert body is None


def test_strips_scripts_and_footers():
    html = """
    <html><body>
      <div class="articleContent">
        <script>alert('ad')</script>
        <p>Real content.</p>
        <footer>Footer crap</footer>
      </div>
    </body></html>
    """
    _, body, _ = clean_html(html)
    assert "alert" not in body
    assert "Footer crap" not in body
    assert "Real content" in body


def test_removes_duplicate_headline_in_body():
    html = """
    <html><body>
      <h1>Economy News</h1>
      <div class="articleContent">
        <p>Economy News</p>
        <p>The actual article body.</p>
      </div>
    </body></html>
    """
    _, body, _ = clean_html(html)
    # Headline-duplicate paragraph removed; body paragraph stays
    assert body.count("Economy News") == 0
    assert "actual article body" in body


class TestExtractImages:
    def _parse(self, html: str):
        return BeautifulSoup(html, "lxml")

    def test_resolves_relative_urls(self):
        soup = self._parse('<div><img src="/img/photo.jpg" width="400" /></div>')
        images = extract_images(soup, base_url="https://spot.uz/article")
        assert len(images) == 1
        assert images[0]["url"] == "https://spot.uz/img/photo.jpg"

    def test_skips_tracking_pixels(self):
        soup = self._parse('<div><img src="https://x/pixel.gif" /></div>')
        assert extract_images(soup) == []

    def test_skips_tiny_images(self):
        soup = self._parse(
            '<div><img src="https://x/icon.png" width="20" height="20" /></div>'
        )
        assert extract_images(soup) == []

    def test_deduplicates_same_url(self):
        soup = self._parse(
            '<div>'
            '<img src="https://x/a.jpg" width="400" />'
            '<img src="https://x/a.jpg" width="400" />'
            '</div>'
        )
        assert len(extract_images(soup)) == 1


def test_clean_telegram_text_strips_html():
    result = clean_telegram_text("<b>Hello</b> <i>world</i>")
    assert "Hello" in result and "world" in result
    assert "<" not in result and ">" not in result


def test_clean_telegram_text_empty():
    assert clean_telegram_text("") == ""
    assert clean_telegram_text(None) == ""
