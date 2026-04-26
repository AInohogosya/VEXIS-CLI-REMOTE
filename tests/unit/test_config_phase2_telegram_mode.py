"""Tests for Telegram config without Phase 2 end-update mode."""

from pathlib import Path

from src.ai_agent.utils.config import ConfigManager, TelegramConfig


def test_telegram_config_has_no_phase2_end_update_flag():
    telegram_config = TelegramConfig()
    assert not hasattr(telegram_config, "send_phase2_end_updates")


def test_legacy_phase2_end_update_flag_is_ignored(tmp_path: Path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "telegram:\n"
        "  enabled: true\n"
        "  send_phase2_end_updates: false\n"
    )

    manager = ConfigManager(cfg_file)
    config = manager.load_config()

    assert config.telegram.enabled is True
    assert not hasattr(config.telegram, "send_phase2_end_updates")
