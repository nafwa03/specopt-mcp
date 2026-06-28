# specopt-mcp

DSPy-Powered Prompt & Code Optimization via the Model Context Protocol (MCP).

Two modes of operation:

- **MCP Server** (`core/server.py`): Exposes 8 optimization tools via stdio MCP. Connect any MCP client (opencode, etc.) for direct tool invocation. Tools are pre-registered via `@mcp.tool()` — no dynamic discovery.

- **Agent Brain** (`agent_brain.py`): A standalone LangChain agent that dynamically discovers markdown skill definitions from `skills/*.md` and injects them into its system prompt. The LLM autonomously reasons about which tools to invoke based on natural language requests.

Currently works with **LM Studio**. Includes stub connectors for **Ollama** and **Lemonade** that demonstrate the extension pattern for adding new providers. Includes synthetic dataset generation, LLM-as-judge curation, multi-stage secure evaluation metrics (injection detection, hallucination auditing), blind QA verification on unseen data, and a pluggable skill architecture.

---

## File Structure Blueprint

```
specopt-mcp/
│
├── core/
│   ├── server.py              # FastMCP stdio transport server (tool entrypoints)
│   ├── optimizer.py           # DSPy optimization pipelines (MIPROv2, GEPA)
│   ├── base_skill.py          # Abstract base class for pluggable skills
│   ├── skill_md_loader.py     # Parses skills/*.md into discoverable manifests
│   ├── config_loader.py       # YAML configuration loader
│   ├── prompt_loader.py       # YAML prompt/description loader
│   ├── artifact_cleanup.py    # Pipeline artifact archival utility
│   └── skills/
│       ├── __init__.py        # SkillRegistry (auto-registers all skills)
│       ├── model_connector.py # LM Studio (working); Ollama / Lemonade (stubs)
│       ├── file_modifier.py   # Surgical markdown file editing
│       ├── spec_optimizer.py  # JSON schema description enhancement
│       ├── verifier.py        # Blind out-of-sample QA evaluation
│       ├── dataset_logger.py  # Dataset persistence to disk
│       └── directory_scanner.py # File discovery and filtering
│
├── skills/                    # Markdown skill definitions (agent brain discovery)
│   ├── file_modifier.md
│   ├── model_connector.md
│   ├── dataset_logger.md
│   ├── prompt_archiver.md
│   └── dataset_metric.md
│
├── agents/
│   └── writer.md              # Sample agent prompt target file (for use with agent_brain.py standalone agent)
│
├── tests/
│   ├── conftest.py            # MockLM for deterministic testing
│   ├── test_skills.py         # Unit tests for skill classes + SkillMDLoader
│   └── test_pipeline_integration.py # Integration tests for pipelines
│
├── opencode.json              # opencode MCP server config
├── agent_brain.py             # LangChain agent with dynamic skill discovery
├── config.yaml                # Pipeline, provider, and artifact config
├── prompts.yaml               # DSPy signatures and tool descriptions
├── requirements.txt           # Python dependencies
├── setup.py                   # Console entrypoint: specopt-server
└── .gitignore
```

---

## MCP Tools

> **Note:** All tools require a running LM Studio instance at `http://localhost:1234/v1` by default. Change `api_base` in `config.yaml` to point to your provider. Only LM Studio is currently implemented; Ollama and Lemonade stubs show how to extend support.



### `optimize_agent_file`
Optimizes an agent markdown prompt file using MIPROv2 or GEPA. Optionally accepts a `document_dir` for supplementary reference docs (`.md`, `.txt`, `.json`, `.pdf`, `.docx`, `.html`, `.pptx`) to ground dataset generation. Automatically validates the generated dataset before optimization proceeds.

```python
# Direct MCP call
result = await session.call_tool("optimize_agent_file", {
    "agent_markdown_path": "./agents/writer.md",
    "provider": "lm-studio",
    "model": "",
    "optimizer_type": "mipro",
    "document_dir": "./reference_docs"
})
```
```
# Agent prompt
Optimize the agent prompt at './agents/writer.md' using LM Studio with 5 trials via MIPROv2
```

