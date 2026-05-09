"""Tests for the heuristic language detector used by Phase 11 TTS routing."""
from spot_bot.audio.lang_detect import detect_language


def test_pure_english_is_en():
    assert detect_language("Hello world this is a news article") == "en"


def test_empty_returns_en():
    assert detect_language("") == "en"
    assert detect_language(None or "") == "en"


def test_pure_russian_is_ru():
    text = "Президент подписал новый закон о налоговом кодексе."
    assert detect_language(text) == "ru"


def test_uzbek_cyrillic_with_specific_chars_is_uz():
    # ў and ҳ are Uzbek-specific Cyrillic letters
    text = "Тошкентда янги метро ўтиш йўлаги ҳақида хабарлар"
    assert detect_language(text) == "uz"


def test_uzbek_latin_with_apostrophes_is_uz():
    text = "Toshkentda yangi oʻzgartirishlar joriy qilindi va gʻalaba qozonildi"
    assert detect_language(text) == "uz"


def test_russian_without_uz_chars_is_ru():
    # Plain Russian should NOT be misclassified as Uzbek even though
    # it's Cyrillic.
    text = "Сегодня в Москве открылась новая выставка современного искусства."
    assert detect_language(text) == "ru"


def test_short_latin_without_uz_markers_is_en():
    text = "Tashkent metro"  # no apostrophes, short
    assert detect_language(text) == "en"


def test_mostly_cyrillic_some_latin_classified_by_cyrillic():
    text = "В апреле компания Apple представила новые функции iOS"
    # Cyrillic dominates; should be Russian
    assert detect_language(text) == "ru"
