import os
import re
import json
import logging
from typing import Any, Dict, List, Optional
import dspy
from dspy.evaluate import Evaluate
from core.base_skill import BaseSkill
from core.prompt_loader import PromptLoader
from core.optimizer import (
    DynamicAgentSignature,
    secure_universal_llm_metric,
    extract_and_load_dataset,
    generate_dataset_via_lm,
)

logger = logging.getLogger(__name__)


def _strip_prompt(content: str) -> str:
    body = content
    frontmatter_match = re.match(r"^(---\s*\n[\s\S]*?\n---\s*\n)", content)
    if frontmatter_match:
        body = content[len(frontmatter_match.group(1)):]
    body = re.sub(r"## Optimized Agent Skills & Demos[\s\S]*", "", body)
    return body.strip()


class VerificationSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "prompt_verifier"

    @property
    def description(self) -> str:
        return PromptLoader.get("skills", "VerificationSkill")

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        agent_markdown_path: str = kwargs.get("agent_markdown_path", "")
        lm_client: dspy.LM = kwargs.get("lm_client")

        original_markdown_path: str = kwargs.get("original_markdown_path", "")
        if original_markdown_path and os.path.exists(original_markdown_path):
            with open(original_markdown_path, "r", encoding="utf-8") as f:
                raw = f.read()
            baseline_instructions = _strip_prompt(raw)
            baseline_source = original_markdown_path
        else:
            baseline_instructions = kwargs.get(
                "baseline_instructions",
                PromptLoader.get("defaults", "baseline_instructions")
            )
            baseline_source = "hardcoded default"

        test_set_path: str = kwargs.get("test_set_path", "")

        if not os.path.exists(agent_markdown_path):
            raise FileNotFoundError(
                f"Target file not found at path: {agent_markdown_path}"
            )

        with open(agent_markdown_path, "r", encoding="utf-8") as f:
            full_content = f.read()

        optimized_instructions = _strip_prompt(full_content)

        logger.info(
            "Baseline source: %s | Optimized source: %s",
            baseline_source, agent_markdown_path
        )

        with dspy.context(lm=lm_client):
            if test_set_path and os.path.exists(test_set_path):
                with open(test_set_path, "r") as f:
                    test_set_data = json.load(f)
                test_set = [
                    dspy.Example(**item).with_inputs("input_context")
                    for item in test_set_data
                ]
                logger.info("Reusing shared test set from %s (%d examples)", test_set_path, len(test_set))
            else:
                test_set = generate_dataset_via_lm(
                    lm_client=lm_client,
                    agent_prompt=optimized_instructions,
                    num_examples=5,
                )

            baseline_signature = DynamicAgentSignature.with_instructions(baseline_instructions)
            baseline_program = dspy.Predict(baseline_signature)

            evaluator = Evaluate(
                devset=test_set,
                metric=secure_universal_llm_metric,
                display_progress=False
            )

            raw_baseline = evaluator(baseline_program)
            true_baseline_score = (
                float(raw_baseline)
                if not isinstance(raw_baseline, dict)
                else float(raw_baseline.get("score", 0))
            )

            optimized_signature = DynamicAgentSignature.with_instructions(optimized_instructions)
            optimized_program = dspy.Predict(optimized_signature)

            raw_optimized = evaluator(optimized_program)
            true_optimized_score = (
                float(raw_optimized)
                if not isinstance(raw_optimized, dict)
                else float(raw_optimized.get("score", 0))
            )

        base_pct = (
            true_baseline_score
            if true_baseline_score > 1.0
            else true_baseline_score * 100
        )
        opt_pct = (
            true_optimized_score
            if true_optimized_score > 1.0
            else true_optimized_score * 100
        )
        generalization_delta = opt_pct - base_pct

        if generalization_delta > 0:
            verdict = "PASS"
            detail = (
                f"Prompt optimization achieved a TRUE improvement of "
                f"+{generalization_delta:.1f}% on unseen scenarios."
            )
        elif generalization_delta == 0:
            verdict = "NEUTRAL"
            detail = (
                "The optimized prompt matched the original baseline "
                "score perfectly on unseen scenarios."
            )
        else:
            verdict = "OVERFIT"
            detail = (
                f"OVERFITTING DETECTED: The optimized prompt dropped "
                f"performance by {abs(generalization_delta):.1f}% on new data."
            )

        return {
            "baseline_score": base_pct,
            "optimized_score": opt_pct,
            "generalization_delta": generalization_delta,
            "verdict": verdict,
            "detail": detail,
            "test_set_size": len(test_set),
            "baseline_source": baseline_source,
        }
