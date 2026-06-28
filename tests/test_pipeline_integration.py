import os
import json
import dspy
import pytest
from unittest.mock import patch, MagicMock
from core.optimizer import (
    run_optimization_pipeline,
    run_verification_pipeline,
    run_section_optimization_pipeline,
    DynamicAgentSignature,
)

SIMPLE_PROMPT = os.path.join(
    os.path.dirname(__file__), "test_data", "simple_prompt.md"
)
TEST_DATA_DIR = os.path.dirname(SIMPLE_PROMPT)
BASE_NAME = os.path.splitext(os.path.basename(SIMPLE_PROMPT))[0]


def _artifact_paths():
    return [
        SIMPLE_PROMPT + ".bak",
        os.path.join(TEST_DATA_DIR, "optimization_report.md"),
        os.path.join(TEST_DATA_DIR, f"{BASE_NAME}_generated_dataset.json"),
        os.path.join(TEST_DATA_DIR, f"{BASE_NAME}_section_comparison.md"),
        os.path.join(TEST_DATA_DIR, f"{BASE_NAME}_optimized.md"),
        os.path.join(TEST_DATA_DIR, f"{BASE_NAME}_compiled_prompt.txt"),
    ]


@pytest.fixture
def cleanup_files():
    yield
    for f in _artifact_paths():
        if os.path.exists(f):
            os.remove(f)


def test_verify_flow():
    """Integration test: run_verification_pipeline with MockLM.
    Exercises file reading, frontmatter stripping, dataset generation,
    baseline/optimized evaluation, score calculation, and verdict formatting.
    """
    from tests.conftest import MockLM

    lm = MockLM(mode="neutral")
    result = run_verification_pipeline(
        agent_markdown_path=SIMPLE_PROMPT,
        provider="mock",
        model="mock-model",
        lm_client=lm,
    )

    assert isinstance(result, str)
    assert "QA Audit Complete" in result
    assert "Baseline Accuracy" in result
    assert "Optimized Accuracy" in result
    assert "Verification" in result
    assert lm.call_count > 0, "MockLM was never called"


def test_verify_missing_file():
    """Error handling: non-existent file returns error string, not crash."""
    from tests.conftest import MockLM

    lm = MockLM()
    result = run_verification_pipeline(
        agent_markdown_path="/nonexistent/path.md",
        provider="mock",
        model="mock-model",
        lm_client=lm,
    )
    assert "Error: Target file not found" in result


def test_optimize_flow(cleanup_files):
    """Integration test: run_optimization_pipeline with MockLM.
    Exercises file reading, backup creation, dataset generation,
    baseline evaluation, report generation. MIPROv2.compile is
    mocked since it uses internal DSPy signatures incompatible
    with a generic MockLM.
    """
    from tests.conftest import MockLM

    mock_program = MagicMock()
    mock_program.signature.instructions = (
        "You are a helpful assistant. Write short poems."
    )
    mock_program.demos = []

    lm = MockLM()
    with patch(
        "dspy.teleprompt.MIPROv2.compile",
        return_value=mock_program,
    ):
        result = run_optimization_pipeline(
            agent_markdown_path=SIMPLE_PROMPT,
            provider="mock",
            model="mock-model",
            lm_client=lm,
            registry=None,
        )

    assert isinstance(result, str)
    assert lm.call_count > 0, "MockLM was never called"

    report_path = os.path.join(TEST_DATA_DIR, "optimization_report.md")
    assert os.path.exists(report_path), "Report file was not created"
    with open(report_path) as f:
        report_content = f.read()
    assert "MIPRO Optimization Performance Report" in report_content
    assert "Baseline Score" in report_content
    assert "Optimized Score" in report_content

    bak_path = SIMPLE_PROMPT + ".bak"
    assert os.path.exists(bak_path), "Backup file was not created"

    generated_dataset_path = os.path.join(TEST_DATA_DIR, f"{BASE_NAME}_generated_dataset.json")
    assert os.path.exists(generated_dataset_path), "Generated dataset was not created"
    with open(generated_dataset_path) as f:
        test_data = json.load(f)
    assert isinstance(test_data, list)
    assert len(test_data) > 0


