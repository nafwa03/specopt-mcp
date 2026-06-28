# specopt-mcp

Optimized Object-Oriented Skill Architecture for DSPy MIPROv2 Agent Prompt Tuning via MCP.

## Repository Blueprint

- `server.py`: Pure FastMCP Transport Server router.
- `agent_brain.py`: LangChain Orchestration Agent client loop.
- `core/`: Decoupled business logic:
  - `base_skill.py`: Interface class for skills.
  - `optimizer.py`: DSPy MIPROv2 optimization pipeline.
  - `skills/`:
    - `__init__.py`: Central Skill Registry.
    - `file_modifier.py`: Surgical markdown file modifier skill.
    - `model_connector.py`: Strategy model connector skill supporting LM Studio, Ollama, and Lemonade.
- `tests/`: Automated unit tests.
- `agents/`: Agent prompts targets.

## Quickstart

```bash
# 1. Spin up and activate venv
python -m venv venv
venv\Scripts\activate  # On Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run unit tests
pytest -v

# 4. Launch Agentic Loop (ensure LM Studio is running on port 1234)
python agent_brain.py
```
