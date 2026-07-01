import os
import re
import sys
import json
import subprocess
import difflib
import logging
from typing import Any, Callable

from core.config_loader import ConfigLoader

try:
    from gepa.optimize_anything import (
        optimize_anything as _oa_optimize_anything,
        log as _oa_log,
        GEPAConfig as _GEPAConfig,
        EngineConfig as _EngineConfig,
        ReflectionConfig as _ReflectionConfig,
        make_litellm_lm as _make_litellm_lm,
    )
    _OA_AVAILABLE = True
except ImportError:
    _OA_AVAILABLE = False
    _oa_optimize_anything = None
    _oa_log = None
    _GEPAConfig = None
    _EngineConfig = None
    _ReflectionConfig = None
    _make_litellm_lm = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Artifact type detection
# ---------------------------------------------------------------------------

ARTIFACT_TYPES = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".py": "python",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".toml": "toml",
    ".cfg": "config",
    ".ini": "config",
    ".txt": "text",
    ".sql": "sql",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "jsx",
    ".tsx": "tsx",
}

REQUIRED_SECTIONS_MARKDOWN = ["Overview", "Rules"]


def detect_artifact_type(path: str, content: str | None = None) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in ARTIFACT_TYPES:
        return ARTIFACT_TYPES[ext]
    if content is not None:
        content_stripped = content.strip()
        if content_stripped.startswith("{"):
            try:
                json.loads(content_stripped)
                return "json"
            except (json.JSONDecodeError, ValueError):
                pass
        if content_stripped.startswith("---"):
            return "yaml"
    return "text"


# ---------------------------------------------------------------------------
# Token estimation (tiktoken with fallback)
# ---------------------------------------------------------------------------

_TOKENIZER = None


def _get_tokenizer():
    global _TOKENIZER
    if _TOKENIZER is None:
        try:
            import tiktoken
            _TOKENIZER = tiktoken.get_encoding("cl100k_base")
        except Exception:
            _TOKENIZER = None
    return _TOKENIZER


def estimate_tokens(text: str) -> int:
    enc = _get_tokenizer()
    if enc is not None:
        return len(enc.encode(text))
    return len(text) // 4


# ---------------------------------------------------------------------------
# Code block extraction
# ---------------------------------------------------------------------------

_CODE_BLOCK_RE = re.compile(r"```(\w+)?\s*\n(.*?)```", re.DOTALL)


def extract_code_blocks(text: str) -> list[dict[str, Any]]:
    blocks = []
    for m in _CODE_BLOCK_RE.finditer(text):
        lang = (m.group(1) or "text").strip().lower()
        code = m.group(2)
        start_line = text[: m.start()].count("\n") + 1
        blocks.append({"language": lang, "code": code, "start_line": start_line})
    return blocks


# ---------------------------------------------------------------------------
# Syntax validation
# ---------------------------------------------------------------------------


