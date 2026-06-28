from typing import Dict
from core.base_skill import BaseSkill
from core.prompt_loader import PromptLoader
from core.skills.file_modifier import SurgicalFileModifierSkill
from core.skills.model_connector import ModelConnectorSkill
from core.skills.spec_optimizer import SpecStructuralIsolationSkill
from core.skills.dataset_logger import DatasetLoggingSkill
from core.skills.directory_scanner import DirectoryScannerSkill
from core.skills.verifier import VerificationSkill

class SkillRegistry:
    
    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}
        # Auto-register available concrete skills
        self.register(SurgicalFileModifierSkill())
        self.register(ModelConnectorSkill())
        self.register(SpecStructuralIsolationSkill())
        self.register(DatasetLoggingSkill())
        self.register(DirectoryScannerSkill())
        self.register(VerificationSkill())

    def register(self, skill: BaseSkill) -> None:
        """Registers a concrete skill class instantiation into the manager lookups."""
        self._skills[skill.name] = skill

    def get_skill(self, name: str) -> BaseSkill:
        """Retrieves a registered skill by its explicit structural name handle."""
        if name not in self._skills:
            raise KeyError(f"Skill '{name}' is not registered in the framework engine.")
        return self._skills[name]

    def list_manifests(self) -> list:
        """Generates schema lists of all registered tools for auditing purposes."""
        return [skill.get_manifest() for skill in self._skills.values()]


SkillRegistry.__doc__ = PromptLoader.get("skills", "Registry")
