"""Unit tests for Phase 2 goal summary behavior."""

from src.ai_agent.core_processing.five_phase_engine import FivePhaseEngine, PipelineContext
from src.ai_agent.external_integration.model_runner import ModelResponse, TaskType


def _success_response(content: str) -> ModelResponse:
    return ModelResponse(
        success=True,
        content=content,
        task_type=TaskType.PHASE2_COMMAND_EXTRACTION,
        model="test-model",
        provider="test-provider",
    )


def test_phase2_generates_goal_summary_and_prints_in_terminal_mode(monkeypatch, capsys):
    engine = FivePhaseEngine(config={"runtime_mode": "terminal"})
    context = PipelineContext(user_prompt="do something", phase1_output="long original plan")

    monkeypatch.setattr(engine, "_summarize_phase2_goal", lambda _text: "Set up the project and run validation.")
    monkeypatch.setattr(
        engine.model_runner,
        "run_model",
        lambda _request: _success_response("```bash\necho done\n```")
    )

    assert engine._run_phase2(context) is True
    assert context.phase2_goal_summary == "Set up the project and run validation."
    assert context.metadata.get("phase2_goal_summary") == "Set up the project and run validation."

    out = capsys.readouterr().out
    assert "Phase 2 goal summary" in out


def test_phase2_generates_goal_summary_without_terminal_print_in_telegram_mode(monkeypatch, capsys):
    engine = FivePhaseEngine(config={"runtime_mode": "telegram"})
    context = PipelineContext(user_prompt="do something", phase1_output="long original plan")

    monkeypatch.setattr(engine, "_summarize_phase2_goal", lambda _text: "Deploy the app successfully.")
    monkeypatch.setattr(
        engine.model_runner,
        "run_model",
        lambda _request: _success_response("```bash\necho done\n```")
    )

    assert engine._run_phase2(context) is True
    assert context.metadata.get("phase2_goal_summary") == "Deploy the app successfully."

    out = capsys.readouterr().out
    assert "Phase 2 goal summary" not in out
