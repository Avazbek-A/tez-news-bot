"""Guards that every command is documented and the menu stays consistent.

The bot exposes ~40 commands; this test fails if a new one is registered
but never explained in /help or the `/` menu (the exact gap the user hit).
"""
from __future__ import annotations

import os

os.environ.setdefault("BOT_TOKEN", "test:dummy")

from telegram.ext import CommandHandler

import spot_bot.help as help_module
from spot_bot.bot import create_app
from spot_bot.translations import _STRINGS, t

_LANGS = ("en", "ru", "uz", "de", "tr")

# Help-navigation commands are the help system itself, not features to
# document inside it.
_HELP_NAV = {
    "help", "about",
    "help_scrape", "help_auto", "help_audio", "help_filter",
    "help_library", "help_languages", "help_system",
}


def _registered_commands():
    app = create_app()
    cmds = set()
    for group in app.handlers.values():
        for h in group:
            if isinstance(h, CommandHandler):
                cmds.update(h.commands)
    return cmds


def _combined_help_text():
    cats = help_module._HELP_CATEGORIES
    parts = [t(f"help_{c}", "en") for c in cats]
    parts.append(t("help_index", "en"))
    parts.append(t("about_body", "en"))
    return " ".join(parts)


def test_every_command_is_documented():
    """Each registered command appears in /help text or the `/` menu."""
    registered = _registered_commands()
    doc = _combined_help_text()
    menu_cmds = {cmd for cmd, _ in help_module._COMMAND_LIST_KEYS}

    undocumented = []
    for cmd in sorted(registered):
        if cmd in _HELP_NAV:
            continue
        if f"/{cmd}" in doc or cmd in menu_cmds:
            continue
        undocumented.append(cmd)

    assert not undocumented, (
        f"These commands are registered but not documented in /help or the "
        f"menu: {undocumented}"
    )


def test_menu_commands_are_registered():
    """Every `/` menu entry maps to a real handler (no dead menu items)."""
    registered = _registered_commands()
    for cmd, _key in help_module._COMMAND_LIST_KEYS:
        assert cmd in registered, f"/{cmd} is in the menu but not registered"


def test_menu_translation_keys_exist_in_all_langs():
    for _cmd, key in help_module._COMMAND_LIST_KEYS:
        assert key in _STRINGS, f"missing translation key {key}"
        for lang in _LANGS:
            assert lang in _STRINGS[key], f"{key} missing {lang}"


def test_every_help_category_has_a_body_and_button():
    for cat in help_module._HELP_CATEGORIES:
        body = t(f"help_{cat}", "en")
        assert body and len(body) > 20, f"help_{cat} body missing/short"
        btn = f"help_btn_{cat}"
        assert btn in _STRINGS, f"missing {btn}"
        for lang in _LANGS:
            assert lang in _STRINGS[btn], f"{btn} missing {lang}"


def test_new_commands_specifically_documented():
    """Belt-and-suspenders for the commands added this cycle."""
    doc = _combined_help_text()
    for cmd in ("/skipseen", "/mute", "/unmute", "/metrics", "/chatid",
                "/cancel", "/status", "/channel"):
        assert cmd in doc, f"{cmd} not documented in /help"
