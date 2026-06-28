import os
import yaml
from typing import Any


class ConfigLoader:
    _config: dict[str, Any] | None = None
    _base_dir: str | None = None

    @classmethod
    def _resolve_path(cls) -> str:
        if cls._base_dir:
            return os.path.join(cls._base_dir, "config.yaml")
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.yaml")

    @classmethod
    def configure(cls, base_dir: str):
        cls._base_dir = base_dir

    @classmethod
    def load(cls) -> dict[str, Any]:
        if cls._config is None:
            path = cls._resolve_path()
            if not os.path.exists(path):
                raise FileNotFoundError(f"config.yaml not found at {path}")
            with open(path, "r", encoding="utf-8") as f:
                cls._config = yaml.safe_load(f)
        return cls._config

    @classmethod
    def get(cls, *keys: str) -> Any:
        data = cls.load()
        for key in keys:
            if isinstance(data, dict):
                if key not in data:
                    raise KeyError(f"Key '{key}' not found in config.yaml (path: {' -> '.join(keys)})")
                data = data[key]
            else:
                raise KeyError(f"Cannot traverse further: '{key}' is not a dict (path: {' -> '.join(keys)})")
        return data

    @classmethod
    def clear_cache(cls):
        cls._config = None

    @classmethod
    def set_config(cls, data: dict):
        cls._config = data
