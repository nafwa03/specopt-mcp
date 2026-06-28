---
name: model_connector
inputs:
  - provider: str
  - model: str
outputs:
  - lm_client: dspy.LM
model: any
temperature: 0.0
---

## Purpose
Dynamically configures and initializes a DSPy language model client for local LLM providers (LM Studio, Ollama, Lemonade) using a uniform strategy pattern interface.

## Behavior
1. Receives a provider string ("lm-studio", "ollama", "lemonade") and optional model name.
2. Looks up provider configuration (api_base, api_key, timeout) from config.yaml.
3. Instantiates the corresponding DSPy BaseLM subclass.
4. Returns the configured LM client ready for use in optimization pipelines.

## Example
```python
skill = ModelConnectorSkill()
lm = skill.execute(provider="lm-studio", model="mistralai/mistral-7b-instruct-v0.3")
# Returns an LMStudioLM instance connected to localhost:1234
```
