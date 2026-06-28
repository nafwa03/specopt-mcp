import pytest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock
import dspy


# =====================================================================
# CHUNKING TESTS
# =====================================================================

def test_chunk_text_small_doc():
    from core.optimizer import chunk_text
    text = "Small document that fits in one chunk."
    chunks = chunk_text(text, chunk_size=4000, chunk_overlap=200)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_large_doc():
    from core.optimizer import chunk_text
    text = "A" * 5000
    chunks = chunk_text(text, chunk_size=2000, chunk_overlap=200)
    assert len(chunks) >= 2
    total = sum(len(c) for c in chunks)
    assert total >= len(text)


def test_chunk_text_overlap():
    from core.optimizer import chunk_text
    text = "X" * 3000
    chunks = chunk_text(text, chunk_size=1500, chunk_overlap=300)
    assert len(chunks) >= 2
    assert len(chunks[0]) == 1500
    if len(chunks) > 1:
        assert len(chunks[-1]) <= 1500


def test_chunk_text_empty():
    from core.optimizer import chunk_text
    assert chunk_text("", chunk_size=100, chunk_overlap=10) == []


def test_chunk_text_no_overlap():
    from core.optimizer import chunk_text
    text = "AB" * 1000
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=0)
    if len(chunks) > 1:
        assert chunks[0][-1] != chunks[1][0]


# =====================================================================
# CURATION TESTS
# =====================================================================

def test_curate_dataset_empty():
    from core.optimizer import curate_dataset
    lm_client = MagicMock()
    result = curate_dataset(lm_client, [], threshold=7.0)
    assert result == []


@patch("core.optimizer._score_example_quality")
def test_curate_dataset_threshold(mock_score):
    from core.optimizer import curate_dataset
    examples = [
        dspy.Example(input_context="q1", output_response="a1").with_inputs("input_context"),
        dspy.Example(input_context="q2", output_response="a2").with_inputs("input_context"),
        dspy.Example(input_context="q3", output_response="a3").with_inputs("input_context"),
    ]
    mock_score.side_effect = [9.0, 5.0, 8.0]
    lm_client = MagicMock()
    result = curate_dataset(lm_client, examples, threshold=7.0)
    assert len(result) == 2


@patch("core.optimizer._score_example_quality")
def test_curate_dataset_max_examples(mock_score):
    from core.optimizer import curate_dataset
    examples = [
        dspy.Example(input_context=f"q{i}", output_response=f"a{i}").with_inputs("input_context")
        for i in range(5)
    ]
    mock_score.side_effect = [9.0, 8.0, 7.0, 6.0, 5.0]
    lm_client = MagicMock()
    result = curate_dataset(lm_client, examples, threshold=6.0, max_examples=2)
    assert len(result) == 2
    assert result[0].input_context == "q0"
    assert result[1].input_context == "q1"


@patch("core.optimizer._score_example_quality")
def test_curate_dataset_all_below_threshold(mock_score):
    from core.optimizer import curate_dataset
    examples = [
        dspy.Example(input_context="q1", output_response="a1").with_inputs("input_context"),
    ]
    mock_score.side_effect = [2.0]
    lm_client = MagicMock()
    result = curate_dataset(lm_client, examples, threshold=7.0)
    assert len(result) == 0


# =====================================================================
# FORMAT CONVERSION TESTS
# =====================================================================

def test_convert_dataset_format_json():
    from core.optimizer import convert_dataset_format
    examples = [
        dspy.Example(input_context="hello", output_response="world").with_inputs("input_context"),
    ]
    text = convert_dataset_format(examples, fmt="json")
    data = json.loads(text)
    assert len(data) == 1
    assert data[0]["input_context"] == "hello"
    assert data[0]["gold_response"] == "world"