def validate_code_syntax(code: str, language: str) -> list[str]:
    errors: list[str] = []
    try:
        if language == "python":
            compile(code, "<candidate>", "exec")
        elif language in ("bash", "sh", "shell", "zsh"):
            result = subprocess.run(
                ["bash", "-n"], input=code, capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                errors.append(result.stderr.strip() or f"bash -n failed (exit {result.returncode})")
        elif language == "json":
            json.loads(code)
        elif language in ("yaml", "yml"):
            try:
                import yaml
                yaml.safe_load(code)
            except ImportError:
                pass
    except SyntaxError as e:
        errors.append(f"{language}: {e}")
    except subprocess.TimeoutExpired:
        errors.append(f"{language}: syntax check timed out")
    except subprocess.CalledProcessError as e:
        errors.append(f"{language}: {e.stderr.strip() or str(e)}")
    except json.JSONDecodeError as e:
        errors.append(f"json: {e}")
    except Exception as e:
        errors.append(f"{language}: {e}")
    return errors


# ---------------------------------------------------------------------------
# Structural checks
# ---------------------------------------------------------------------------


def validate_markdown_structure(text: str, required_sections: list[str] | None = None) -> list[str]:
    issues: list[str] = []
    if required_sections is None:
        required_sections = REQUIRED_SECTIONS_MARKDOWN
    for section in required_sections:
        pattern = re.compile(r"^##\s*" + re.escape(section), re.MULTILINE)
        if not pattern.search(text):
            issues.append(f"Missing required section: '## {section}'")
    heading_levels = re.findall(r"^(#+)\s", text, re.MULTILINE)
    for i in range(1, len(heading_levels)):
        prev = len(heading_levels[i - 1])
        curr = len(heading_levels[i])
        if curr > prev + 1:
            issues.append(f"Heading jump: {heading_levels[i-1]} -> {heading_levels[i]}")
    return issues


def validate_python_structure(text: str) -> list[str]:
    issues: list[str] = []
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.rstrip()
        if line != stripped:
            issues.append(f"Trailing whitespace at line {i}")
        if "\t" in line:
            issues.append(f"Tab character at line {i} (use spaces)")
    return issues


def validate_generic_structure(text: str) -> list[str]:
    issues: list[str] = []
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.rstrip()
        if line != stripped:
            issues.append(f"Trailing whitespace at line {i}")
    trailing_newlines = len(text) - len(text.rstrip("\n"))
    if trailing_newlines > 2:
        issues.append(f"Excessive trailing newlines ({trailing_newlines})")
    return issues


# ---------------------------------------------------------------------------
# Regression / drift detection
# ---------------------------------------------------------------------------


def compute_regressions(original: str, candidate: str) -> list[dict[str, Any]]:
    regressions: list[dict[str, Any]] = []
    if original == candidate:
        return regressions
    orig_lines = original.splitlines()
    cand_lines = candidate.splitlines()
    differ = difflib.SequenceMatcher(None, orig_lines, cand_lines)
    for op, i1, i2, j1, j2 in differ.get_opcodes():
        if op == "replace":
            for o, c in zip(orig_lines[i1:i2], cand_lines[j1:j2]):
                regressions.append({
                    "type": "line_changed",
                    "before": o,
                    "after": c,
                })
        elif op == "delete":
            for o in orig_lines[i1:i2]:
                regressions.append({
                    "type": "line_removed",
                    "before": o,
                    "after": None,
                })
    return regressions


# ---------------------------------------------------------------------------
# Format adherence
# ---------------------------------------------------------------------------


def check_format_adherence(text: str) -> list[str]:
    issues: list[str] = []
    lines = text.splitlines()
    trailing_count = sum(1 for l in lines if l != l.rstrip())
    if trailing_count:
        issues.append(f"{trailing_count} line(s) with trailing whitespace")
    if not text.endswith("\n"):
        issues.append("File does not end with a newline")
    return issues


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------


def compute_composite_score(
    conciseness: dict[str, Any],
    syntax_errors: list[dict[str, Any]],
    structural_issues: list[str],
    regressions: list[dict[str, Any]],
    format_issues: list[str],
    weights: dict[str, float] | None = None,
) -> float:
    if weights is None:
        weights = {"conciseness": 0.30, "syntax": 0.35, "structure": 0.30, "regression": 0.05}
    raw = 1.0
    raw -= weights["conciseness"] * (1.0 - conciseness.get("score", 1.0))
    raw -= weights["syntax"] * min(1.0, len(syntax_errors) * 0.3)
    raw -= weights["structure"] * min(1.0, len(structural_issues) * 0.25)
    raw -= weights["regression"] * min(1.0, len(regressions) * 0.15)
    if format_issues:
        raw -= 0.05 * min(1.0, len(format_issues) * 0.5)
    return max(0.0, min(1.0, raw))


# ---------------------------------------------------------------------------
# Evaluator factory
# ---------------------------------------------------------------------------


def make_universal_evaluator(
    artifact_type: str,
    original_content: str,
    reference_content: str | None = None,
    max_lines: int = 150,
    max_tokens: int = 4000,
    required_sections: list[str] | None = None,
    weights: dict[str, float] | None = None,
) -> Callable:
    ref = reference_content if reference_content is not None else original_content

    def evaluator(candidate: str, example: Any = None) -> tuple[float, dict]:
        cand_type = type(candidate).__name__
        cand_len = len(candidate) if isinstance(candidate, str) else 'N/A'
        cand_preview = str(candidate)[:200] if isinstance(candidate, str) else str(candidate)[:200]
        ex_type = type(example).__name__ if example is not None else 'None'
        ex_val = str(example)[:200] if example else 'None'
        with open("gepa_debug.log", "a") as _df:
            _df.write(f"candidate: type={cand_type} len={cand_len} first_200={cand_preview!r}\n")
            _df.write(f"example: type={ex_type} val={ex_val!r}\n")
        asi: dict[str, Any] = {}

        # 1. Conciseness
        lines = candidate.splitlines()
        line_count = len(lines)
        token_count = estimate_tokens(candidate)
        line_ratio = min(1.0, line_count / max_lines) if max_lines else 1.0
        token_ratio = min(1.0, token_count / max_tokens) if max_tokens else 1.0
        conciseness_score = 1.0 - 0.5 * (line_ratio + token_ratio) / 2.0
        conciseness_info = {
            "lines": line_count,
            "tokens": token_count,
            "max_lines": max_lines,
            "max_tokens": max_tokens,
            "score": max(0.0, conciseness_score),
        }
        asi["Conciseness"] = conciseness_info

        # 2. Syntax validation
        syntax_errors: list[dict[str, Any]] = []
        blocks = extract_code_blocks(candidate)
        for block in blocks:
            if block["language"] in ("python", "bash", "sh", "shell", "json", "yaml", "yml"):
                errs = validate_code_syntax(block["code"], block["language"])
                for err in errs:
                    syntax_errors.append({
                        "language": block["language"],
                        "line": block["start_line"],
                        "error": err,
                    })

        if artifact_type == "python":
            errs = validate_code_syntax(candidate, "python")
            for err in errs:
                syntax_errors.append({"language": "python", "line": 1, "error": err})
        elif artifact_type == "json":
            errs = validate_code_syntax(candidate, "json")
            for err in errs:
                syntax_errors.append({"language": "json", "line": 1, "error": err})
        asi["SyntaxErrors"] = syntax_errors

        # 3. Structural integrity
        structural_issues: list[str] = []
        if artifact_type == "markdown":
            structural_issues = validate_markdown_structure(candidate, required_sections)
        elif artifact_type == "python":
            structural_issues = validate_python_structure(candidate)
        else:
            structural_issues = validate_generic_structure(candidate)
        asi["StructuralIssues"] = structural_issues

        # 4. Regression / drift
        regressions = compute_regressions(ref, candidate)
        asi["Regressions"] = regressions

        # 5. Format adherence
        format_issues = check_format_adherence(candidate)
        asi["FormatIssues"] = format_issues

        score = compute_composite_score(
            conciseness_info, syntax_errors, structural_issues, regressions, format_issues, weights
        )
        asi["score"] = score
        with open("gepa_debug.log", "a") as _df:
            _df.write(f"score={score:.4f} conciseness={conciseness_info['score']:.2f} "
                      f"syntax_errs={len(syntax_errors)} struct_issues={len(structural_issues)} "
                      f"regressions={len(regressions)} format_issues={len(format_issues)}\n")

        return score, asi

    return evaluator


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def run_optimize_anything_pipeline(
    artifact_path: str,
    objective: str = "",
    background: str = "",
    reference_path: str | None = None,
    max_metric_calls: int = 50,
    evaluator_type: str | None = None,
    dataset_paths: list[str] | None = None,
    config_override: dict | None = None,
    lm_client=None,
) -> str:
    logger.info("optimize_anything pipeline start: %s", artifact_path)

    if not os.path.exists(artifact_path):
        return f"Error: Target file not found at path: {artifact_path}"

    with open(artifact_path, "r", encoding="utf-8") as f:
        original_content = f.read()

    if reference_path and os.path.exists(reference_path):
        with open(reference_path, "r", encoding="utf-8") as f:
            reference_content = f.read()
    else:
        reference_content = original_content

    if not evaluator_type:
        evaluator_type = detect_artifact_type(artifact_path, original_content)

    logger.info("Detected artifact type: %s", evaluator_type)

    scoring_cfg = ConfigLoader.get("pipeline", "optimize_anything", "scoring")
    weights = {
        "conciseness": scoring_cfg.get("conciseness_weight", 0.30),
        "syntax": scoring_cfg.get("syntax_weight", 0.35),
        "structure": scoring_cfg.get("structure_weight", 0.30),
        "regression": scoring_cfg.get("regression_weight", 0.05),
    }

    evaluator = make_universal_evaluator(
        artifact_type=evaluator_type,
        original_content=original_content,
        reference_content=reference_content,
        weights=weights,
    )

    # Dataset for reflection LM (always provide at least the source artifact)
    dataset = [{"path": artifact_path, "content": original_content}]
    if dataset_paths:
        dataset = []
        for dp in dataset_paths:
            if os.path.exists(dp):
                with open(dp, "r", encoding="utf-8") as f:
                    dataset.append({"path": dp, "content": f.read()})

    # Build config
    cfg_overrides = config_override or {}
    gepa_config = _build_gepa_config(max_metric_calls, cfg_overrides, lm_client)

    if not _OA_AVAILABLE or _oa_optimize_anything is None:
        msg = "gepa package not installed. Run: ./install.sh (Linux) or .\\install.ps1 (Windows)"
        logger.error(msg)
        return f"Error: {msg}"

    result = _oa_optimize_anything(
        seed_candidate=original_content,
        evaluator=evaluator,
        dataset=dataset,
        objective=objective or f"Optimize {os.path.basename(artifact_path)}",
        background=background,
        config=gepa_config,
    )

    # Debug: dump result shape
    with open("gepa_debug.log", "a") as _df:
        _df.write(f"RESULT dir={[a for a in dir(result) if not a.startswith('_')]}\n")
        _df.write(f"RESULT candidates_count={len(result.candidates)}\n")
        _df.write(f"RESULT val_aggregate_scores={result.val_aggregate_scores}\n")
        _df.write(f"RESULT total_metric_calls={result.total_metric_calls}\n")

    best_candidate = result.best_candidate
    best_score = max(result.val_aggregate_scores) if result.val_aggregate_scores else 0.0
    total_calls = result.total_metric_calls or 0

    # Write backup
    bak_path = artifact_path + ".bak"
    if not os.path.exists(bak_path):
        with open(bak_path, "w", encoding="utf-8") as f:
            f.write(original_content)

    # Write optimized content
    with open(artifact_path, "w", encoding="utf-8") as f:
        f.write(best_candidate)

    score_delta = best_score - _score_original(evaluator, original_content)

    summary_lines = [
        f"### optimize_anything — Optimization Complete",
        f"**File**: {artifact_path}",
        f"**Type**: {evaluator_type}",
        f"**Mode**: {'multi-task' if dataset else 'single-task'}",
        f"**Best Score**: {best_score:.4f} (Δ: {score_delta:+.4f})",
        f"**Metric Calls**: {total_calls}",
        f"**Backup**: {bak_path}",
    ]

    if dataset:
        summary_lines.append(f"**Dataset Files**: {len(dataset)}")

    logger.info("optimize_anything pipeline complete: score=%.4f calls=%d", best_score, total_calls)
    return "\n".join(summary_lines)


def _score_original(evaluator: Callable, content: str) -> float:
    try:
        score, _ = evaluator(content)
        return float(score)
    except Exception:
        return 0.0


def _build_gepa_config(
    max_metric_calls: int,
    overrides: dict,
    lm_client=None,
) -> Any:
    if not _OA_AVAILABLE:
        return None

    engine_cfg = _EngineConfig(
        max_metric_calls=overrides.get("max_metric_calls", max_metric_calls),
    )

    # Build a proper LanguageModel callable via make_litellm_lm
    # so gepa receives a bare str, not list[str] from our LMStudioLM wrapper.
    # api_base/api_key are passed via env vars for litellm compatibility.
    if lm_client and _make_litellm_lm:
        api_base = getattr(lm_client, "api_base", "")
        api_key = getattr(lm_client, "api_key", "lm-studio")
        model_name = getattr(lm_client, "model", "not-needed")
        os.environ.setdefault("OPENAI_API_BASE", api_base)
        os.environ.setdefault("OPENAI_API_KEY", api_key)
        reflection_lm = _make_litellm_lm(model_name=f"openai/{model_name}")
    else:
        reflection_lm = lm_client

    reflection_cfg = _ReflectionConfig(
        reflection_minibatch_size=overrides.get("reflection_minibatch_size", 3),
        reflection_lm=reflection_lm,
    )
    return _GEPAConfig(
        engine=engine_cfg,
        reflection=reflection_cfg,
    )
