import asyncio
import os
import sys
import argparse
from core.skills import SkillRegistry
from core.skills.verifier import VerificationSkill


def resolve_paths(path: str):
    """Auto-detect the optimized variant and original file."""
    candidate = path
    original_path = ""

    # If the given path is the original, look for _optimized variant
    base, ext = os.path.splitext(path)
    optimized_variant = f"{base}_optimized{ext}"

    if path.endswith("_optimized.md") or path.endswith("_optimized.json"):
        # Already pointing at optimized output
        candidate = path
        original_path = base.rsplit("_optimized", 1)[0] + ext
        if not os.path.exists(original_path):
            original_path = ""
    elif os.path.exists(optimized_variant):
        # Original given, optimized variant exists — use it
        candidate = optimized_variant
        original_path = path

    # Also check for .bak
    if not original_path:
        bak_path = path + ".bak"
        if os.path.exists(bak_path):
            original_path = bak_path

    return candidate, original_path


async def run_independent_verification(agent_markdown_path: str, provider: str = "lm-studio",
                                       model: str = "", original_path: str = ""):
    registry = SkillRegistry()
    connection_skill = registry.get_skill("model_connector")
    lm_client = connection_skill.execute(provider=provider, model=model)

    test_set_path = os.path.splitext(agent_markdown_path)[0] + "_generated_dataset.json"
    if not os.path.exists(test_set_path):
        test_set_path = ""

    verifier = VerificationSkill()
    result = verifier.execute(
        agent_markdown_path=agent_markdown_path,
        original_markdown_path=original_path,
        test_set_path=test_set_path,
        lm_client=lm_client,
    )

    baseline_src = result.get("baseline_source", "default")
    print(f"\nBaseline Source: {baseline_src}")
    print(f"Optimized File: {agent_markdown_path}")
    print(f"Baseline Score: {result['baseline_score']:.1f}%")
    print(f"Optimized Score: {result['optimized_score']:.1f}%")
    print(f"Delta: {result['generalization_delta']:+.1f}%")
    print(f"Verdict: {result['verdict']}")
    print(f"Detail: {result['detail']}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify prompt optimization results")
    parser.add_argument("path", nargs="?", default="agents/writer.md",
                        help="Path to the file to verify (auto-detects _optimized and .bak)")
    parser.add_argument("--provider", default="lm-studio", help="LLM provider")
    parser.add_argument("--model", default="", help="Model name")
    parser.add_argument("--original", default="",
                        help="Explicit path to original file (overrides auto-detect)")
    args = parser.parse_args()

    target, auto_original = resolve_paths(args.path)
    original = args.original or auto_original

    print(f"Resolved target: {target}")
    if original:
        print(f"Original/baseline: {original}")
    else:
        print("No original file found — using hardcoded default baseline.")

    asyncio.run(run_independent_verification(
        target, args.provider, args.model, original
    ))
