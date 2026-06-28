import pytest
import os
import json
from unittest.mock import patch, MagicMock, mock_open
from core.base_skill import BaseSkill
from core.skills import SkillRegistry
from core.skills.file_modifier import SurgicalFileModifierSkill
from core.skills.model_connector import ModelConnectorSkill
from core.skills.spec_optimizer import SpecStructuralIsolationSkill
from core.skills.dataset_logger import DatasetLoggingSkill
import dspy

def test_cannot_instantiate_incomplete_skill():
    with pytest.raises(TypeError):
        class BrokenSkill(BaseSkill): pass
        BrokenSkill()

def test_registry_lifecycle_and_lookup():
    registry = SkillRegistry()
    skill = registry.get_skill("surgical_file_modifier")
    assert isinstance(skill, SurgicalFileModifierSkill)

@patch("os.path.exists")
def test_file_modifier_handles_missing_files(mock_exists):
    mock_exists.return_value = False
    skill = SurgicalFileModifierSkill()
    with pytest.raises(FileNotFoundError):
        skill.execute(file_path="missing.md", new_prompt="...", demos=[])

@patch("dspy.LM")
@patch("dspy.configure")
def test_model_connector_strategy(mock_dspy_configure, mock_dspy_lm):
    mock_lm_instance = MagicMock()
    mock_dspy_lm.return_value = mock_lm_instance
    skill = ModelConnectorSkill()
    result = skill.execute(provider="lm-studio", model="custom-llama-3")
    assert result is not None

@patch("os.path.exists")
def test_spec_optimizer_validation_guard_catches_bad_data(mock_exists):
    mock_exists.return_value = True
    mock_input_schema = '{"type": "object", "description": "old text"}'
    m_open = mock_open(read_data=mock_input_schema)
    skill = SpecStructuralIsolationSkill()

    def broken_dspy_callback(text):
        return {"this-should-be-a-string-but-is-a-bad-dict-nest"}

    with patch("builtins.open", m_open):
        with pytest.raises(RuntimeError) as exc_info:
            skill.execute(file_path="mock_spec.json", optimize_callback=broken_dspy_callback)

    assert "Validation Failure" in str(exc_info.value)

def test_dataset_logger_empty_dataset():
    skill = DatasetLoggingSkill()
    result = skill.execute(dataset=[], output_path="agents/generated_dataset.json")
    assert "Skipped" in result


# =====================================================================
# SECTION OPTIMIZATION TESTS
# =====================================================================

def test_extract_sections_from_markdown():
    from core.optimizer import extract_sections_from_markdown
    sample_path = os.path.join(os.path.dirname(__file__), "test_data", "sample_AGENTS.md")
    sections = extract_sections_from_markdown(sample_path)
    assert len(sections) >= 5, f"Expected at least 5 sections, got {len(sections)}"
    headers = [s["header"] for s in sections]
    assert "## Setup" in headers
    assert "## Run" in headers
    assert "## Key facts for editing" in headers
    assert "## Design reference" in headers
    for s in sections:
        assert "header" in s
        assert "body" in s
        assert len(s["body"]) >= 10, f"Section {s['header']} body too short"


def test_compute_text_similarity():
    from core.optimizer import compute_text_similarity
    assert compute_text_similarity("identical", "identical") == 1.0
    assert compute_text_similarity("abc", "xyz") == 0.0
    result = compute_text_similarity("hello world", "hello there")
    assert 0.0 < result < 1.0


@patch("os.path.exists")
def test_section_pipeline_missing_file(mock_exists):
    from core.optimizer import run_section_optimization_pipeline
    mock_exists.return_value = False
    result = run_section_optimization_pipeline("nonexistent.md", "lm-studio", "")
    assert "Error: Target file not found" in result


def test_section_pipeline_imports():
    from core.server import optimize_agents_file_by_section
    assert callable(optimize_agents_file_by_section)


# =====================================================================
# VERIFICATION SKILL TESTS
# =====================================================================

def test_verifier_skill_registered():
    registry = SkillRegistry()
    skill = registry.get_skill("prompt_verifier")
    from core.skills.verifier import VerificationSkill
    assert isinstance(skill, VerificationSkill)


def test_verifier_skill_name_and_description():
    from core.skills.verifier import VerificationSkill
    skill = VerificationSkill()
    assert skill.name == "prompt_verifier"
    assert "blind out-of-sample evaluation" in skill.description


@patch("os.path.exists")
def test_verifier_handles_missing_file(mock_exists):
    mock_exists.return_value = False
    from core.skills.verifier import VerificationSkill
    skill = VerificationSkill()
    with pytest.raises(FileNotFoundError):
        skill.execute(agent_markdown_path="nonexistent.md", lm_client=None)


