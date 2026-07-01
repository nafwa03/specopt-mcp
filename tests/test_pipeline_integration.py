import dspy
import glob
import json
import os
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
    return (
        glob.glob(SIMPLE_PROMPT + ".*.bak")
        + [
            os.path.join(TEST_DATA_DIR, "optimization_report.md"),
            os.path.join(TEST_DATA_DIR, f"{BASE_NAME}_generated_dataset.json"),
            os.path.join(TEST_DATA_DIR, f"{BASE_NAME}_section_comparison.md"),
            os.path.join(TEST_DATA_DIR, f"{BASE_NAME}_optimized.md"),
            os.path.join(TEST_DATA_DIR, f"{BASE_NAME}_compiled_prompt.txt"),
        ]
    )


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

    bak_files = glob.glob(SIMPLE_PROMPT + ".*.bak")
    assert len(bak_files) > 0, "Timestamped backup file was not created"

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

    bak_files = glob.glob(SIMPLE_PROMPT + ".*.bak")
    assert len(bak_files) > 0, "Timestamped backup file was not created"


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


# ---------------------------------------------------------------------------
# optimize_anything adapter tests
# ---------------------------------------------------------------------------


def test_detect_artifact_type():
    from core.optimize_anything_adapter import detect_artifact_type

    assert detect_artifact_type("file.md") == "markdown"
    assert detect_artifact_type("file.py") == "python"
    assert detect_artifact_type("file.yaml") == "yaml"
    assert detect_artifact_type("file.json") == "json"
    assert detect_artifact_type("file.sh") == "shell"
    assert detect_artifact_type("file.txt") == "text"
    assert detect_artifact_type("file.unknown") == "text"
    assert detect_artifact_type("file.json", '{"a": 1}') == "json"


def test_estimate_tokens():
    from core.optimize_anything_adapter import estimate_tokens

    text = "hello world " * 100
    count = estimate_tokens(text)
    assert count > 0


def test_extract_code_blocks():
    from core.optimize_anything_adapter import extract_code_blocks

    text = "Some text\n```python\nprint('hello')\n```\nMore text\n```bash\necho hi\n```"
    blocks = extract_code_blocks(text)
    assert len(blocks) == 2
    assert blocks[0]["language"] == "python"
    assert blocks[1]["language"] == "bash"


def test_validate_code_syntax_python_ok():
    from core.optimize_anything_adapter import validate_code_syntax

    errors = validate_code_syntax("x = 1", "python")
    assert errors == []


def test_validate_code_syntax_python_error():
    from core.optimize_anything_adapter import validate_code_syntax

    errors = validate_code_syntax("x = ", "python")
    assert len(errors) >= 1


def test_validate_markdown_structure():
    from core.optimize_anything_adapter import validate_markdown_structure

    text = "# Title\n\n## Overview\nContent\n\n## Rules\n- rule\n"
    issues = validate_markdown_structure(text)
    assert issues == []

    text = "# Title\n\n## Details\nContent\n"
    issues = validate_markdown_structure(text)
    assert any("Overview" in i for i in issues)


def test_compute_regressions():
    from core.optimize_anything_adapter import compute_regressions

    orig = "line one\nline two\nline three\n"
    cand = "line one\nmodified two\nline three\n"
    regressions = compute_regressions(orig, cand)
    assert len(regressions) >= 1
    assert regressions[0]["type"] == "line_changed"


def test_compute_composite_score():
    from core.optimize_anything_adapter import compute_composite_score

    score = compute_composite_score(
        conciseness={"score": 1.0},
        syntax_errors=[],
        structural_issues=[],
        regressions=[],
        format_issues=[],
    )
    assert score == 1.0

    score = compute_composite_score(
        conciseness={"score": 0.5},
        syntax_errors=[{"language": "python", "line": 1, "error": "syntax err"}],
        structural_issues=["Missing section"],
        regressions=[{"type": "line_changed", "before": "a", "after": "b"}],
        format_issues=["trailing whitespace"],
    )
    assert 0.0 <= score < 1.0


def test_check_format_adherence():
    from core.optimize_anything_adapter import check_format_adherence

    issues = check_format_adherence("line one\nline two  \nline three\n")
    assert len(issues) >= 1


def test_make_universal_evaluator(sample_markdown_file):
    from core.optimize_anything_adapter import make_universal_evaluator

    with open(sample_markdown_file) as f:
        content = f.read()

    evaluator = make_universal_evaluator("markdown", content)
    score, asi = evaluator(content)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
    assert "Conciseness" in asi
    assert "SyntaxErrors" in asi
    assert "StructuralIssues" in asi
    assert "Regressions" in asi
    assert "FormatIssues" in asi


def test_run_optimize_anything_pipeline(sample_markdown_file, mock_optimize_anything):
    from core.optimize_anything_adapter import run_optimize_anything_pipeline

    result = run_optimize_anything_pipeline(
        artifact_path=sample_markdown_file,
        objective="Test optimization",
        max_metric_calls=5,
    )
    assert isinstance(result, str)
    assert "optimize_anything" in result
    assert "Optimization Complete" in result


def test_run_optimize_anything_pipeline_missing_file():
    from core.optimize_anything_adapter import run_optimize_anything_pipeline

    result = run_optimize_anything_pipeline(
        artifact_path="/nonexistent/path.md",
    )
    assert "Error: Target file not found" in result


def test_run_optimize_anything_pipeline_with_reference(sample_markdown_file, tmp_path, mock_optimize_anything):
    from core.optimize_anything_adapter import run_optimize_anything_pipeline

    ref = tmp_path / "reference.md"
    ref.write_text("# Reference\n\n## Overview\nRef\n\n## Rules\n- r1\n")

    result = run_optimize_anything_pipeline(
        artifact_path=sample_markdown_file,
        reference_path=str(ref),
        objective="Test with reference",
    )
    assert isinstance(result, str)
    assert "Optimization Complete" in result


def test_run_optimize_anything_pipeline_multi_task(sample_markdown_file, sample_python_file, tmp_path, mock_optimize_anything):
    from core.optimize_anything_adapter import run_optimize_anything_pipeline

    result = run_optimize_anything_pipeline(
        artifact_path=sample_markdown_file,
        objective="Multi-task optimization",
        dataset_paths=[sample_python_file],
    )
    assert isinstance(result, str)
    assert "multi-task" in result


def test_evaluator_python_detects_syntax_errors(tmp_path):
    from core.optimize_anything_adapter import make_universal_evaluator

    bad_code = "def broken(\n    print('missing parens')\n"
    evaluator = make_universal_evaluator("python", bad_code)
    score, asi = evaluator(bad_code)
    assert len(asi["SyntaxErrors"]) >= 1


def test_evaluator_tracks_conciseness(tmp_path):
    from core.optimize_anything_adapter import make_universal_evaluator

    long_content = "\n".join(f"line {i}" for i in range(300))
    evaluator = make_universal_evaluator("text", long_content, max_lines=150, max_tokens=50000)
    score, asi = evaluator(long_content)
    assert asi["Conciseness"]["lines"] == 300
    assert asi["Conciseness"]["score"] < 1.0


def test_detect_artifact_type_by_content():
    from core.optimize_anything_adapter import detect_artifact_type

    json_content = '{"key": "value"}'
    assert detect_artifact_type("unknown", json_content) == "json"

    yaml_content = "---\nkey: value\n"
    assert detect_artifact_type("unknown", yaml_content) == "yaml"

    text_content = "Just plain text\nwith no extension hint\n"
    assert detect_artifact_type("unknown", text_content) == "text"
