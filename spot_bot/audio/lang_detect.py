"""Heuristic per-article language detector.

We need to distinguish five cases for routing TTS:
- 'uz' → Uzbek (Cyrillic or Latin)
- 'ru' → Russian (Cyrillic)
- 'de' → German (Latin + ä, ö, ü, ß)
- 'tr' → Turkish (Latin + ç, ğ, ı, İ, ş)
- 'en' → English (default fallback)

A full-blown lang-detect library (langid, fasttext) would be more accurate
but adds 10-50 MB of dependencies. For our use case — articles that are
overwhelmingly in one language — script + character-set heuristics are
plenty.
"""

from __future__ import annotations

# Uzbek-Cyrillic-only characters that don't appear in Russian.
_UZBEK_CYRILLIC_CHARS = set("ўғҳқ")
# Uzbek Latin uses apostrophe-modified letters (oʻ, gʻ).
_UZBEK_LATIN_MARKERS = ("oʻ", "gʻ", "o'", "g'")
# German-only letter ß (eszett); ä is also unique to German among our set.
_GERMAN_ONLY = set("ßäÄ")
# German has umlauts ö ü; shared with Turkish but bundled with ß/ä when present.
_GERMAN_UMLAUTS = set("öüÖÜ")
# Turkish has ı (dotless i), İ, ç, ğ, ş — none of these appear in German.
_TURKISH_SPECIFIC = set("ıİçğşÇĞŞ")


def detect_language(text: str) -> str:
    """Return one of 'uz', 'ru', 'de', 'tr', 'en' for the given text."""
    if not text:
        return "en"
    text_lower = text.lower()

    cyrillic = sum(1 for c in text if "Ѐ" <= c <= "ӿ")
    latin = sum(1 for c in text if c.isascii() and c.isalpha())

    has_uz_cyr = any(c in _UZBEK_CYRILLIC_CHARS for c in text_lower)

    if cyrillic > latin:
        # Cyrillic-dominant. Russian unless Uzbek-specific letters appear.
        return "uz" if has_uz_cyr else "ru"

    # Latin-dominant. Disambiguate by characteristic non-ASCII letters.
    if any(c in _TURKISH_SPECIFIC for c in text):
        return "tr"
    if any(c in _GERMAN_ONLY for c in text):
        return "de"
    # ö / ü alone are ambiguous (German + Turkish + a few others) but if
    # we've ruled out Turkish-specific chars, German wins.
    if any(c in _GERMAN_UMLAUTS for c in text):
        return "de"
    if latin >= 30 and any(m in text_lower for m in _UZBEK_LATIN_MARKERS):
        return "uz"
    return "en"
