from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseSkill(ABC):
    """
    Abstract Base Class establishing the standard interface for all Agent Skills.
    Ensures consistent metadata registry and execution schemas across the project.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier string for the skill registration."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Detailed documentation explaining the skill's purpose to the orchestrator."""
        pass

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """
        The uniform execution entrypoint for the business logic.
        Accepts flexible keyword arguments and returns a standardized outcome.
        """
        pass

    def get_manifest(self) -> Dict[str, str]:
        """Self-documenting method to expose skill traits to LLMs or Routers."""
        return {
            "name": self.name,
            "description": self.description
        }
