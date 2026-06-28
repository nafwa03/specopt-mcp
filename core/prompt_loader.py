import os
import yaml
from typing import Any


class PromptLoader:
    _prompts: dict[str, Any] | None = None
    _base_dir: str | None = None

    @classmethod
    def _resolve_path(cls) -> str:
        if cls._base_dir:
            return os.path.join(cls._base_dir, "prompts.yaml")
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "prompts.yaml")

    @classmethod
    def configure(cls, base_dir: str):
        cls._base_dir = base_dir

    @classmethod
    def load(cls) -> dict[str, Any]:
        if cls._prompts is None:
            path = cls._resolve_path()
            if not os.path.exists(path):
                raise FileNotFoundError(f"prompts.yaml not found at {path}")
            with open(path, "r", encoding="utf-8") as f:
                cls._prompts = yaml.safe_load(f)
        return cls._prompts

    @classmethod
    def get(cls, *keys: str) -> str:
        data = cls.load()
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key)
                if data is None:
                    raise KeyError(f"Key '{key}' not found in prompts.yaml (path: {' -> '.join(keys)})")
            else:
                raise KeyError(f"Cannot traverse further: '{key}' is not a dict (path: {' -> '.join(keys)})")
        return str(data)

    @classmethod
    def clear_cache(cls):
        cls._prompts = None

    @classmethod
    def set_prompts(cls, data: dict):
        cls._prompts = data
