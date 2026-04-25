"""Tests for Telegram Phase 2 end-update config mode."""

from pathlib import Path

from src.ai_agent.utils.config import ConfigManager


def test_send_phase2_end_updates_defaults_to_true(tmp_path: Path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("telegram:\n  enabled: true\n")

    manager = ConfigManager(cfg_file)
    config = manager.load_config()

    assert config.telegram.send_phase2_end_updates is True


def test_send_phase2_end_updates_can_be_disabled(tmp_path: Path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "telegram:\n"
        "  enabled: true\n"
        "  send_phase2_end_updates: false\n"
    )

    manager = ConfigManager(cfg_file)
    config = manager.load_config()

    assert config.telegram.send_phase2_end_updates is False
