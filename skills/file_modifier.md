---
name: surgical_file_modifier
inputs:
  - file_path: str
  - new_prompt: str
  - demos: list[dict]
outputs:
  - success: bool
model: any
temperature: 0.0
---

## Purpose
Surgically modifies markdown text bodies while preserving YAML frontmatter configuration. Outputs to a separate `_optimized` file to keep the original intact.

## Behavior
1. Reads the target markdown file.
2. Extracts and preserves any YAML frontmatter (between `---` delimiters).
3. Replaces the body with the new prompt text.
4. Optionally appends few-shot demonstration examples under an "Optimized Agent Skills & Demos" section.
5. Writes the result to `<original>_optimized.md`.

## Example
```python
skill = SurgicalFileModifierSkill()
skill.execute(file_path="./agents/writer.md", new_prompt="You are a poet.", demos=[])
# Writes ./agents/writer_optimized.md
```