def test_convert_dataset_format_jsonl():
    from core.optimizer import convert_dataset_format
    examples = [
        dspy.Example(input_context="q1", output_response="a1").with_inputs("input_context"),
        dspy.Example(input_context="q2", output_response="a2").with_inputs("input_context"),
    ]
    text = convert_dataset_format(examples, fmt="jsonl")
    lines = text.strip().split("\n")
    assert len(lines) == 2
    for i, line in enumerate(lines):
        obj = json.loads(line)
        assert obj["input_context"] == f"q{i+1}"


def test_convert_dataset_format_alpaca():
    from core.optimizer import convert_dataset_format
    examples = [
        dspy.Example(input_context="user query", output_response="agent answer").with_inputs("input_context"),
    ]
    text = convert_dataset_format(examples, fmt="alpaca")
    data = json.loads(text)
    assert len(data) == 1
    assert data[0]["instruction"] == "Respond to the user query based on the agent's system prompt."
    assert data[0]["input"] == "user query"
    assert data[0]["output"] == "agent answer"


def test_convert_dataset_format_chatml():
    from core.optimizer import convert_dataset_format
    examples = [
        dspy.Example(input_context="user msg", output_response="assistant msg").with_inputs("input_context"),
    ]
    text = convert_dataset_format(examples, fmt="chatml")
    data = json.loads(text)
    assert len(data) == 1
    assert data[0]["messages"][0]["role"] == "user"
    assert data[0]["messages"][0]["content"] == "user msg"
    assert data[0]["messages"][1]["role"] == "assistant"
    assert data[0]["messages"][1]["content"] == "assistant msg"


def test_convert_dataset_format_fallback():
    from core.optimizer import convert_dataset_format
    examples = [
        dspy.Example(input_context="test", output_response="result").with_inputs("input_context"),
    ]
    text = convert_dataset_format(examples, fmt="unknown_format")
    data = json.loads(text)
    assert len(data) == 1
    assert data[0]["input_context"] == "test"


def test_convert_dataset_format_empty():
    from core.optimizer import convert_dataset_format
    text = convert_dataset_format([], fmt="json")
    data = json.loads(text)
    assert data == []


# =====================================================================
# READ DOCUMENT FILE TESTS
# =====================================================================

def test_read_document_file_txt():
    from core.optimizer import read_document_file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Hello world")
        tmp = f.name
    try:
        content = read_document_file(tmp)
        assert content == "Hello world"
    finally:
        os.unlink(tmp)


def test_read_document_file_json():
    from core.optimizer import read_document_file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"key": "value"}, f)
        tmp = f.name
    try:
        content = read_document_file(tmp)
        assert "key" in content
        assert "value" in content
    finally:
        os.unlink(tmp)


def test_read_document_file_missing():
    from core.optimizer import read_document_file
    content = read_document_file("/nonexistent/path.txt")
    assert content == ""


def test_read_document_file_unsupported_ext():
    from core.optimizer import read_document_file
    content = read_document_file("/tmp/test.xyz")
    assert content == ""


# =====================================================================
# PIPELINE TESTS
# =====================================================================

@patch("core.optimizer.ConfigLoader.get")
@patch("core.optimizer._get_lm_client")
def test_run_dataset_generation_pipeline_missing_file(mock_get_lm, mock_cfg_get):
    from core.optimizer import run_dataset_generation_pipeline
    result = run_dataset_generation_pipeline("nonexistent.md", "lm-studio", "")
    assert "Error: Target file not found" in result


@patch("os.path.exists")
@patch("core.optimizer.ConfigLoader.get")
@patch("core.optimizer._get_lm_client")
@patch("builtins.open")
def test_run_dataset_generation_pipeline_output_format_jsonl(mock_open, mock_get_lm, mock_cfg_get, mock_exists):
    from core.optimizer import run_dataset_generation_pipeline
    mock_exists.return_value = True
    mock_cfg_get.side_effect = lambda *keys: {
        ("file_suffixes", "generated_dataset"): "_generated_dataset.json",
    }.get(tuple(keys), "test")
    mock_lm = MagicMock()
    mock_lm.return_value = [
        json.dumps([{"input_context": "test", "gold_response": "ok"} for _ in range(3)])
    ]
    mock_get_lm.return_value = mock_lm
    mock_open.return_value.__enter__.return_value.read.return_value = \
        "---\nmodel: test\n---\n\nAgent prompt."
    result = run_dataset_generation_pipeline(
        "agents/test.md", "lm-studio", "",
        num_examples=3, output_format="jsonl"
    )
    assert "Success!" in result
    assert "jsonl" in result.lower()


