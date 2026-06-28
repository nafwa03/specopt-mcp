import os
from typing import Any, List, Dict
from core.base_skill import BaseSkill
from core.prompt_loader import PromptLoader


class DirectoryScannerSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "directory_scanner"

    @property
    def description(self) -> str:
        return PromptLoader.get("skills", "DirectoryScannerSkill")

    def execute(self, **kwargs: Any) -> Dict[str, List[str]]:
        dir_path: str = kwargs.get("directory_path", "").strip()

        if not os.path.exists(dir_path):
            raise FileNotFoundError(f"Target directory path not found: {dir_path}")
        if not os.path.isdir(dir_path):
            raise ValueError(f"Provided path is a file, not a directory: {dir_path}")

        manifest = {
            "python_files": [],
            "markdown_files": []
        }

        # Standard industry exclusion patterns to prevent tracking garbage files
        ignored_tokens = ["__pycache__", ".git", ".pytest_cache", "venv", ".venv", "env"]

        print(f"[Scanner] Scanning workspace directory tree: '{dir_path}'...")

        # Walk through the directory tree recursively
        for root, dirs, files in os.walk(dir_path):
            # Modify dirs in-place to skip ignored directories entirely
            dirs[:] = [d for d in dirs if d not in ignored_tokens]

            for file in files:
                file_path = os.path.join(root, file)

                if file.endswith(".py") and not file.startswith("__"):
                    manifest["python_files"].append(file_path)
                elif file.endswith(".md") or file.endswith(".markdown"):
                    manifest["markdown_files"].append(file_path)

        print(
            f"[Scanner Report] Found {len(manifest['python_files'])} Python file(s) and {len(manifest['markdown_files'])} Markdown file(s).")