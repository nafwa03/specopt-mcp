import os
import sys
import select
import logging
import threading
import anyio
from mcp.server.fastmcp import FastMCP
from core.skills import SkillRegistry
from core.prompt_loader import PromptLoader
from core.artifact_cleanup import cleanup_artifacts
from core.optimizer import (
    run_optimization_pipeline,
    run_specification_pipeline,
    run_code_optimization_pipeline,
    run_verification_pipeline,
    run_section_optimization_pipeline,
    run_dataset_generation_pipeline,
    run_dataset_validation_pipeline,
)


class ThreadLocalStdout:
    def __init__(self, main_stdout, stderr):
        self._main_stdout = main_stdout
        self._stderr = stderr
        self._main_thread_id = threading.get_ident()

    def write(self, data):
        if threading.get_ident() == self._main_thread_id:
            self._main_stdout.write(data)
        else:
            self._stderr.write(data)

    def flush(self):
        if threading.get_ident() == self._main_thread_id:
            self._main_stdout.flush()
        else:
            self._stderr.flush()

    def reconfigure(self, **kwargs):
        self._main_stdout.reconfigure(**kwargs)
        self._stderr.reconfigure(**kwargs)

    def __getattr__(self, name):
        return getattr(self._main_stdout, name)


sys.stdout = ThreadLocalStdout(sys.stdout, sys.stderr)

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "specopt_mcp_debug.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filemode="w"
)
logging.info("specopt-mcp Server Logging Engine Initialized Successfully.")


def _start_stdin_watchdog():
    """Monitor stdin for POLLHUP (client disconnected). Kill process immediately,
    including any in-flight threads making HTTP requests to LM Studio."""
    def _watch():
        try:
            poll = select.poll()
            poll.register(sys.stdin.fileno(), select.POLLHUP | select.POLLERR)
            poll.poll()
            logging.info("stdin POLLHUP — client disconnected. Exiting process.")
        except Exception:
            pass
        os._exit(0)
    threading.Thread(target=_watch, daemon=True).start()


mcp = FastMCP("specopt-mcp Server")
registry = SkillRegistry()


@mcp.tool()
async def optimize_agent_file(agent_markdown_path: str, provider: str = "lm-studio", model: str = "",
                              optimizer_type: str = "mipro", document_dir: str = "") -> str:
    """Dynamically optimizes an agent prompt file using MIPROv2 or GEPA.
    Optionally accepts a document_dir for supplementary reference docs.
    optimizer_type: "mipro" (default) or "gepa"."""
    if not os.path.exists(agent_markdown_path):
        logging.error(f"Target execution file path missing: {agent_markdown_path}")
        return f"Error: Target file not found at path: {agent_markdown_path}"

    if document_dir and not os.path.isdir(document_dir):
        return f"Error: Document directory not found at path: {document_dir}"

    connection_skill = registry.get_skill("model_connector")
    lm_client = connection_skill.execute(provider=provider, model=model)

    logging.info("Spawning agent optimization worker thread using AnyIO context synchronizer...")
    try:
        with anyio.fail_after(3600):
            result = await anyio.to_thread.run_sync(
                lambda: run_optimization_pipeline(
                    agent_markdown_path, provider, model, lm_client, registry,
                    optimizer_type=optimizer_type,
                    document_dir=document_dir,
                )
            )
    except TimeoutError:
        logging.error("Optimization pipeline timed out after 3600 seconds")
        return "Error: Optimization pipeline timed out after 60 minutes. The process may be blocked."
    return result


optimize_agent_file.__doc__ = PromptLoader.get("tools", "optimize_agent_file")


@mcp.tool()
async def optimize_specification_file(spec_json_path: str, provider: str = "lm-studio", model: str = "") -> str:
    if not os.path.exists(spec_json_path):
        logging.error(f"Target specification file path missing: {spec_json_path}")
        return f"Error: Target file not found at path: {spec_json_path}"

    connection_skill = registry.get_skill("model_connector")
    lm_client = connection_skill.execute(provider=provider, model=model)

    logging.info("Spawning spec optimization worker thread using AnyIO context synchronizer...")
    result = await anyio.to_thread.run_sync(
        run_specification_pipeline,
        spec_json_path,
        provider,
        model,
        lm_client,
        registry
    )
    return result


optimize_specification_file.__doc__ = PromptLoader.get("tools", "optimize_specification_file")


@mcp.tool()
async def optimize_skill_logic(skill_file_path: str, provider: str = "lm-studio", model: str = "",
                               optimizer_type: str = "mipro") -> str:
    """Optimizes Python skill code using MIPROv2 or GEPA with pytest validation.
    optimizer_type: "mipro" (default) or "gepa"."""
    if not os.path.exists(skill_file_path):
        return f"Error: Target file not found at path: {skill_file_path}"
    if not skill_file_path.endswith(".py"):
        return f"Error: The self-mutation engine can only optimize valid Python (.py) source files."

    connection_skill = registry.get_skill("model_connector")
    lm_client = connection_skill.execute(provider=provider, model=model)

    logging.info("Spawning code optimization worker thread...")
    result = await anyio.to_thread.run_sync(
        lambda: run_code_optimization_pipeline(
            skill_file_path, provider, model, lm_client, registry,
            optimizer_type=optimizer_type,
        )
    )
    return result