---

### `optimize_specification_file`
Enhances `description`, `summary`, and `title` fields in a JSON schema file using DSPy while preserving structural layout.

```python
result = await session.call_tool("optimize_specification_file", {
    "spec_json_path": "./api_spec.json",
    "provider": "lm-studio",
    "model": ""
})
```
```
# Agent prompt
Enhance all descriptions in './api_spec.json' using Ollama
```

---

### `optimize_skill_logic`
Optimizes Python skill source code using MIPROv2 or GEPA with an actual `pytest` suite run as the reward metric. The optimizer proposes code variants, syntax-checks them, swaps them in, runs `pytest tests/test_skills.py`, and reverts on failure.

```python
result = await session.call_tool("optimize_skill_logic", {
    "skill_file_path": "./core/skills/file_modifier.py",
    "provider": "lm-studio",
    "model": "",
    "optimizer_type": "mipro"
})
```
```
# Agent prompt
Refactor the Python skill at './core/skills/file_modifier.py' using GEPA and validate with pytest
```

---

### `optimize_agents_file_by_section`
Parses an AGENTS markdown file into sections by headers, optimizes each section independently, and outputs a side-by-side original-vs-optimized comparison document plus a reconstructed `_optimized.md` file.

```python
result = await session.call_tool("optimize_agents_file_by_section", {
    "agents_markdown_path": "./agents/writer.md",
    "provider": "lm-studio",
    "model": ""
})
```
```
# Agent prompt
Optimize each section of './agents/writer.md' independently and produce a side-by-side comparison
```

---

### `verify_prompt_generalization`
Runs a blind out-of-sample QA evaluation comparing the optimized prompt against the original (or a hardcoded fallback) on unseen test scenarios to detect generalization improvement or overfitting.

```python
result = await session.call_tool("verify_prompt_generalization", {
    "agent_markdown_path": "./agents/writer.md",
    "provider": "lm-studio",
    "model": ""
})
```
```
# Agent prompt
Run blind QA verification on './agents/writer.md' to check generalization on unseen data
```

---

### `generate_training_dataset`
Generates a synthetic training dataset from an agent markdown file without running the full optimization pipeline. Supports chunking for large supplementary docs, LLM-as-judge curation, and multiple output formats: `json`, `jsonl`, `alpaca`, `chatml`.

```python
result = await session.call_tool("generate_training_dataset", {
    "agent_markdown_path": "./agents/writer.md",
    "provider": "lm-studio",
    "model": "",
    "num_examples": 20,
    "document_dir": "./reference_docs",
    "curate": True,
    "curation_threshold": 7.0,
    "output_format": "alpaca"
})
```
```
# Agent prompt
Generate 20 training examples from './agents/writer.md' in Alpaca format and curate with quality threshold 7.0
```

---

### `validate_generated_dataset`
Validates a generated dataset against four quality criteria:
1. **Alignment** — LLM-as-Judge checks solvability, label correctness, and hardness
2. **Diversity** — sentence-transformers embedding similarity (target < 0.75)
3. **Baseline Failure Test** — unoptimized agent score (target 40–70%)
4. **Negative Class Ratio** — adversarial/out-of-scope cases (target ≥ 15%)

Returns a structured PASS/FAIL verdict with per-metric breakdown.

```python
result = await session.call_tool("validate_generated_dataset", {
    "dataset_path": "./agents/writer_generated_dataset.json",
    "agent_markdown_path": "./agents/writer.md",
    "provider": "lm-studio",
    "model": "",
    "document_dir": ""
})
```
```
# Agent prompt
Validate the dataset './agents/writer_generated_dataset.json' against all four quality criteria
```

---

### `cleanup_pipeline_artifacts`
Scans a directory for all pipeline-generated artifacts (`.bak`, `_optimized.*`, `_compiled_prompt.txt`, `_section_comparison.md`, `_generated_dataset.json`, `optimization_report.md`) and moves them to an `artifacts/<timestamp>/` folder.

