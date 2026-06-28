import re
import os
from typing import Any, List
from core.base_skill import BaseSkill
from core.prompt_loader import PromptLoader
from core.config_loader import ConfigLoader


class SurgicalFileModifierSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "surgical_file_modifier"

    @property
    def description(self) -> str:
        return PromptLoader.get("skills", "SurgicalFileModifierSkill")

    def execute(self, **kwargs: Any) -> bool:
        file_path: str = kwargs.get("file_path", "")
        new_prompt: str = kwargs.get("new_prompt", "")
        demos: List[dict] = kwargs.get("demos", [])

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Target path does not exist: {file_path}")
              
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        frontmatter = ""
        body = content
        frontmatter_match = re.match(r"^(---\s*\n[\s\S]*?\n---\s*\n)", content)
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            body = content[len(frontmatter):]

        demo_markdown = ""
        if demos:
            demo_markdown = "\n\n## Optimized Agent Skills & Demos\n"
            for i, d in enumerate(demos):
                ctx = d.get('input_context', d.get('input', ''))
                resp = d.get('output_response', d.get('output', ''))
                demo_markdown += f"\n### Example Task {i+1}\n* **Context:** {ctx}\n* **Target Action:** {resp}\n"

        final_body = f"{new_prompt.strip()}{demo_markdown}"
        
        base, ext = os.path.splitext(file_path)
        optimized_file_path = f"{base}{ConfigLoader.get("file_suffixes", "optimized")}{ext}"

        with open(optimized_file_path, "w", encoding="utf-8") as f:
            f.write(frontmatter + final_body)

        return True
