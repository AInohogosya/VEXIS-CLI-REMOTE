"""Unit tests for real-time Phase 2 Telegram updates."""

from types import SimpleNamespace

from src.ai_agent.core_processing.five_phase_engine import FivePhaseEngine, PipelineContext


def test_record_phase2_update_sends_telegram_update_in_terminal_mode(monkeypatch):
    engine = FivePhaseEngine(config={"runtime_mode": "terminal"})
    context = PipelineContext(user_prompt="test prompt")
    context.iteration_count = 2

    monkeypatch.setattr(
        "src.ai_agent.utils.config.load_config",
        lambda: SimpleNamespace(telegram=SimpleNamespace(send_phase2_end_updates=True)),
    )

    sent_payloads = []
    monkeypatch.setattr(engine, "_init_telegram", lambda: setattr(engine, "_telegram_enabled", True))
    monkeypatch.setattr(engine, "_send_via_telegram", lambda message, update_type="update": sent_payloads.append((message, update_type)))

    engine._record_phase2_update(context, status="success", detail="Phase 2 completed (iteration 2).")

    assert context.metadata["phase2_updates"][-1]["status"] == "success"
    assert sent_payloads
    message, update_type = sent_payloads[-1]
    assert "Phase 2 update (iteration 2)" in message
    assert "Status: success" in message
    assert update_type == "phase2_end_update"


def test_record_phase2_update_skips_send_when_disabled(monkeypatch):
    engine = FivePhaseEngine(config={"runtime_mode": "terminal"})
    context = PipelineContext(user_prompt="test prompt")
    context.iteration_count = 1

    monkeypatch.setattr(
        "src.ai_agent.utils.config.load_config",
        lambda: SimpleNamespace(telegram=SimpleNamespace(send_phase2_end_updates=False)),
    )

    called = {"send": False}
    monkeypatch.setattr(engine, "_send_via_telegram", lambda *args, **kwargs: called.__setitem__("send", True))

    engine._record_phase2_update(context, status="failed", detail="Phase 2 failed.")

    assert context.metadata["phase2_updates"][-1]["status"] == "failed"
    assert called["send"] is False
