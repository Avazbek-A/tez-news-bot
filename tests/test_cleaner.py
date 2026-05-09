"""Unit tests for the article text cleaner.

The cleaner removes noise and (optionally) ad markers. The /ads toggle
gates ad-related filters; pure noise should always be stripped. Tests
pin both behaviors so /ads on doesn't accidentally re-enable view-count
spam, and /ads off doesn't accidentally let through real ad markers.
"""
from spot_bot.cleaners.text_cleaner import clean_article


def test_clean_strips_view_counts_regardless_of_ads_setting():
    text = "1 786\n\nSome real article body here."
    assert "1 786" not in clean_article(text)
    assert "1 786" not in clean_article(text, include_ads=True)


def test_clean_strips_hashtag_lines():
    text = "#economy #news\n\nReal content goes here."
    assert "#economy" not in clean_article(text)


def test_ads_off_strips_promo_markers():
    text = "Реклама\n\nBuy our product\n\nНа правах рекламы"
    out = clean_article(text, include_ads=False)
    assert "Реклама" not in out
    assert "На правах рекламы" not in out


def test_ads_on_keeps_promo_markers():
    text = "Реклама\n\nBuy our product\n\nНа правах рекламы"
    out = clean_article(text, include_ads=True)
    assert "Реклама" in out
    assert "На правах рекламы" in out


def test_ads_off_strips_contact_footers():
    text = "Article body.\n\nСайт: example.uz\nTelegram: @example"
    out = clean_article(text, include_ads=False)
    assert "Сайт:" not in out
    assert "Telegram:" not in out


def test_ads_on_keeps_contact_footers():
    text = "Article body.\n\nСайт: example.uz\nTelegram: @example"
    out = clean_article(text, include_ads=True)
    assert "Сайт:" in out
    assert "Telegram:" in out


def test_urls_stripped_in_both_modes():
    text = "See https://example.com/article for more details."
    assert "https://" not in clean_article(text)
    assert "https://" not in clean_article(text, include_ads=True)


def test_cross_references_stripped_regardless():
    text = "Real content.\n\nРанее Spot писал о подобной ситуации."
    assert "Ранее Spot писал" not in clean_article(text)
    assert "Ранее Spot писал" not in clean_article(text, include_ads=True)


def test_empty_input_returns_empty():
    assert clean_article("") == ""
    assert clean_article(None or "") == ""
