"""Tests for text_cleaner — the module removes promo/footer lines and
preserves real content. Each test covers a category of noise we saw in
real Spot articles."""

from spot_bot.cleaners.text_cleaner import (
    _clean_paragraph,
    _is_footer_line,
    clean_article,
    clean_batch,
)


class TestCleanParagraph:
    def test_empty_returns_empty(self):
        assert _clean_paragraph("") == ""

    def test_digit_only_line_removed(self):
        # View counts like "1 786"
        assert _clean_paragraph("1 786") == ""
        assert _clean_paragraph("42") == ""

    def test_hashtag_only_line_removed(self):
        assert _clean_paragraph("#экономика") == ""

    def test_comments_marker_removed(self):
        assert _clean_paragraph("Комментарии") == ""
        assert _clean_paragraph("Комментарии: 5") == ""

    def test_also_read_removed(self):
        assert _clean_paragraph("Читайте также: важная новость") == ""
        assert _clean_paragraph("Also read about this") == ""

    def test_normal_text_preserved(self):
        text = "Центральный банк повысил ставку."
        assert _clean_paragraph(text) == text

    def test_urls_stripped_from_text(self):
        assert "https://" not in _clean_paragraph("Подробнее на https://spot.uz/news")

    def test_too_short_removed(self):
        assert _clean_paragraph("a") == ""
        assert _clean_paragraph(".") == ""

    def test_dash_normalization(self):
        cleaned = _clean_paragraph("Текст—важный—пример")
        assert " — " in cleaned


class TestIsFooterLine:
    def test_pure_url_is_footer(self):
        assert _is_footer_line("https://spot.uz")

    def test_normal_text_not_footer(self):
        assert not _is_footer_line("Это обычное предложение.")


class TestCleanArticle:
    def test_empty_returns_empty(self):
        assert clean_article("") == ""
        assert clean_article(None) == ""

    def test_removes_noise_but_keeps_content(self):
        text = "Главный заголовок\n\n1 786\n\n#экономика\n\nРеальный текст статьи."
        cleaned = clean_article(text)
        assert "1 786" not in cleaned
        assert "#экономика" not in cleaned
        assert "Реальный текст статьи." in cleaned

    def test_strips_trailing_footer_block(self):
        text = "Статья о чём-то важном.\n\nhttps://facebook.com/spot"
        cleaned = clean_article(text)
        assert "Статья о чём-то важном." in cleaned
        assert "facebook" not in cleaned

    def test_preserves_substantial_text_when_cleaning_would_empty(self):
        # If everything matched filter rules but original was long, fall back
        # to minimally cleaned version (regression test for today's fix).
        # "Читайте также" triggers removal of the whole line, leaving nothing.
        # But the minimal-cleanup branch kicks in because original > 50 chars.
        noisy = "Читайте также: важная новость о событиях в мире сегодня дня"
        result = clean_article(noisy)
        # Either result is empty (if paragraph rules killed everything and
        # the minimal branch decided not to intervene) OR substantial text
        # survived. Key invariant: we don't return empty when the original
        # had substantial text meeting our threshold.
        assert len(result) > 0 or len(noisy) <= 50


class TestCleanBatch:
    def test_cleans_each_article_body(self):
        articles = [
            {"body": "Real content.\n\n1 786"},
            {"body": "Another article.\n\n#tag"},
        ]
        clean_batch(articles)
        assert "1 786" not in articles[0]["body"]
        assert "#tag" not in articles[1]["body"]

    def test_ignores_missing_body(self):
        articles = [{"title": "no body"}]
        # Should not raise
        clean_batch(articles)