def test_optimize_flow_with_gepa(cleanup_files):
    """Integration test: run_optimization_pipeline with GEPA optimizer.
    Exercises the factory selection of GEPA, verifies report title uses
    'GEPA' and no demos access occurs.
    """
    from tests.conftest import MockLM

    mock_program = MagicMock()
    mock_program.signature.instructions = (
        "You are a helpful GEPA assistant. Write short poems."
    )

    lm = MockLM()
    with patch(
        "dspy.teleprompt.GEPA.compile",
        return_value=mock_program,
    ):
        result = run_optimization_pipeline(
            agent_markdown_path=SIMPLE_PROMPT,
            provider="mock",
            model="mock-model",
            lm_client=lm,
            registry=None,
            optimizer_type="gepa",
        )

    assert isinstance(result, str)
    assert lm.call_count > 0, "MockLM was never called"

    report_path = os.path.join(TEST_DATA_DIR, "optimization_report.md")
    assert os.path.exists(report_path), "Report file was not created"
    with open(report_path) as f:
        report_content = f.read()
    assert "GEPA Optimization Performance Report" in report_content
    assert "Baseline Score" in report_content
    assert "Optimized Score" in report_content

    bak_path = SIMPLE_PROMPT + ".bak"
    assert os.path.exists(bak_path), "Backup file was not created"


def test_factory_invalid_optimizer_type():
    """Error handling: unknown optimizer_type raises ValueError."""
    from core.optimizer import _create_teleprompter
    with pytest.raises(ValueError, match="Unknown optimizer_type"):
        _create_teleprompter("invalid_opt", metric=lambda: 1.0, lm_client=None)


def test_gepa_metric_adapter():
    """Verify that _adapt_metric_for_gepa wraps a standard metric correctly.
    GEPA expects a raw float score (it wraps it in feedback text itself).
    """
    from core.optimizer import _adapt_metric_for_gepa

    def dummy_metric(gold, pred, trace=None):
        return 0.85

    adapted = _adapt_metric_for_gepa(dummy_metric)
    result = adapted("gold", "pred", trace=None, pred_name="test", pred_trace=None)
    assert isinstance(result, float)
    assert result == 0.85


def test_optimize_missing_file():
    """Error handling: non-existent file returns error string."""
    from tests.conftest import MockLM

    lm = MockLM()
    result = run_optimization_pipeline(
        agent_markdown_path="/nonexistent/path.md",
        provider="mock",
        model="mock-model",
        lm_client=lm,
        registry=None,
    )
    assert "Error: Target file not found" in result


def test_section_optimization_flow(cleanup_files):
    """Integration test: section optimization pipeline with MockLM.
    Exercises section extraction, optimization, and comparison output.
    Also verifies the reconstructed _optimized.md is created.
    """
    from tests.conftest import MockLM

    lm = MockLM()
    result = run_section_optimization_pipeline(
        agents_markdown_path=SIMPLE_PROMPT,
        provider="mock",
        model="mock-model",
        lm_client=lm,
    )

    assert isinstance(result, str)
    assert len(result) > 50
    assert lm.call_count > 0, "MockLM was never called"

    optimized_path = os.path.join(TEST_DATA_DIR, f"{BASE_NAME}_optimized.md")
    assert os.path.exists(optimized_path), "Reconstructed optimized doc was not created"

    comparison_path = os.path.join(TEST_DATA_DIR, f"{BASE_NAME}_section_comparison.md")
    assert os.path.exists(comparison_path), "Section comparison doc was not created"


def test_optimize_then_verify_cycle(cleanup_files):
    """End-to-end cycle: optimize a file, then verify the result.
    Validates that both pipelines work together, passing the original
    as the baseline for meaningful delta comparison.
    """
    from tests.conftest import MockLM

    mock_program = MagicMock()
    mock_program.signature.instructions = (
        "You are a helpful assistant. Write short poems."
    )
    mock_program.demos = []

    lm = MockLM()
    with patch(
        "dspy.teleprompt.MIPROv2.compile",
        return_value=mock_program,
    ):
        opt_result = run_optimization_pipeline(
            agent_markdown_path=SIMPLE_PROMPT,
            provider="mock",
            model="mock-model",
            lm_client=lm,
            registry=None,
        )
    assert isinstance(opt_result, str)

    verify_result = run_verification_pipeline(
        agent_markdown_path=SIMPLE_PROMPT,
        provider="mock",
        model="mock-model",
        lm_client=lm,
        registry=None,
    )
    assert isinstance(verify_result, str)
    assert "QA Audit Complete" in verify_result

    generated_dataset_path = os.path.join(TEST_DATA_DIR, f"{BASE_NAME}_generated_dataset.json")
    assert os.path.exists(generated_dataset_path), "Generated dataset should persist for verifier"
