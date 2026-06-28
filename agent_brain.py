import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from core.prompt_loader import PromptLoader
from core.config_loader import ConfigLoader

AGENT_SYSTEM_PROMPT = PromptLoader.get("agent_brain", "system_prompt")


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
        def optimize_agent_file_tool(agent_markdown_path: str, provider: str = "lm-studio", model: str = "",
                                     optimizer_type: str = "mipro", document_dir: str = "") -> str:
            print(f"[Agent Action] Invoking optimize_agent_file_tool for: {agent_markdown_path}")
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(
                self.mcp_session.call_tool(
                    name="optimize_agent_file",
                    arguments={
                        "agent_markdown_path": agent_markdown_path,
                        "provider": provider,
                        "model": model,
                        "optimizer_type": optimizer_type,
                        "document_dir": document_dir,
                    }
                )
            )
            return response.content.text

        @tool(description=PromptLoader.get('agent_brain', 'optimize_skill_logic_tool'))
        def optimize_skill_logic_tool(skill_file_path: str, provider: str = "lm-studio", model: str = "",
                                      optimizer_type: str = "mipro") -> str:
            print(f"[Agent Action] Invoking optimize_skill_logic_tool for: {skill_file_path}")
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(
                self.mcp_session.call_tool(
                    name="optimize_skill_logic",
                    arguments={
                        "skill_file_path": skill_file_path,
                        "provider": provider,
                        "model": model,
                        "optimizer_type": optimizer_type,
                    }
                )
            )
            return response.content.text

        @tool(description=PromptLoader.get('agent_brain', 'optimize_entire_skill_directory_tool'))
        def optimize_entire_skill_directory_tool(directory_path: str, provider: str = "lm-studio",
                                                 model: str = "") -> str:
            print(f"[Agent Action] Invoking optimize_entire_skill_directory_tool for: {directory_path}")
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(
                self.mcp_session.call_tool(
                    name="optimize_entire_skill_directory",
                    arguments={"directory_path": directory_path, "provider": provider, "model": model}
                )
            )
            return response.content.text

        @tool(description=PromptLoader.get('agent_brain', 'verify_prompt_generalization_tool'))
        def verify_prompt_generalization_tool(agent_markdown_path: str, provider: str = "lm-studio",
                                              model: str = "") -> str:
            print(f"[Agent Action] Invoking QA Verification Tool for: {agent_markdown_path}")
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(
                self.mcp_session.call_tool(
                    name="verify_prompt_generalization",
                    arguments={"agent_markdown_path": agent_markdown_path, "provider": provider, "model": model}
                )
            )
            return response.content.text

        @tool(description=PromptLoader.get('agent_brain', 'generate_training_dataset_tool'))
        def generate_training_dataset_tool(agent_markdown_path: str, provider: str = "lm-studio",
                                           model: str = "", num_examples: int = 5,
                                           document_dir: str = "") -> str:
            print(f"[Agent Action] Generating training dataset from: {agent_markdown_path}")
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(
                self.mcp_session.call_tool(
                    name="generate_training_dataset",
                    arguments={
                        "agent_markdown_path": agent_markdown_path,
                        "provider": provider,
                        "model": model,
                        "num_examples": num_examples,
                        "document_dir": document_dir,
                    }
                )
            )
            return response.content.text

        @tool(description=PromptLoader.get('agent_brain', 'validate_generated_dataset_tool'))
        def validate_generated_dataset_tool(dataset_path: str, agent_markdown_path: str,
                                            provider: str = "lm-studio", model: str = "",
                                            document_dir: str = "") -> str:
            print(f"[Agent Action] Validating dataset: {dataset_path}")
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(
                self.mcp_session.call_tool(
                    name="validate_generated_dataset",
                    arguments={
                        "dataset_path": dataset_path,
                        "agent_markdown_path": agent_markdown_path,
                        "provider": provider,
                        "model": model,
                        "document_dir": document_dir,
                    }
                )
            )
            return response.content.text

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
                brain_llm = ChatOpenAI(
                    model=brain_cfg["model"],
                    api_base=brain_cfg["api_base"],
                    api_key=brain_cfg["api_key"],
                    temperature=brain_cfg["temperature"]
                ).bind_tools(tools_list)

                messages = [
                    SystemMessage(content=AGENT_SYSTEM_PROMPT),
                    HumanMessage(content=user_query)
                ]

                print(f"\n[User] Request: {user_query}")
                print("[Analyze] Agent is analyzing request and choosing a strategy...")

                ai_analysis = brain_llm.invoke(messages)

                if ai_analysis.tool_calls:
                    for call in ai_analysis.tool_calls:
                        # Locate the matching local tool tool object handle and execute it
                        matched_tool = next((t for t in tools_list if t.name == call['name']), None)
                        if matched_tool:
                            print(f"\n[Decision] Selected Tool: '{call['name']}'")
                            result = matched_tool.invoke(call['args'])
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


