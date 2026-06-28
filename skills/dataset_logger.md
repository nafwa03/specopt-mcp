---
name: dataset_logger
inputs:
  - dataset: list[dspy.Example]
  - output_path: str
outputs:
  - result: str
model: any
temperature: 0.0
---

## Purpose
Intercepts generated datasets during pipeline execution and persists them to disk as JSON files for audit trail, debugging, and reuse in verification pipelines.

## Behavior
1. Receives a list of dspy.Example objects and an output file path.
2. Serializes each example to a dict with example_id, input_context, and gold_response.
3. Creates parent directories if they don't exist.
4. Writes the JSON array to disk.
5. Returns a confirmation string.

## Example
```python
skill = DatasetLoggingSkill()
skill.execute(dataset=examples, output_path="./agents/dataset.json")
# Saved 15 examples to ./agents/dataset.json
```
