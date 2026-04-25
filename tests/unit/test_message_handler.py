"""
Unit tests for Telegram message handler behavior.
"""

import asyncio

from src.ai_agent.telegram_integration.message_handler import MessageHandler


class DummyTelegramClient:
    """Minimal Telegram client stub for MessageHandler tests."""

    def __init__(self):
        self.callback = None

    def register_message_handler(self, callback):
        self.callback = callback


class DummySender:
    def __init__(self, username="tester", user_id=42, phone=None):
        self.username = username
        self.id = user_id
        self.phone = phone


class DummyMessage:
    def __init__(self, text, sender):
        self.message = text
        self._sender = sender
        self.date = None

    async def get_sender(self):
        return self._sender


class DummyEvent:
    def __init__(self, text, sender=None):
        self.sender = sender or DummySender()
        self.message = DummyMessage(text, self.sender)
        self.replies = []

    async def reply(self, text):
        self.replies.append(text)


def test_reset_command_replies_confirmation_and_clears_history(monkeypatch):
    telegram_client = DummyTelegramClient()
    handler = MessageHandler(telegram_client)
    handler.authorized_users = []

    cleared = {"value": False}

    class FakeHistory:
        def clear_history(self):
            cleared["value"] = True

    # Patch history getter used by message handler
    monkeypatch.setattr(
        "src.ai_agent.telegram_integration.message_handler.get_terminal_history",
        lambda: FakeHistory()
    )

    event = DummyEvent("/reset")
    asyncio.run(handler._handle_message(event))

    assert cleared["value"] is True
    assert any("Reset complete" in msg for msg in event.replies)


def test_callback_retries_once_and_notifies_on_final_failure(monkeypatch):
    telegram_client = DummyTelegramClient()
    handler = MessageHandler(telegram_client)
    handler.authorized_users = []

    # Avoid waiting in test for retry backoff
    async def no_sleep(_):
        return None

    monkeypatch.setattr("src.ai_agent.telegram_integration.message_handler.asyncio.sleep", no_sleep)

    calls = {"count": 0}
    notifications = {"count": 0}

    async def failing_callback(_message, _sender):
        calls["count"] += 1
        raise RuntimeError("simulated callback failure")

    async def fake_notify_error(**_kwargs):
        notifications["count"] += 1

    monkeypatch.setattr(handler, "_notify_error", fake_notify_error)

    handler.set_prompt_callback_with_sender(failing_callback)
    event = DummyEvent("run task")
    asyncio.run(handler._handle_message(event))

    # Initial call + one auto-retry
    assert calls["count"] == 2
    # Final failure triggers notifier
    assert notifications["count"] == 1