```python
result = await session.call_tool("cleanup_pipeline_artifacts", {
    "directory_path": "./agents"
})
```
```
# Agent prompt
Clean up all pipeline artifacts in the './agents' directory
```

---

> **Provider Support:** Only **LM Studio** is fully functional. The `OllamaLM` and `LemonadeLM` classes in `core/skills/model_connector.py` are stub implementations that show the extension pattern for adding new providers — they return placeholder responses and need a real API client implementation to go live.

## Architecture

The system is organized in five layers:

| Layer | Component | Description |
|-------|-----------|-------------|
| **Transport** | `core/server.py` | FastMCP stdio server exposing 8 tools, threaded with AnyIO |
| **Pipeline** | `core/optimizer.py` | DSPy MIPROv2/GEPA optimizers, dataset generation, validation, verification |
| **Python Skill** | `core/skills/*.py` | Strategy-pattern skills registered in `SkillRegistry` |
| **Markdown Skill** | `skills/*.md` | Zero-code skill definitions discovered by `SkillMDLoader` |
| **Agent** | `agent_brain.py` | LangChain agent with dynamic skill discovery |

### Evaluation Pipeline Flow

```
Agent Markdown File
    │
    ▼
Dataset Generation (LLM-as-Judge) ──► Dataset Validation (4 criteria)
    │
    ▼
Baseline Evaluation (secure_universal_llm_metric)
    │
    ▼
MIPROv2 / GEPA Compile
    │
    ▼
Optimized Evaluation
    │
    ▼
Report Generation ──► QA Verification (blind out-of-sample)
```

The default evaluation metric is a 3-stage guard:
1. **Security Auditor** — rejects prompts with injection vulnerabilities
2. **Fact Grounding Auditor** — rejects hallucinated content
3. **Universal Judge** — passes only correct, non-trivial predictions

---

## Quickstart

```bash
# 1. Clone and set up a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install the server CLI entrypoint
pip install -e .

# 4. Run tests
pytest -v

# Mode 1 — Start the MCP server (for opencode):
python -m core.server

# Mode 2 — Launch the LangChain agent brain (standalone):
python agent_brain.py
```

---

## Two Modes of Operation

| | Mode 1: MCP Server | Mode 2: Agent Brain |
|---|---|---|
| **Entry point** | `core/server.py` (via `specopt-server`) | `agent_brain.py` |
| **Client** | opencode, or any MCP client over stdio | Standalone terminal script |
| **Tool source** | 8 hardcoded `@mcp.tool()` functions | Dynamic discovery from `skills/*.md` |
| **Markdown skill awareness** | Not aware | Fully aware via `SkillMDLoader` |
| **LLM orchestration** | Handled by the client (e.g., opencode) | Built-in LangChain agent loop |
| **Best for** | Direct optimization via chat | Autonomous multi-step reasoning |

---

## Mode 1: MCP Server (for opencode)

### opencode Integration

