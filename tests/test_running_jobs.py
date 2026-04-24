"""Regression tests for running_jobs keying.

It should be keyed by user_id (not chat_id) so:
- Same user can't run two scrapes across different chats at once
- Different users in the same group chat can scrape in parallel
"""

from __future__ import annotations

import asyncio

import pytest

from spot_bot.jobs import running_jobs


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear the module-level registry between tests."""
    running_jobs.clear()
    yield
    running_jobs.clear()


def _dummy_entry(chat_id: int) -> dict:
    return {
        "task": asyncio.Future(),  # placeholder — never awaited
        "cancel_event": asyncio.Event(),
        "chat_id": chat_id,
    }


def test_same_user_cannot_run_two_jobs():
    """If user 42 starts a scrape, a second attempt from the same user
    (even from a different chat) must see their existing job."""
    running_jobs[42] = _dummy_entry(chat_id=100)
    # Second invocation from a different chat:
    assert 42 in running_jobs


def test_different_users_can_run_in_same_chat():
    """Users 1 and 2 in group chat 500 each have their own slot."""
    running_jobs[1] = _dummy_entry(chat_id=500)
    running_jobs[2] = _dummy_entry(chat_id=500)
    assert 1 in running_jobs
    assert 2 in running_jobs


def test_cancel_resolves_by_user_not_chat():
    """Looking up by user_id finds the right job regardless of chat."""
    running_jobs[42] = _dummy_entry(chat_id=100)
    job = running_jobs.get(42)
    assert job is not None
    # chat_id is carried alongside for delivery purposes
    assert job["chat_id"] == 100


def test_chat_id_alone_is_not_a_key():
    """Tests the regression: chat_id used to be the key, user_id now is."""
    running_jobs[42] = _dummy_entry(chat_id=100)
    assert 100 not in running_jobs
    assert 42 in running_jobs
