import json
import dspy
from typing import Optional, List


class MockLM(dspy.BaseLM):
    """Deterministic LM that returns JSON responses matching DSPy output field names.

    ChatAdapter tries FieldName: value format first, then falls back to JSONAdapter
    which parses JSON objects with output field keys. This MockLM returns JSON
    so JSONAdapter can parse it successfully.
    """

    def __init__(self, model: str = "mock-model", mode: str = "pass"):
        self.model = model
        self.mode = mode
        self.call_count = 0
        self.history: List[str] = []
        super().__init__(model=model)

    def __call__(
        self, prompt: Optional[str] = None,
        messages: Optional[list] = None, **kwargs
    ) -> List[str]:
        self.call_count += 1
        prompt_text = prompt or ""
        if messages:
            last = messages[-1] if messages else {}
            prompt_text = last.get("content", str(messages))
        prompt_lower = prompt_text.lower()
        self.history.append(prompt_text[:200])

        if "json_dataset" in prompt_lower or "generate a json array" in prompt_lower:
            dataset = json.dumps([
                {"input_context": "Write a short poem.",
                 "gold_response": "Roses are red."}
            ])
            return [json.dumps({"json_dataset": dataset})]

        if "injection_vulnerability" in prompt_lower:
            return [json.dumps({"injection_vulnerability_detected": "NO"})]

        if "contains_false_information" in prompt_lower:
            return [json.dumps({"contains_false_information": "NO"})]

        if "verdict" in prompt_lower and "input_context" in prompt_lower:
            if self.mode == "overfit" and self.call_count > 3:
                return [json.dumps({"verdict": "NO"})]
            return [json.dumps({"verdict": "YES"})]

        if "output_response" in prompt_lower:
            return [json.dumps({"output_response": f"Mock output #{self.call_count}"})]

        if "optimized_section" in prompt_lower:
            return [json.dumps({"optimized_section": "Mock optimized section content."})]

        if "quality_score" in prompt_lower:
            return [json.dumps({"quality_score": 50})]

        if "optimized_python_code" in prompt_lower:
            return [json.dumps({"optimized_python_code": "def foo(): pass"})]

        if "optimized_description" in prompt_lower:
            return [json.dumps({"optimized_description": "Mock optimized description."})]

        return [json.dumps({"output_response": f"Default mock #{self.call_count}"})]

    def copy(self, **kwargs):
        return MockLM(
            model=kwargs.get("model", self.model),
            mode=self.mode,
        )
