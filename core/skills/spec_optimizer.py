import os
import json
from typing import Any, Dict, Callable
from core.base_skill import BaseSkill
from core.prompt_loader import PromptLoader
from core.config_loader import ConfigLoader


class SpecStructuralIsolationSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "spec_structural_isolation"

    @property
    def description(self) -> str:
        return PromptLoader.get("skills", "SpecStructuralIsolationSkill")

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        file_path: str = kwargs.get("file_path", "")
        optimize_fn: Callable[[str], str] = kwargs.get("optimize_callback")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Target specification file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            spec_data = json.load(f)

        def walk_and_optimize(node: Any) -> Any:
            if isinstance(node, dict):
                new_dict = {}
                for key, value in node.items():
                    if key in ["description", "summary", "title"] and isinstance(value, str) and value.strip():
                        print(f"   [Optimizer Worker] Refining field [{key}]...")
                        new_dict[key] = optimize_fn(value)
                    else:
                        new_dict[key] = walk_and_optimize(value)
                return new_dict
            elif isinstance(node, list):
                return [walk_and_optimize(item) for item in node]
            return node

        print(f"\n[Schema Lock] Commencing structural separation walker on {file_path}...")
        optimized_spec = walk_and_optimize(spec_data)

        print("[Guard Pass] Initiating structural round-trip serialization audit...")
        try:
            serialized_text = json.dumps(optimized_spec, indent=2)
            validated_json_structure = json.loads(serialized_text)
            if not isinstance(validated_json_structure, dict) and not isinstance(validated_json_structure, list):
                raise ValueError("Payload parsed successfully but root object structure is invalid.")
            print("[Success] Validation complete. JSON structure contains zero syntactic errors.")
        except (json.JSONDecodeError, TypeError, ValueError) as json_error:
            print(f"[CRITICAL ABORT] Syntactic validation failed! Error detail: {str(json_error)}")
            raise RuntimeError(
                f"Validation Failure: The optimized data tree corrupted structural compliance schemas. "
                f"File write operation killed defensively. Details: {str(json_error)}"
            )

        base, ext = os.path.splitext(file_path)
        optimized_file_path = f"{base}{ConfigLoader.get("file_suffixes", "optimized")}{ext}"
        
        with open(optimized_file_path, "w", encoding="utf-8") as f:
            f.write(serialized_text)

        print(f"[Saved] Validation pass logged. File safely written to: {optimized_file_path}")
        return optimized_spec
