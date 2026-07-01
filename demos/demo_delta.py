"""
Demo Part 2: Show the score delta after hypothetical improvements.
This simulates what the optimizer would produce: a condensed, fixed file.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.optimize_anything_adapter import make_universal_evaluator, detect_artifact_type

DEMO_FILE = os.path.join(os.path.dirname(__file__), "verbose_skill.md")

with open(DEMO_FILE) as f:
    original = f.read()

# Simulate a realistic intermediate candidate the optimizer might propose.
# This keeps most of the original structure but fixes the specific issues
# the evaluator flagged.
fixed = original

# Add ## Overview section right after the title
fixed = fixed.replace(
    "## What This Skill Does\n\n",
    "## Overview\n"
    "AI agent skill for reviewing pull requests. Flags style, security, performance,\n"
    "and testing issues before merge. Designed to be comprehensive yet practical.\n"
    "\n"
    "## What This Skill Does\n\n",
    1,
)

# Remove excess paragraph from "What This Skill Does" (the third paragraph)
fixed = fixed.replace(
    "The skill described in this document is designed to be comprehensive yet practical. It covers the\n"
    "most common categories of issues found in code reviews: style and formatting, error handling, security,\n"
    "performance, and testing. Each category has a detailed set of rules that the agent should apply when\n"
    "reviewing code. The rules are designed to be specific enough to catch real issues but flexible enough\n"
    "to avoid false positives in cases where the code intentionally deviates from best practices.\n\n",
    "",
    1,
)

# Remove excess paragraph from "How To Use" (the intro paragraph)
fixed = fixed.replace(
    "Following these steps\nwill ensure that your review is thorough, consistent, and useful to the developer who submitted the\n"
    "pull request. Each step builds on the previous one, so it is important to complete them in order.\n\n",
    "",
    1,
)

# Remove excess intro to Rules section
fixed = fixed.replace(
    "\n"
    "The rules below define the specific checks that the agent should perform when reviewing code.\n"
    "These rules are organized by category so that related checks are grouped together. The agent should\n"
    "go through each category in order and check each rule against every file in the pull request. If a\n"
    "file does not contain any code relevant to a particular category (e.g., a Python file for CSS rules),\n"
    "the agent should skip that category for that file. The categories are ordered by importance, with the\n"
    "most impactful categories first.\n"
    "\n"
    "It is important to note that these rules are guidelines, not hard requirements. There may be cases\n"
    "where the code intentionally violates a rule for a good reason (e.g., using a bare except clause\n"
    "in a specific situation where all exceptions need to be caught and logged). In these cases, the\n"
    "agent should evaluate whether the exception is justified and either flag it with lower severity or\n"
    "ask a clarifying question. The goal is to be helpful, not pedantic.\n\n",
    "\n",
    1,
)

# Strip trailing whitespace from all lines
fixed = "\n".join(line.rstrip() for line in fixed.splitlines()) + "\n"

artifact_type = detect_artifact_type(DEMO_FILE, original)
evaluator = make_universal_evaluator(
    artifact_type=artifact_type,
    original_content=original,
)

orig_score, orig_asi = evaluator(original)
fixed_score, fixed_asi = evaluator(fixed)

def _sub_score(asi, category, weight):
    """Extract the penalty contribution for a category."""
    if category == "conciseness":
        return weight * (1.0 - asi["Conciseness"]["score"])
    if category == "syntax":
        return weight * min(1.0, len(asi["SyntaxErrors"]) * 0.3)
    if category == "structure":
        return weight * min(1.0, len(asi["StructuralIssues"]) * 0.25)
    if category == "regression":
        return weight * min(1.0, len(asi["Regressions"]) * 0.15)
    if category == "format":
        return 0.05 * min(1.0, len(asi["FormatIssues"]) * 0.5)
    return 0.0

print(f"{'='*60}")
print(f"  optimize_anything — Score Delta Demo")
print(f"{'='*60}")
print()
print(f"  {'Category':<16} {'Score Weight':>6} {'Before Penalty':>10} {'After Penalty':>10} {'Δ Penalty':>10}")
print(f"  {'-'*16:16} {'-'*12:>6} {'-'*14:>10} {'-'*13:>10} {'-'*9:>10}")
for cat, weight_str, w in [("Conciseness","0.20",0.20),("Syntax","0.35",0.35),("Structure","0.25",0.25),("Regression","0.20",0.20),("Format","0.05",0.05)]:
    bp = _sub_score(orig_asi, cat.lower(), w)
    ap = _sub_score(fixed_asi, cat.lower(), w)
    print(f"  {cat:<16} {weight_str:>6} {bp:>10.4f} {ap:>10.4f} {ap - bp:>+10.4f}")
print(f"  {'-'*60}")
print(f"  {'Composite Score':<34} {orig_score:>10.4f} {fixed_score:>10.4f} {fixed_score - orig_score:>+10.4f}")
print()
print(f"  Details:")
print(f"    Lines:        {orig_asi['Conciseness']['lines']:>3} → {fixed_asi['Conciseness']['lines']:<3}")
print(f"    ## Overview:  {'Missing' if orig_asi['StructuralIssues'] else 'Present':>8} → {'Missing' if fixed_asi['StructuralIssues'] else 'Present'}")
print(f"    Trailing ws:  {orig_asi['FormatIssues']!s:>14} → {fixed_asi['FormatIssues']!s}")
print(f"    Regressions:  {len(orig_asi['Regressions']):>3} → {len(fixed_asi['Regressions'])} (line diffs from edits)")
print()
print(f"  The optimizers LLM proposer receives ASI after each candidate")
print(f"  evaluation. It sees: structure and format improved, but every")
print(f"  text edit creates regressions. The proposer learns to make")
print(f"  targeted edits that minimize regressions while fixing issues.")
print()
print(f"  After several iterations, the proposer converges on a version")
print(f"  with ## Overview, no trailing whitespace, and minimal regressions.")
print(f"  This is the Pareto-efficient search in action.")
