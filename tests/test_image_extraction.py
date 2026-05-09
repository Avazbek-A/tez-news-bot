"""Tests for the image extraction in scrapers + cleaners.

Two related improvements verified here:
- Telegram channel posts have 3-5 photos in inline background-image
  styles. The scraper extracts those into post["tg_photos"].
- Spot.uz wraps each body image in <a class="lightbox-img" href="..._l.webp">.
  The cleaner now uses the lightbox href (full-size) instead of the
  inner <img src> (thumbnail).
"""
from bs4 import BeautifulSoup
from selectolax.parser import HTMLParser

from spot_bot.cleaners.html_cleaner import (
    extract_images,
    _largest_from_srcset,
)
from spot_bot.scrapers.telegram_channel import _extract_post_photos


# ---------- Spot.uz lightbox ----------

def test_lightbox_href_preferred_over_thumbnail_img_src():
    html = """
    <div class="articleContent">
      <a class="lightbox-img" href="https://example.com/full_l.webp">
        <img src="https://example.com/thumb_b.webp" alt="cover">
      </a>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.find("div", class_="articleContent")
    images = extract_images(body, base_url="https://example.com/article")
    assert len(images) == 1
    # Full-size variant from the parent <a href>
    assert images[0]["url"] == "https://example.com/full_l.webp"
    assert images[0]["alt"] == "cover"


def test_lightbox_relative_href_resolved_against_base_url():
    html = """
    <div class="articleContent">
      <a class="lightbox-img" href="/media/img/full_l.webp">
        <img src="/media/img/thumb_b.webp">
      </a>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.find("div", class_="articleContent")
    images = extract_images(body, base_url="https://www.spot.uz/article/")
    assert len(images) == 1
    assert images[0]["url"] == "https://www.spot.uz/media/img/full_l.webp"


def test_no_double_count_lightbox_plus_inner_img():
    """The same image should NOT appear twice (once from <a href> and
    once from the inner <img src>)."""
    html = """
    <div class="articleContent">
      <a class="lightbox-img" href="https://example.com/A_l.webp">
        <img src="https://example.com/A_b.webp">
      </a>
      <a class="lightbox-img" href="https://example.com/B_l.webp">
        <img src="https://example.com/B_b.webp">
      </a>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.find("div", class_="articleContent")
    images = extract_images(body, base_url="")
    assert len(images) == 2
    urls = [img["url"] for img in images]
    # Only the _l versions, no _b duplicates
    assert all("_l" in u for u in urls)


def test_plain_img_without_lightbox_still_extracted():
    html = """
    <div class="articleContent">
      <img src="https://example.com/plain.jpg" alt="plain">
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.find("div", class_="articleContent")
    images = extract_images(body, base_url="")
    assert len(images) == 1
    assert images[0]["url"] == "https://example.com/plain.jpg"


def test_srcset_picks_largest():
    assert _largest_from_srcset(
        "https://x/small.jpg 320w, https://x/big.jpg 1200w, https://x/mid.jpg 640w"
    ) == "https://x/big.jpg"


def test_srcset_pixel_density_descriptor():
    assert _largest_from_srcset(
        "https://x/1x.jpg 1x, https://x/2x.jpg 2x"
    ) == "https://x/2x.jpg"


def test_srcset_empty_returns_empty():
    assert _largest_from_srcset("") == ""


def test_data_src_lazy_load_attribute():
    """When src is missing, prefer data-src."""
    html = """
    <div class="articleContent">
      <img src="" data-src="https://example.com/lazy.jpg">
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.find("div", class_="articleContent")
    images = extract_images(body, base_url="")
    assert len(images) == 1
    assert images[0]["url"] == "https://example.com/lazy.jpg"


def test_tracking_pixel_dropped():
    html = """
    <div class="articleContent">
      <img src="https://tracker.example.com/pixel.gif">
      <img src="https://example.com/real.jpg">
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.find("div", class_="articleContent")
    images = extract_images(body, base_url="")
    assert len(images) == 1
    assert "real" in images[0]["url"]


# ---------- Telegram channel post photos ----------

def test_extract_telegram_post_photos_from_background_image():
    html = """
    <div class="tgme_widget_message">
      <a class="tgme_widget_message_photo_wrap"
         style="width:680px;height:340px;background-image:url('https://cdn.tg/p1.jpg')"></a>
      <a class="tgme_widget_message_photo_wrap"
         style="width:680px;height:340px;background-image:url('https://cdn.tg/p2.jpg')"></a>
    </div>
    """
    tree = HTMLParser(html)
    msg = tree.css_first(".tgme_widget_message")
    photos = _extract_post_photos(msg)
    assert [p["url"] for p in photos] == [
        "https://cdn.tg/p1.jpg",
        "https://cdn.tg/p2.jpg",
    ]


def test_telegram_photos_dedupe():
    html = """
    <div class="tgme_widget_message">
      <a class="tgme_widget_message_photo_wrap"
         style="background-image:url('https://cdn.tg/x.jpg')"></a>
      <a class="tgme_widget_message_photo"
         style="background-image:url('https://cdn.tg/x.jpg')"></a>
    </div>
    """
    tree = HTMLParser(html)
    msg = tree.css_first(".tgme_widget_message")
    photos = _extract_post_photos(msg)
    assert len(photos) == 1


def test_telegram_no_photos_returns_empty_list():
    html = '<div class="tgme_widget_message"></div>'
    tree = HTMLParser(html)
    msg = tree.css_first(".tgme_widget_message")
    assert _extract_post_photos(msg) == []


def test_telegram_handles_double_quotes_in_style():
    html = """
    <div class="tgme_widget_message">
      <a class="tgme_widget_message_photo_wrap"
         style='background-image:url("https://cdn.tg/q.jpg")'></a>
    </div>
    """
    tree = HTMLParser(html)
    msg = tree.css_first(".tgme_widget_message")
    photos = _extract_post_photos(msg)
    assert len(photos) == 1
    assert photos[0]["url"] == "https://cdn.tg/q.jpg"
