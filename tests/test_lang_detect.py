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


def test_german_with_eszett_is_de():
    assert detect_language("Die Straße ist sehr groß und schön") == "de"


def test_german_with_umlauts_is_de():
    assert detect_language("Bundeskanzler trifft sich für ein Gespräch") == "de"


def test_turkish_with_dotless_i_is_tr():
    assert detect_language("Türkiye ekonomisi bu yıl büyüdü") == "tr"


def test_turkish_with_cedilla_is_tr():
    assert detect_language("Cumhurbaşkanı çok önemli bir konuşma yaptı") == "tr"


def test_turkish_not_misclassified_as_german():
    # Turkish has ö ü but ALSO ı ç ğ ş — those tip the balance
    assert detect_language("Türk ekonomisi çok güçlü bir şekilde büyüdü") == "tr"


def test_german_not_misclassified_as_turkish():
    # German has ö ü but no Turkish-specific letters
    assert detect_language("Über die Möglichkeiten der größeren Wirtschaft") == "de"


def test_pure_english_still_en_after_adding_de_tr():
    assert detect_language("The company announced new features yesterday") == "en"
