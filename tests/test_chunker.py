"""Unit tests for the TTS text chunker.

Why these tests matter: long interview-format articles used to silently
disappear from combined audio because Edge TTS hit the 60s timeout. The
chunker fixes that by splitting bodies before TTS. If the splitter
regresses (oversized chunks, dropped content, infinite loops on edge
cases), long articles will start vanishing again.
"""
from spot_bot.audio.tts_generator import (
    _split_text_into_chunks,
    TTS_CHUNK_CHAR_LIMIT,
)


def test_short_text_returns_single_chunk():
    text = "Hello world. Short and sweet."
    chunks = _split_text_into_chunks(text)
    assert chunks == [text]


def test_empty_text_returns_empty_list():
    assert _split_text_into_chunks("") == []


def test_whitespace_only_returns_empty_list():
    assert _split_text_into_chunks("   \n\n  \t  ") == []


def test_long_single_paragraph_splits_under_limit():
    para = ("Lorem ipsum dolor sit amet. " * 200).strip()  # ~5600 chars
    chunks = _split_text_into_chunks(para)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= TTS_CHUNK_CHAR_LIMIT, f"chunk size {len(c)} exceeds limit"


def test_multi_paragraph_packs_greedily():
    paragraphs = [f"Paragraph {i} content. " * 50 for i in range(10)]
    text = "\n\n".join(paragraphs)
    chunks = _split_text_into_chunks(text)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= TTS_CHUNK_CHAR_LIMIT


def test_oversize_sentence_falls_back_to_word_split():
    # A single sentence longer than the limit (no sentence-ending punct)
    text = "word " * 1000  # ~5000 chars, no periods
    chunks = _split_text_into_chunks(text)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= TTS_CHUNK_CHAR_LIMIT


def test_no_content_lost_after_split():
    # Word count after rejoining should match original
    text = "Word " * 800 + ". " + "More word " * 800 + "."
    chunks = _split_text_into_chunks(text)
    rejoined_words = " ".join(chunks).split()
    original_words = text.split()
    # Allow for whitespace normalization but not actual word loss
    assert len(rejoined_words) == len(original_words)


def test_cyrillic_text_handled():
    text = ("Президент подписал закон о новом налоговом кодексе. " * 200).strip()
    chunks = _split_text_into_chunks(text)
    for c in chunks:
        assert len(c) <= TTS_CHUNK_CHAR_LIMIT