optimize_skill_logic.__doc__ = PromptLoader.get("tools", "optimize_skill_logic")


@mcp.tool()
async def verify_prompt_generalization(agent_markdown_path: str, provider: str = "lm-studio", model: str = "") -> str:
    if not os.path.exists(agent_markdown_path):
        return f"Error: Target file not found at path: {agent_markdown_path}"

    connection_skill = registry.get_skill("model_connector")
    lm_client = connection_skill.execute(provider=provider, model=model)

    logging.info("Spawning QA verification worker thread using VerificationSkill...")
    result = await anyio.to_thread.run_sync(
        run_verification_pipeline,
        agent_markdown_path,
        provider,
        model,
        lm_client,
        registry
    )
    return result


verify_prompt_generalization.__doc__ = PromptLoader.get("tools", "verify_prompt_generalization")


@mcp.tool()
async def optimize_agents_file_by_section(agents_markdown_path: str, provider: str = "lm-studio",
                                          model: str = "") -> str:
    if not os.path.exists(agents_markdown_path):
        return f"Error: Target file not found at path: {agents_markdown_path}"

    connection_skill = registry.get_skill("model_connector")
    lm_client = connection_skill.execute(provider=provider, model=model)

    logging.info("Spawning section optimization worker thread...")
    result = await anyio.to_thread.run_sync(
        run_section_optimization_pipeline,
        agents_markdown_path,
        provider,
        model,
        lm_client,
        registry
    )
    return result


optimize_agents_file_by_section.__doc__ = PromptLoader.get("tools", "optimize_agents_file_by_section")


@mcp.tool()
async def cleanup_pipeline_artifacts(directory_path: str = "") -> str:
    """Move all pipeline-generated artifacts to a timestamped archive folder."""
    target = directory_path.strip() if directory_path.strip() else os.getcwd()
    if not os.path.isdir(target):
        return f"Error: '{target}' is not a valid directory."

    logging.info("Spawning pipeline artifact cleanup for: %s", target)
    result = await anyio.to_thread.run_sync(cleanup_artifacts, target)
    if result["count"] == 0:
        return "No artifacts found. Workspace is clean."
    return f"Moved {result['count']} artifact(s) to {result['archive_path']}"


cleanup_pipeline_artifacts.__doc__ = PromptLoader.get("tools", "cleanup_pipeline_artifacts")


@mcp.tool()
async def generate_training_dataset(agent_markdown_path: str, provider: str = "lm-studio", model: str = "",
                                    num_examples: int = 5, document_dir: str = "",
                                    curate: bool = False, curation_threshold: float = 0.0,
                                    output_format: str = "json") -> str:
    """Generate a synthetic training dataset from an agent markdown file.
    Supports document_dir for supplementary reference docs, LLM-as-judge curation,
    and multiple output formats (json, jsonl, alpaca, chatml)."""
    if not os.path.exists(agent_markdown_path):
        return f"Error: Target file not found at path: {agent_markdown_path}"

    if document_dir and not os.path.isdir(document_dir):
        return f"Error: Document directory not found at path: {document_dir}"

    connection_skill = registry.get_skill("model_connector")
    lm_client = connection_skill.execute(provider=provider, model=model)

    logging.info("Spawning dataset generation worker thread...")
    result = await anyio.to_thread.run_sync(
        run_dataset_generation_pipeline,
        agent_markdown_path,
        provider,
        model,
        lm_client,
        registry,
        num_examples,
        document_dir,
        curate,
        curation_threshold,
        output_format,
    )
    return result


generate_training_dataset.__doc__ = PromptLoader.get("tools", "generate_training_dataset")


@mcp.tool()
async def validate_generated_dataset(dataset_path: str, agent_markdown_path: str, provider: str = "lm-studio",
                                     model: str = "", document_dir: str = "") -> str:
    """Validates a generated dataset against four quality criteria: alignment,
    diversity, baseline failure test, and negative class ratio."""
    if not os.path.exists(dataset_path):
        return f"Error: Dataset file not found at path: {dataset_path}"
    if not os.path.exists(agent_markdown_path):
        return f"Error: Agent file not found at path: {agent_markdown_path}"

    connection_skill = registry.get_skill("model_connector")
    lm_client = connection_skill.execute(provider=provider, model=model)

    logging.info("Spawning dataset validation worker thread...")
    result = await anyio.to_thread.run_sync(
        run_dataset_validation_pipeline,
        dataset_path,
        agent_markdown_path,
        provider,
        model,
        lm_client,
        registry,
        document_dir,
    )
    return result


validate_generated_dataset.__doc__ = PromptLoader.get("tools", "validate_generated_dataset")


def main():
    """Global execution entrypoint hook registered by setup.py."""
    #_start_stdin_watchdog()
    mcp.run(transport='stdio')


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.flush()
    sys.stderr.flush()

    logging.info("Starting FastMCP Stdio Transport stream with line_buffering disabled.")
    #_start_stdin_watchdog()
    mcp.run(transport='stdio')
