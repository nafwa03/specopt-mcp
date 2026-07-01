"""
Standalone demo: Run the optimize_anything evaluator on the verbose skill file.

This shows the ASI (Actionable Side Information) that drives the optimizer.
The evaluator runs in about 1 second with zero external dependencies (no LLM calls).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.optimize_anything_adapter import (
    make_universal_evaluator,
    detect_artifact_type,
    estimate_tokens,
)

DEMO_FILE = os.path.join(os.path.dirname(__file__), "verbose_skill.md")

with open(DEMO_FILE) as f:
    content = f.read()

artifact_type = detect_artifact_type(DEMO_FILE, content)
print(f"Artifact: {DEMO_FILE}")
print(f"Type: {artifact_type}")
print(f"Lines: {len(content.splitlines())}")
print(f"Tokens (est): {estimate_tokens(content)}")
print(f"Has ## Overview: {'## Overview' in content}")
print()

evaluator = make_universal_evaluator(
    artifact_type=artifact_type,
    original_content=content,
)

score, asi = evaluator(content)

print(f"=== Optimize Anything Evaluator ===")
print(f"Composite Score: {score:.4f}  (1.0 = perfect, 0.0 = worst)")
print()

print("--- Conciseness ---")
c = asi["Conciseness"]
print(f"  Lines: {c['lines']} (max {c['max_lines']})")
print(f"  Tokens: {c['tokens']} (max {c['max_tokens']})")
print(f"  Score: {c['score']:.4f}")
print()

print("--- Syntax Errors ---")
if asi["SyntaxErrors"]:
    for e in asi["SyntaxErrors"]:
        print(f"  [{e['language']}] line {e['line']}: {e['error']}")
else:
    print("  None found")
print()

print("--- Structural Issues ---")
if asi["StructuralIssues"]:
    for s in asi["StructuralIssues"]:
        print(f"  - {s}")
else:
    print("  None found")
print()

print("--- Format Issues ---")
if asi["FormatIssues"]:
    for f in asi["FormatIssues"]:
        print(f"  - {f}")
else:
    print("  None found")
print()

print("--- Regressions (vs original) ---")
if asi["Regressions"]:
    for r in asi["Regressions"][:5]:
        print(f"  [{r['type']}] before: {r['before'][:60]}")
    if len(asi["Regressions"]) > 5:
        print(f"  ... and {len(asi['Regressions']) - 5} more")
else:
    print("  None (file is identical to reference)")
print()

print(f"{'='*50}")
print(f"These diagnostics would be fed as ASI to the LLM proposer")
print(f"via oa.log() calls. The proposer would then propose targeted")
print(f"improvements to raise the score toward 1.0.")
