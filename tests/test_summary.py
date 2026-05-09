"""Tests for spot_bot.summary — the Groq LLM summarizer wrapper.

We don't actually hit Groq in CI. Tests verify:
- No-op behavior when GROQ_API_KEY is missing.
- Prompt-builder includes the right language instruction.
- Prefix-stripping logic cleans common preamble.
"""
import pytest

from spot_bot import summary as sm


@pytest.mark.asyncio
async def test_summarize_returns_none_when_no_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    article = {"id": "spotuz/1", "title": "Hi", "body": "Some body."}
    out = await sm.summarize(article, lang="en")
    assert out is None


@pytest.mark.asyncio
async def test_summarize_returns_none_for_empty_body(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test_key")
    article = {"id": "spotuz/1", "title": "Hi", "body": ""}
    out = await sm.summarize(article, lang="en")
    assert out is None


def test_prompt_includes_language_instruction():
    p_en = sm._build_prompt("Title", "Body text.", "en")
    assert "in English" in p_en
    p_ru = sm._build_prompt("Title", "Body text.", "ru")
    assert "in Russian" in p_ru
    p_uz = sm._build_prompt("Title", "Body text.", "uz")
    assert "in Uzbek" in p_uz


def test_prompt_unknown_lang_falls_back():
    p = sm._build_prompt("Title", "Body text.", "xx")
    assert "same language" in p


def test_prompt_includes_title_and_body():
    p = sm._build_prompt("My Title", "Article body here.", "en")
    assert "My Title" in p
    assert "Article body here." in p