@patch("os.path.exists")
@patch("core.optimizer.ConfigLoader.get")
@patch("core.optimizer._get_lm_client")
@patch("builtins.open")
def test_run_dataset_generation_pipeline_output_format_alpaca(mock_open, mock_get_lm, mock_cfg_get, mock_exists):
    from core.optimizer import run_dataset_generation_pipeline
    mock_exists.return_value = True
    mock_cfg_get.side_effect = lambda *keys: {
        ("file_suffixes", "generated_dataset"): "_generated_dataset.json",
    }.get(tuple(keys), "test")
    mock_lm = MagicMock()
    mock_lm.return_value = [
        json.dumps([{"input_context": "user query", "gold_response": "agent answer"}])
    ]
    mock_get_lm.return_value = mock_lm
    mock_open.return_value.__enter__.return_value.read.return_value = \
        "---\n---\nTest agent."
    result = run_dataset_generation_pipeline(
        "agents/test.md", "lm-studio", "",
        num_examples=1, output_format="alpaca"
    )
    assert "Success!" in result
    assert "alpaca" in result.lower()


@patch("os.path.exists")
@patch("core.optimizer.ConfigLoader.get")
@patch("core.optimizer._get_lm_client")
@patch("builtins.open")
def test_run_dataset_generation_pipeline_with_curation(mock_open, mock_get_lm, mock_cfg_get, mock_exists):
    from core.optimizer import run_dataset_generation_pipeline
    mock_exists.return_value = True
    mock_cfg_get.side_effect = lambda *keys: {
        ("file_suffixes", "generated_dataset"): "_generated_dataset.json",
        ("pipeline", "curation", "threshold"): 7.0,
    }.get(tuple(keys), "test")
    mock_lm = MagicMock()
    mock_lm.return_value = [
        json.dumps([{"input_context": "q1", "gold_response": "a1"} for _ in range(3)])
    ]
    mock_get_lm.return_value = mock_lm
    mock_open.return_value.__enter__.return_value.read.return_value = \
        "---\n---\nAgent."
    result = run_dataset_generation_pipeline(
        "agents/test.md", "lm-studio", "",
        num_examples=3, curate=True
    )
    assert "Success!" in result


# =====================================================================
# TOOL REGISTRATION TESTS
# =====================================================================

def test_generate_training_dataset_tool_registered():
    from core.server import generate_training_dataset
    assert callable(generate_training_dataset)


def test_generate_training_dataset_has_new_params():
    import inspect
    from core.server import generate_training_dataset
    sig = inspect.signature(generate_training_dataset)
    params = list(sig.parameters.keys())
    assert "curate" in params
    assert "curation_threshold" in params
    assert "output_format" in params


# =====================================================================
# GENERATION HELPER TESTS
# =====================================================================

def test_extract_and_load_dataset_valid_json():
    from core.optimizer import extract_and_load_dataset
    raw = json.dumps([{"input_context": "test query", "gold_response": "test answer"}])
    result = extract_and_load_dataset(raw)
    assert len(result) == 1
    assert result[0].input_context == "test query"
    assert result[0].output_response == "test answer"


def test_extract_and_load_dataset_fallback():
    from core.optimizer import extract_and_load_dataset
    result = extract_and_load_dataset("not valid json at all")
    assert len(result) == 2


def test_extract_and_load_dataset_with_code_fence():
    from core.optimizer import extract_and_load_dataset
    raw = "```json\n[{\"input_context\": \"q\", \"gold_response\": \"a\"}]\n```"
    result = extract_and_load_dataset(raw)
    assert len(result) == 1
    assert result[0].input_context == "q"