Add the following to `opencode.json` or `opencode.jsonc` in your project root:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "specopt": {
      "type": "local",
      "command": ["specopt-server"],
      "enabled": true
    }
  },
  "experimental": {
    "mcp_timeout": 36000000
  }
}
```

> **Note:** The `specopt-server` command is registered by `setup.py` via `pip install -e .`. If you prefer not to install the entrypoint, use:
> ```jsonc
> "command": ["python", "-m", "core.server"]
> ```

Once configured, opencode discovers all 8 MCP tools automatically. You can optimize prompts or code conversationally:

```
Optimize the agent prompt at './agents/writer.md' using LM Studio
```

Verify the tools are available:

```
opencode mcp list
```

Expected: `specopt_optimize_agent_file`, `specopt_verify_prompt_generalization`, etc.

---

## Mode 2: Agent Brain (Standalone LangChain Agent)

The agent brain (`agent_brain.py`) is a standalone script that runs a LangChain agent loop. It dynamically discovers markdown skill definitions from the `skills/` directory and injects them into the LLM's system prompt. Adding a new `skills/*.md` file automatically makes the agent brain aware of the new capability — no code changes, no config edits, no redeployment.

### How Markdown Skill Discovery Works

At startup, `SkillMDLoader.load_all()` scans `skills/` for `*.md` files, parses the YAML frontmatter and body, and passes them to `_build_system_prompt()`. The resulting system prompt looks like:

```
Available markdown skill definitions:
- prompt_archiver: inputs(source_dir: str, archive_name: str) -> outputs(archive_path: str)
  Archives prompt files from a source directory into a timestamped zip archive.
- surgical_file_modifier: inputs(file_path: str, new_prompt: str, demos: list[dict]) -> outputs(success: bool)
  Surgically modifies markdown text bodies while preserving YAML frontmatter.
- model_connector: inputs(provider: str, model: str) -> outputs(lm_client: dspy.LM)
  Dynamically configures DSPy clients for LM Studio, Ollama, Lemonade.
- dataset_logger: inputs(dataset: list[dspy.Example], output_path: str) -> outputs(result: str)
  Persists generated datasets to disk as JSON files.
```

The LLM can then reason about which skill to use and how to chain multiple skills together.

### Running the Agent Brain

```bash
source venv/bin/activate
pip install -e .                       # registers specopt-server on PATH
python agent_brain.py
```

### Extending with a New Skill (Zero-Code)

To add a new capability that the agent brain can reason about:

1. Create `skills/my_skill.md` with YAML frontmatter (`name`, `inputs`, `outputs`)
2. Add `## Purpose` and `## Behavior` sections describing what it does

The agent brain discovers it automatically on the next run. No Python code required. The corresponding Python implementation can be added later when execution is needed.

### Example

```python
from agent_brain import AgenticOrchestrator
import asyncio

orchestrator = AgenticOrchestrator()
task = (
    "Please optimize our prompt file at './agents/writer.md' using 10 trials via LM Studio. "
    "Immediately after the optimization pass finishes, execute our QA validation tool on the file "
    "to verify if the changes genuinely improved our accuracy parameters on unseen test data."
)
asyncio.run(orchestrator.run_reasoning_loop(task))
```

---

## Configuration

### Providers (`config.yaml`)

Only `lm-studio` is production-ready. The `ollama` and `lemonade` provider configurations and stub classes are pre-defined as templates — implement the real API calls in `core/skills/model_connector.py` to activate them.

```yaml
providers:
  default: "lm-studio"
  lm-studio:
    api_base: "http://localhost:1234/v1"
    api_key: "not-needed"
    default_model: "mistralai/mistral-7b-instruct-v0.3"
  ollama:
    api_base: "http://localhost:11434/v1"
    default_model: "llama3"
  lemonade:
    api_base: "http://localhost:8000/v1"
    default_model: "lemon-model"
```

### Pipeline Parameters
```yaml
pipeline:
  mipro:
    num_trials: 5
    num_candidates: 3
    seed: 9
  dataset:
    num_examples: 15
    chunk_size: 4000
    chunk_overlap: 200
  dataset_validation:
    enabled: true
    alignment_threshold: 80.0
    diversity_threshold: 0.75
    baseline_min: 40.0
    baseline_max: 70.0
    negative_class_min: 15.0
```
## Links
- MIPRO: https://dspy.ai/api/optimizers/MIPROv2/
- GEPA: https://dspy.ai/api/optimizers/GEPA/overview/


## Requirements

- Python ≥ 3.10
- LM Studio running locally at `http://localhost:1234/v1` (required — Ollama and Lemonade stubs need real API client code to activate)
- Dependencies: `mcp`, `langchain-core`, `langchain-openai`, `dspy`, `anyio`, `PyYAML`, `sentence-transformers`, `PyMuPDF`, `pytest`
