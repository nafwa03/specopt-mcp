import os
import json
from typing import Any, List
import dspy
from core.base_skill import BaseSkill
from core.prompt_loader import PromptLoader


class DatasetLoggingSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "dataset_logger"

    @property
    def description(self) -> str:
        return PromptLoader.get("skills", "DatasetLoggingSkill")

    def execute(self, **kwargs: Any) -> str:
        dataset: List[dspy.Example] = kwargs.get("dataset", [])
        output_path: str = kwargs.get("output_path", "generated_dataset.json")

        if not dataset:
            print("[Dataset Logger] Received an empty dataset. Skipping file dump.")
            return "Skipped: Empty dataset."

        serializable_data = []
        for i, example in enumerate(dataset):
            serializable_data.append({
                "example_id": i + 1,
                "input_context": getattr(example, "input_context", ""),
                "gold_response": getattr(example, "output_response", getattr(example, "gold_response", ""))
            })

        directory = os.path.dirname(output_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(serializable_data, f, indent=2)

        print(f"[Dataset Logger] Captured {len(dataset)} examples. Ground-truth audited at: {output_path}")
        return f"Successfully saved dataset to {output_path}"
