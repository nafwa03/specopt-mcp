import asyncio
import subprocess
import requests
from openai import BadRequestError
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from core.prompt_loader import PromptLoader
from core.config_loader import ConfigLoader
from core.skill_md_loader import SkillMDLoader

def _build_system_prompt() -> str:
    base = PromptLoader.get("agent_brain", "system_prompt")
    md_skills = SkillMDLoader.load_all()
    if not md_skills:
        return base

    lines = ["\n\nAvailable markdown skill definitions:"]
    for name, data in md_skills.items():
        fm = data["frontmatter"]
        in_list = ", ".join(
            f"{list(k.keys())[0]}: {list(k.values())[0]}" for k in fm.get("inputs", [])
        )
        out_list = ", ".join(
            f"{list(k.keys())[0]}: {list(k.values())[0]}" for k in fm.get("outputs", [])
        )
        purpose = ""
        if "## Purpose" in data["body"]:
            purpose = data["body"].split("## Purpose")[-1].split("##")[0].strip().split("\n")[0]
        lines.append(f"- {name}: inputs({in_list}) -> outputs({out_list})")
        if purpose:
            lines.append(f"  {purpose}")

    return base + "\n".join(lines)


def _check_lm_studio_ready(api_base: str, model: str) -> bool:
    """Check LM Studio has the expected model loaded. If none loaded, try `lms load`."""
    models_url = api_base.rstrip("/") + "/models"
    try:
        resp = requests.get(models_url, timeout=5)
        resp.raise_for_status()
        models = resp.json()
    except requests.ConnectionError:
        print(f"[Error] Cannot reach LM Studio at {api_base}. Is it running?")
        return False
    except Exception as e:
        print(f"[Error] Failed to query LM Studio models: {e}")
        return False

    loaded_ids = [m.get("id", "") for m in models.get("data", []) if m.get("id")]
    if not loaded_ids:
        print(f"[Warning] LM Studio has no models loaded. Attempting `lms load {model}` ...")
        try:
            subprocess.run(["lms", "load", model], check=True, timeout=60)
            print("[Info] Model load initiated. Retrying availability check...")
            import time
            time.sleep(3)
            resp2 = requests.get(models_url, timeout=5)
            resp2.raise_for_status()
            models2 = resp2.json()
            loaded_ids = [m.get("id", "") for m in models2.get("data", []) if m.get("id")]
            if loaded_ids:
                print(f"[Info] Model '{model}' loaded successfully.")
                return True
            else:
                print(f"[Error] `lms load` completed but model still not available.")
                return False
        except FileNotFoundError:
            print("[Error] `lms` CLI not found. Install it or load a model in the LM Studio UI.")
            return False
        except subprocess.TimeoutExpired:
            print("[Error] `lms load` timed out after 60s.")
            return False
        except subprocess.CalledProcessError as e:
            print(f"[Error] `lms load` failed (exit {e.returncode}). Load the model manually in LM Studio.")
            return False

    if model and model not in loaded_ids:
        print(f"[Warning] Configured model '{model}' is not in LM Studio's loaded list: {loaded_ids}")
        print(f"[Info] Attempting `lms load {model}` ...")
        try:
            subprocess.run(["lms", "load", model], check=True, timeout=60)
            print("[Info] Model load initiated.")
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            print(f"[Warning] Could not auto-load model. Available models: {loaded_ids}")
            return False

    return True


