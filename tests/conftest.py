import json
import dspy
from typing import Optional, List


class MockLM(dspy.BaseLM):
    """Deterministic LM that returns JSON responses matching DSPy output field names.

    ChatAdapter tries FieldName: value format first, then falls back to JSONAdapter
    which parses JSON objects with output field keys. This MockLM returns JSON
    so JSONAdapter can parse it successfully.
    """

    def __init__(self, model: str = "mock-model", mode: str = "pass"):
        self.model = model
        self.mode = mode
        self.call_count = 0
        self.history: List[str] = []
        super().__init__(model=model)

    def __call__(
        self, prompt: Optional[str] = None,
        messages: Optional[list] = None, **kwargs
    ) -> List[str]:
        self.call_count += 1
        prompt_text = prompt or ""
        if messages:
            last = messages[-1] if messages else {}
            prompt_text = last.get("content", str(messages))
        prompt_lower = prompt_text.lower()
        self.history.append(prompt_text[:200])

        if "json_dataset" in prompt_lower or "generate a json array" in prompt_lower:
            dataset = json.dumps([
                {"input_context": "Write a short poem.",
                 "gold_response": "Roses are red."}
            ])
            return [json.dumps({"json_dataset": dataset})]

        if "injection_vulnerability" in prompt_lower:
            return [json.dumps({"injection_vulnerability_detected": "NO"})]

        if "contains_false_information" in prompt_lower:
            return [json.dumps({"contains_false_information": "NO"})]

        if "verdict" in prompt_lower and "input_context" in prompt_lower:
            if self.mode == "overfit" and self.call_count > 3:
                return [json.dumps({"verdict": "NO"})]
            return [json.dumps({"verdict": "YES"})]

        if "output_response" in prompt_lower:
            return [json.dumps({"output_response": f"Mock output #{self.call_count}"})]

        if "optimized_section" in prompt_lower:
            return [json.dumps({"optimized_section": "Mock optimized section content."})]

        if "quality_score" in prompt_lower:
            return [json.dumps({"quality_score": 50})]

        if "optimized_python_code" in prompt_lower:
            return [json.dumps({"optimized_python_code": "def foo(): pass"})]

        if "optimized_description" in prompt_lower:
            return [json.dumps({"optimized_description": "Mock optimized description."})]

        return [json.dumps({"output_response": f"Default mock #{self.call_count}"})]

    def copy(self, **kwargs):
        return MockLM(
            model=kwargs.get("model", self.model),
            mode=self.mode,
        )


# ---------------------------------------------------------------------------
# Fixtures for optimize_anything adapter tests
# ---------------------------------------------------------------------------

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_optimize_anything():
    mock_result = MagicMock()
    mock_result.best_candidate = "Optimized content result"
    mock_result.val_aggregate_scores = [0.85]
    mock_result.candidates = [{"text": "Optimized content result"}]
    mock_result.total_metric_calls = 10
    with patch("core.optimize_anything_adapter._build_gepa_config", return_value=None):
        with patch(
            "core.optimize_anything_adapter._oa_optimize_anything",
            return_value=mock_result,
        ):
            with patch("core.optimize_anything_adapter._OA_AVAILABLE", True):
                yield


@pytest.fixture
def sample_markdown_file(tmp_path):
    p = tmp_path / "test_skill.md"
    p.write_text("# Test Skill\n\n## Overview\nA test skill.\n\n## Rules\n- Rule one\n- Rule two\n")
    return str(p)


@pytest.fixture
def sample_python_file(tmp_path):
    p = tmp_path / "test_script.py"
    p.write_text("def hello():\n    print('hello')\n")
    return str(p)


@pytest.fixture
def sample_yaml_file(tmp_path):
    p = tmp_path / "test_config.yaml"
    p.write_text("key: value\nnested:\n  inner: 42\n")
    return str(p)


@pytest.fixture
def sample_json_file(tmp_path):
    p = tmp_path / "test_data.json"
    p.write_text('{"name": "test", "count": 3}\n')
    return str(p)


@pytest.fixture
def sample_shell_file(tmp_path):
    p = tmp_path / "test_script.sh"
    p.write_text("#!/bin/bash\necho 'hello'\n")
    return str(p)
