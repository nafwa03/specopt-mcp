import logging
from typing import Any
import requests
import dspy
from core.base_skill import BaseSkill
from core.prompt_loader import PromptLoader
from core.config_loader import ConfigLoader

# Custom LM class that avoids response_format issues with LM Studio
class LMStudioLM(dspy.BaseLM):
    """Custom LM class for LM Studio that doesn't use response_format."""

    def __init__(self, model: str, api_base: str, api_key: str = "not-needed", timeout: int = 600):
        self.model = model
        self.api_base = api_base
        self.api_key = api_key
        self.timeout = timeout
        super().__init__(model=model)
        logging.info(f"LMStudioLM initialized with model={model}, api_base={api_base}")

    def __call__(self, prompt: str = None, messages: list = None, **kwargs) -> list[str]:
        """Make a request to LM Studio without response_format."""
        logging.info(f"LMStudioLM.__call__ called with prompt={prompt[:100] if prompt else 'None'}...")
        logging.info(f"LMStudioLM kwargs: {kwargs}")

        if messages is None:
            messages = [{"role": "user", "content": prompt}]

        # Remove response_format if present to avoid LM Studio errors
        if "response_format" in kwargs:
            logging.info(f"Removing response_format from kwargs: {kwargs['response_format']}")
            kwargs.pop("response_format", None)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024),
            **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens", "n"]}
        }

        # Add n parameter if specified (for multiple completions)
        if "n" in kwargs:
            payload["n"] = kwargs["n"]

        logging.info(f"Sending request to LM Studio: {self.api_base}/chat/completions")
        logging.info(f"Payload keys: {list(payload.keys())}")

        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            # Extract completions
            completions = []
            for choice in data.get("choices", []):
                completions.append(choice.get("message", {}).get("content", ""))

            logging.info(f"LM Studio returned {len(completions)} completions")

            # If n > 1, return list; otherwise return single completion wrapped in list
            if kwargs.get("n", 1) > 1:
                return completions
            else:
                return completions if completions else [""]

        except Exception as e:
            logging.error(f"LM Studio request failed: {str(e)}")
            raise

    def copy(self, **kwargs):
        """Create a copy of this LM with optional parameter overrides."""
        return LMStudioLM(
            model=kwargs.get("model", self.model),
            api_base=kwargs.get("api_base", self.api_base),
            api_key=kwargs.get("api_key", self.api_key),
            timeout=kwargs.get("timeout", self.timeout)
        )


class OllamaLM(dspy.BaseLM):
    """Placeholder LM class for Ollama."""

    def __init__(self, model: str, api_base: str, api_key: str = "ollama-token", timeout: int = 600):
        self.model = model
        self.api_base = api_base
        self.api_key = api_key
        self.timeout = timeout
        super().__init__(model=model)

    def __call__(self, prompt: str = None, messages: list = None, **kwargs) -> list[str]:
        logging.info(f"OllamaLM placeholder called with model={self.model}")
        return ["Ollama placeholder response"]

    def copy(self, **kwargs):
        return OllamaLM(
            model=kwargs.get("model", self.model),
            api_base=kwargs.get("api_base", self.api_base),
            api_key=kwargs.get("api_key", self.api_key),
            timeout=kwargs.get("timeout", self.timeout)
        )


class LemonadeLM(dspy.BaseLM):
    """Placeholder LM class for Lemonade server."""

    def __init__(self, model: str, api_base: str, api_key: str = "lemonade-token", timeout: int = 600):
        self.model = model
        self.api_base = api_base
        self.api_key = api_key
        self.timeout = timeout
        super().__init__(model=model)

    def __call__(self, prompt: str = None, messages: list = None, **kwargs) -> list[str]:
        logging.info(f"LemonadeLM placeholder called with model={self.model}")
        return ["Lemonade placeholder response"]

    def copy(self, **kwargs):
        return LemonadeLM(
            model=kwargs.get("model", self.model),
            api_base=kwargs.get("api_base", self.api_base),
            api_key=kwargs.get("api_key", self.api_key),
            timeout=kwargs.get("timeout", self.timeout)
        )


class ModelConnectorSkill(BaseSkill):
    """
    Concrete Skill that dynamically configures and initializes local LLM providers
    (e.g., LM Studio, Ollama, Lemonade) using a uniform strategy pattern interface.
    """

    @property
    def name(self) -> str:
        return "model_connector"

    @property
    def description(self) -> str:
        return PromptLoader.get("skills", "ModelConnectorSkill")

    def execute(self, **kwargs: Any) -> dspy.LM:
        """
        Switches connection parameters based on provider arguments.
        Returns a configured, operational dspy.LM client object.
        """
        provider: str = kwargs.get("provider", ConfigLoader.get("providers", "default")).lower().strip()
        model_name: str = kwargs.get("model", "")

        configs = ConfigLoader.get("providers")
        known_providers = {k: v for k, v in configs.items() if k != "default"}

        if provider not in known_providers:
            logging.warning(f"Unknown provider '{provider}'. Defaulting to {configs['default']}.")
            provider = configs["default"]

        selected = known_providers[provider]
        target_model = model_name if model_name else selected["default_model"]

        try:
            if provider == "lm-studio":
                lm_client = LMStudioLM(
                    model=target_model,
                    api_base=selected["api_base"],
                    api_key=selected["api_key"],
                    timeout=selected.get("timeout", 600)
                )
            elif provider == "ollama":
                lm_client = OllamaLM(
                    model=target_model,
                    api_base=selected["api_base"],
                    api_key=selected["api_key"],
                    timeout=selected.get("timeout", 600)
                )
            elif provider == "lemonade":
                lm_client = LemonadeLM(
                    model=target_model,
                    api_base=selected["api_base"],
                    api_key=selected["api_key"],
                    timeout=selected.get("timeout", 600)
                )
            else:
                lm_client = dspy.LM(
                    model=target_model,
                    api_base=selected["api_base"],
                    api_key=selected["api_key"],
                    timeout=selected.get("timeout", 600)
                )

            return lm_client

        except Exception as e:
            raise ConnectionError(f"Failed to bind local engine client target '{provider}': {str(e)}")
