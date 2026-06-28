import os
import re
import yaml
from typing import Any


class SkillMDLoader:
    _skills: dict[str, dict] | None = None
    _skills_dir: str | None = None

    @classmethod
    def configure(cls, skills_dir: str):
        cls._skills_dir = skills_dir

    @classmethod
    def _resolve_dir(cls) -> str:
        if cls._skills_dir:
            return cls._skills_dir
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills")

    @classmethod
    def load_all(cls) -> dict[str, dict]:
        if cls._skills is not None:
            return cls._skills
        skills_dir = cls._resolve_dir()
        cls._skills = {}
        if not os.path.isdir(skills_dir):
            return cls._skills
        for fname in sorted(os.listdir(skills_dir)):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(skills_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            parsed = cls._parse(content, fname)
            if parsed is not None:
                cls._skills[parsed["name"]] = parsed
        return cls._skills

    @classmethod
    def _parse(cls, content: str, fname: str = "") -> dict | None:
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
        if not match:
            return None
        frontmatter = yaml.safe_load(match.group(1))
        body = match.group(2).strip()
        if not isinstance(frontmatter, dict) or "name" not in frontmatter:
            return None
        return {
            "name": frontmatter["name"],
            "frontmatter": frontmatter,
            "body": body,
            "file": fname,
        }

    @classmethod
    def get(cls, name: str) -> dict | None:
        skills = cls.load_all()
        return skills.get(name)

    @classmethod
    def clear_cache(cls):
        cls._skills = None
