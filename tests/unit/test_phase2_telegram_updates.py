"""Unit tests for Phase 2 per-iteration update recording."""

from src.ai_agent.core_processing.five_phase_engine import FivePhaseEngine, PipelineContext


def test_record_phase2_update_records_success_metadata():
    engine = FivePhaseEngine(config={"runtime_mode": "terminal"})
    context = PipelineContext(user_prompt="test prompt")
    context.iteration_count = 2

    engine._record_phase2_update(context, status="success", detail="Phase 2 completed (iteration 2).")

    assert context.metadata["phase2_updates"][-1] == {
        "status": "success",
        "iteration": 2,
        "detail": "Phase 2 completed (iteration 2).",
    }


def test_record_phase2_update_records_failure_metadata():
    engine = FivePhaseEngine(config={"runtime_mode": "telegram"})
    context = PipelineContext(user_prompt="test prompt")
    context.iteration_count = 3

    engine._record_phase2_update(context, status="failed", detail="Phase 2 ended without a code block.")

    assert context.metadata["phase2_updates"][-1] == {
        "status": "failed",
        "iteration": 3,
        "detail": "Phase 2 ended without a code block.",
    }
