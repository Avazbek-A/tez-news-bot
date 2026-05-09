"""Heuristic per-article language detector.

We only need to distinguish three cases for routing TTS:
- 'uz' → Uzbek (Cyrillic or Latin)
- 'ru' → Russian
- 'en' → English (default fallback)

A full-blown lang-detect library (langid, fasttext) would be more accurate
but adds 10-50 MB of dependencies. For our use case — articles that are
overwhelmingly in one language — script + character-set heuristics are
plenty.
"""

from __future__ import annotations

# Uzbek-Cyrillic-only characters that don't appear in Russian.
_UZBEK_CYRILLIC_CHARS = set("ўғҳқ")
# Uzbek Latin uses apostrophe-modified letters (oʻ, gʻ, sh, ng).
_UZBEK_LATIN_MARKERS = ("oʻ", "gʻ", "o'", "g'", "ng")


def detect_language(text: str) -> str:
    """Return one of 'uz', 'ru', 'en' for the given text."""
    if not text:
        return "en"
    text_lower = text.lower()

    cyrillic = sum(1 for c in text if "Ѐ" <= c <= "ӿ")
    latin = sum(1 for c in text if c.isascii() and c.isalpha())

    has_uz_cyr = any(c in _UZBEK_CYRILLIC_CHARS for c in text_lower)

    if cyrillic > latin:
        # Cyrillic-dominant. Russian unless Uzbek-specific letters appear.
        return "uz" if has_uz_cyr else "ru"

    # Latin-dominant. Could be English or Uzbek Latin.
    if latin >= 30 and any(m in text_lower for m in _UZBEK_LATIN_MARKERS):
        return "uz"
    return "en"
