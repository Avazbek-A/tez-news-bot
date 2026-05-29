"""End-to-end cleaner test against a realistic spot.uz article fixture.

Unlike the unit tests in test_image_extraction.py (which feed tiny inline
HTML snippets), this exercises clean_html on a full-page document with the
real structures spot.uz uses — site header/footer, articleContent, a
lightbox cover, lazy-loaded body images at multiple size variants, a
tracking pixel, and read-also/social-share noise. It's the regression
guard for "our parser stopped handling real markup."
"""
from pathlib import Path

import pytest

from spot_bot.cleaners.html_cleaner import clean_html

FIXTURE = Path(__file__).parent / "fixtures" / "spot_article.html"


@pytest.fixture
def article_html():
    return FIXTURE.read_text(encoding="utf-8")


def test_headline_extracted(article_html):
    headline, body, images = clean_html(
        article_html, base_url="https://www.spot.uz/ru/2026/05/08/hong-kong/"
    )
    assert headline
    assert "Гонконг" in headline


def test_body_extracted_and_substantial(article_html):
    _, body, _ = clean_html(article_html, base_url="https://www.spot.uz/x")
    assert body
    assert len(body) > 200
    # Real paragraph content survived…
    assert "авиасообщение" in body
    # …and the boilerplate noise was stripped.
    assert "Читайте также" not in body
    assert "share buttons" not in body
    assert "footer that should be stripped" not in body


def test_images_extracted_absolute_and_deduped(article_html):
    _, _, images = clean_html(article_html, base_url="https://www.spot.uz/x")
    urls = [img["url"] for img in images]

    # Cover + body1 + body2 = 3 unique (body1's _s variant collapses into _b).
    assert len(images) == 3, urls

    # All absolute https URLs.
    assert all(u.startswith("https://") for u in urls)

    # Cover prefers the full-size lightbox _l, not the inner _b thumbnail.
    assert any(u.endswith("cover_l.webp") for u in urls), urls

    # The smaller _s body variant was dropped in favor of _b.
    assert not any(u.endswith("body1_s.webp") for u in urls), urls
    assert any(u.endswith("body1_b.webp") for u in urls), urls

    # Tracking pixel is gone.
    assert not any("pixel" in u for u in urls), urls


def test_cover_image_first(article_html):
    """Cover image should lead the list (it's the article's lead photo)."""
    _, _, images = clean_html(article_html, base_url="https://www.spot.uz/x")
    assert images
    assert images[0]["url"].endswith("cover_l.webp")