@patch("core.skills.verifier.extract_and_load_dataset")
@patch("core.skills.verifier.dspy.Predict")
@patch("core.skills.verifier.Evaluate")
@patch("dspy.context")
@patch("builtins.open")
def test_verifier_returns_structured_result(
    mock_open, mock_dspy_context, mock_evaluate_cls,
    mock_predict_cls, mock_extract
):
    import dspy
    from core.skills.verifier import VerificationSkill

    mock_open.return_value.__enter__.return_value.read.return_value = (
        "---\nmodel: test\n---\n\nYou are a helpful assistant."
    )

    mock_lm = MagicMock()

    mock_predict_response = MagicMock()
    mock_predict_response.json_dataset = '[{"input_context": "test", "gold_response": "ok"}]'
    mock_predict_instance = MagicMock()
    mock_predict_instance.return_value = mock_predict_response
    mock_predict_cls.return_value = mock_predict_instance

    mock_extract.return_value = [
        dspy.Example(input_context="test", output_response="ok").with_inputs("input_context")
    ]

    mock_evaluator = MagicMock()
    mock_evaluate_cls.return_value = mock_evaluator
    mock_evaluator.side_effect = [0.7, 0.9]

    skill = VerificationSkill()
    result = skill.execute(
        agent_markdown_path="agents/writer.md",
        lm_client=mock_lm,
    )

    assert isinstance(result, dict)
    assert "baseline_score" in result
    assert "optimized_score" in result
    assert "generalization_delta" in result
    assert "verdict" in result
    assert result["verdict"] == "PASS"
    assert result["generalization_delta"] > 0
    assert result.get("baseline_source") == "hardcoded default"


@patch("core.skills.verifier.extract_and_load_dataset")
@patch("core.skills.verifier.dspy.Predict")
@patch("core.skills.verifier.Evaluate")
@patch("dspy.context")
@patch("builtins.open")
@patch("os.path.exists")
def test_verifier_uses_original_markdown_path(
    mock_exists, mock_open, mock_dspy_context, mock_evaluate_cls,
    mock_predict_cls, mock_extract
):
    import dspy
    from core.skills.verifier import VerificationSkill

    # os.path.exists should return True for the original file path
    mock_exists.side_effect = lambda p: p == "original.md" or p == "agents/writer.md"

    # Mock open to return different content for original vs optimized
    def _mock_open_side_effect(*args, **kwargs):
        handle = MagicMock()
        if args[0] == "original.md":
            handle.__enter__.return_value.read.return_value = (
                "---\nmodel: orig\n---\n\nOriginal prompt content."
            )
        else:
            handle.__enter__.return_value.read.return_value = (
                "---\nmodel: opt\n---\n\nOptimized prompt content."
            )
        return handle

    mock_open.side_effect = _mock_open_side_effect

    mock_lm = MagicMock()

    mock_predict_response = MagicMock()
    mock_predict_response.json_dataset = '[{"input_context": "test", "gold_response": "ok"}]'
    mock_predict_instance = MagicMock()
    mock_predict_instance.return_value = mock_predict_response
    mock_predict_cls.return_value = mock_predict_instance

    mock_extract.return_value = [
        dspy.Example(input_context="test", output_response="ok").with_inputs("input_context")
    ]

    mock_evaluator = MagicMock()
    mock_evaluate_cls.return_value = mock_evaluator
    mock_evaluator.side_effect = [0.5, 0.9]

    skill = VerificationSkill()
    result = skill.execute(
        agent_markdown_path="agents/writer.md",
        original_markdown_path="original.md",
        lm_client=mock_lm,
    )

    assert result.get("baseline_source") == "original.md"
    assert result["baseline_score"] == 50.0
    assert result["optimized_score"] == 90.0
    assert result["verdict"] == "PASS"


@patch("core.skills.verifier.extract_and_load_dataset")
@patch("core.skills.verifier.dspy.Predict")
@patch("core.skills.verifier.Evaluate")
@patch("dspy.context")
@patch("builtins.open")
def test_verifier_detects_overfitting(
    mock_open, mock_dspy_context, mock_evaluate_cls,
    mock_predict_cls, mock_extract
):
    import dspy
    from core.skills.verifier import VerificationSkill

    mock_open.return_value.__enter__.return_value.read.return_value = (
        "---\nmodel: test\n---\n\nOptimized instructions."
    )

    mock_lm = MagicMock()

    mock_predict_response = MagicMock()
    mock_predict_response.json_dataset = '[{"input_context": "test", "gold_response": "ok"}]'
    mock_predict_instance = MagicMock()
    mock_predict_instance.return_value = mock_predict_response
    mock_predict_cls.return_value = mock_predict_instance

    mock_extract.return_value = [
        dspy.Example(input_context="test", output_response="ok").with_inputs("input_context")
    ]

    mock_evaluator = MagicMock()
    mock_evaluate_cls.return_value = mock_evaluator
    mock_evaluator.side_effect = [0.8, 0.4]

    skill = VerificationSkill()
    result = skill.execute(
        agent_markdown_path="agents/writer.md",
        lm_client=mock_lm,
    )

    assert result["verdict"] == "OVERFIT"
    assert result["generalization_delta"] < 0