class AgenticOrchestrator:
    def __init__(self, server_script="server.py"):
        # 💡 UPDATE: Point this directly to your new system command
        self.server_params = StdioServerParameters(
            command="specopt-server",
            args=[]
        )
        self.mcp_session = None

    def get_tools(self):
        """Builds LangChain tool bindings linked directly to this orchestrator instance context."""

        @tool(description=PromptLoader.get('agent_brain', 'optimize_agent_file_tool'))
        async def optimize_agent_file_tool(agent_markdown_path: str, provider: str = "lm-studio", model: str = "",
                                           optimizer_type: str = "mipro", document_dir: str = "") -> str:
            print(f"[Agent Action] Invoking optimize_agent_file_tool for: {agent_markdown_path}")
            response = await self.mcp_session.call_tool(
                name="optimize_agent_file",
                arguments={
                    "agent_markdown_path": agent_markdown_path,
                    "provider": provider,
                    "model": model,
                    "optimizer_type": optimizer_type,
                    "document_dir": document_dir,
                }
            )
            return response.content[0].text

        @tool(description=PromptLoader.get('agent_brain', 'optimize_skill_logic_tool'))
        async def optimize_skill_logic_tool(skill_file_path: str, provider: str = "lm-studio", model: str = "",
                                            optimizer_type: str = "mipro") -> str:
            print(f"[Agent Action] Invoking optimize_skill_logic_tool for: {skill_file_path}")
            response = await self.mcp_session.call_tool(
                name="optimize_skill_logic",
                arguments={
                    "skill_file_path": skill_file_path,
                    "provider": provider,
                    "model": model,
                    "optimizer_type": optimizer_type,
                }
            )
            return response.content[0].text

        @tool(description=PromptLoader.get('agent_brain', 'optimize_entire_skill_directory_tool'))
        async def optimize_entire_skill_directory_tool(directory_path: str, provider: str = "lm-studio",
                                                       model: str = "") -> str:
            print(f"[Agent Action] Invoking optimize_entire_skill_directory_tool for: {directory_path}")
            response = await self.mcp_session.call_tool(
                name="optimize_entire_skill_directory",
                arguments={"directory_path": directory_path, "provider": provider, "model": model}
            )
            return response.content[0].text

        @tool(description=PromptLoader.get('agent_brain', 'verify_prompt_generalization_tool'))
        async def verify_prompt_generalization_tool(agent_markdown_path: str, provider: str = "lm-studio",
                                                    model: str = "") -> str:
            print(f"[Agent Action] Invoking QA Verification Tool for: {agent_markdown_path}")
            response = await self.mcp_session.call_tool(
                name="verify_prompt_generalization",
                arguments={"agent_markdown_path": agent_markdown_path, "provider": provider, "model": model}
            )
            return response.content[0].text

        @tool(description=PromptLoader.get('agent_brain', 'generate_training_dataset_tool'))
        async def generate_training_dataset_tool(agent_markdown_path: str, provider: str = "lm-studio",
                                                 model: str = "", num_examples: int = 5,
                                                 document_dir: str = "") -> str:
            print(f"[Agent Action] Generating training dataset from: {agent_markdown_path}")
            response = await self.mcp_session.call_tool(
                name="generate_training_dataset",
                arguments={
                    "agent_markdown_path": agent_markdown_path,
                    "provider": provider,
                    "model": model,
                    "num_examples": num_examples,
                    "document_dir": document_dir,
                }
            )
            return response.content[0].text

        @tool(description=PromptLoader.get('agent_brain', 'validate_generated_dataset_tool'))
        async def validate_generated_dataset_tool(dataset_path: str, agent_markdown_path: str,
                                                  provider: str = "lm-studio", model: str = "",
                                                  document_dir: str = "") -> str:
            print(f"[Agent Action] Validating dataset: {dataset_path}")
            response = await self.mcp_session.call_tool(
                name="validate_generated_dataset",
                arguments={
                    "dataset_path": dataset_path,
                    "agent_markdown_path": agent_markdown_path,
                    "provider": provider,
                    "model": model,
                    "document_dir": document_dir,
                }
            )
            return response.content[0].text

        return [optimize_agent_file_tool, optimize_skill_logic_tool, optimize_entire_skill_directory_tool, verify_prompt_generalization_tool, generate_training_dataset_tool, validate_generated_dataset_tool]

    async def run_reasoning_loop(self, user_query: str):
        print("[Init] Initializing Agentic reasoning channel...")

        async with stdio_client(self.server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                # Bind the network session instance context to the orchestrator object
                self.mcp_session = session

                # Fetch dynamically linked tools
                tools_list = self.get_tools()

                brain_cfg = ConfigLoader.get("agent_brain")
                model_name = brain_cfg["model"].strip()
                api_base = brain_cfg["api_base"].rstrip("/")

                if not _check_lm_studio_ready(api_base, model_name):
                    print("[Error] Aborting. Requires a loaded model in LM Studio.")
                    return

                brain_llm = ChatOpenAI(
                    model=model_name,
                    base_url=api_base,
                    api_key=brain_cfg["api_key"],
                    temperature=brain_cfg["temperature"]
                ).bind_tools(tools_list)

                messages = [
                    SystemMessage(content=_build_system_prompt()),
                    HumanMessage(content=user_query)
                ]

                print(f"\n[User] Request: {user_query}")
                print("[Analyze] Agent is analyzing request and choosing a strategy...")

                try:
                    ai_analysis = brain_llm.invoke(messages)
                except BadRequestError as e:
                    print(f"[Error] LM Studio request failed: {e}")
                    print("[Error] No model is loaded in LM Studio. Load a model and try again.")
                    return

                if ai_analysis.tool_calls:
                    for call in ai_analysis.tool_calls:
                        # Locate the matching local tool tool object handle and execute it
                        matched_tool = next((t for t in tools_list if t.name == call['name']), None)
                        if matched_tool:
                            print(f"\n[Decision] Selected Tool: '{call['name']}'")
                            result = await matched_tool.ainvoke(call['args'])
                            print(f"\n[Result] Pipeline Response:\n{result}")
                else:
                    print("[Error] Agent did not trigger a tool tool call. Response:", ai_analysis.content)


if __name__ == '__main__':
    # Initialize our object-oriented runner
    orchestrator = AgenticOrchestrator()

    # Define a clean natural language task query
    task = (
        "Please optimize our prompt file at './agents/writer.md' using 10 trials via LM Studio. "
        "Immediately after the optimization pass finishes, execute our QA validation tool on the file "
        "to verify if the changes genuinely improved our accuracy parameters on unseen test data."
    )

    asyncio.run(orchestrator.run_reasoning_loop(task))


