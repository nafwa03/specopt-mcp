import os
import yaml


PROMPTS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts.yaml")


def _load_yaml():
    with open(PROMPTS_PATH, "r") as f:
        return yaml.safe_load(f)


def test_prompts_yaml_exists():
    assert os.path.exists(PROMPTS_PATH), f"prompts.yaml not found at {PROMPTS_PATH}"


def test_prompts_yaml_valid_yaml():
    data = _load_yaml()
    assert isinstance(data, dict)


def test_prompts_yaml_has_all_sections():
    data = _load_yaml()
    expected_sections = ["signatures", "skills", "tools", "agent_brain", "defaults"]
    for section in expected_sections:
        assert section in data, f"Missing section '{section}' in prompts.yaml"


def test_signatures_section():
    data = _load_yaml()
    sigs = data["signatures"]
    expected = [
        "DatasetGeneratorSignature",
        "CodeDatasetGeneratorSignature",
        "UniversalJudgeSignature",
        "DynamicAgentSignature",
        "SpecDocumentationSignature",
        "SecurityAuditorSignature",
        "FactGroundingAuditorSignature",
        "CodeOptimizationSignature",
        "ContextualJudgeSignature",
        "DatasetValidatorSignature",
        "UniversalAgentProgram",
        "SpecSectionSignature",
        "SpecSectionQualitySignature",
    ]
    for sig in expected:
        assert sig in sigs, f"Missing signature '{sig}' in prompts.yaml"
        assert isinstance(sigs[sig], str) and len(sigs[sig]) > 10, f"Signature '{sig}' is too short or not a string"


def test_skills_section():
    data = _load_yaml()
    skills = data["skills"]
    expected = [
        "SurgicalFileModifierSkill",
        "ModelConnectorSkill",
        "SpecStructuralIsolationSkill",
        "DatasetLoggingSkill",
        "DirectoryScannerSkill",
        "VerificationSkill",
        "Registry",
    ]
    for skill in expected:
        assert skill in skills, f"Missing skill '{skill}' in prompts.yaml"
        assert isinstance(skills[skill], str) and len(skills[skill]) > 10


def test_tools_section():
    data = _load_yaml()
    tools = data["tools"]
    expected = [
        "optimize_agent_file",
        "optimize_specification_file",
        "optimize_skill_logic",
        "verify_prompt_generalization",
        "optimize_agents_file_by_section",
        "cleanup_pipeline_artifacts",
        "generate_training_dataset",
        "validate_generated_dataset",
    ]
    for tool in expected:
        assert tool in tools, f"Missing tool '{tool}' in prompts.yaml"
        assert isinstance(tools[tool], str) and len(tools[tool]) > 10


def test_agent_brain_section():
    data = _load_yaml()
    brain = data["agent_brain"]
    expected = [
        "system_prompt",
        "optimize_agent_file_tool",
        "optimize_skill_logic_tool",
        "optimize_entire_skill_directory_tool",
        "verify_prompt_generalization_tool",
        "generate_training_dataset_tool",
        "validate_generated_dataset_tool",
    ]
    for key in expected:
        assert key in brain, f"Missing agent_brain key '{key}' in prompts.yaml"
        assert isinstance(brain[key], str) and len(brain[key]) > 10


def test_defaults_section():
    data = _load_yaml()
    defaults = data["defaults"]
    assert "baseline_instructions" in defaults
    assert isinstance(defaults["baseline_instructions"], str) and len(defaults["baseline_instructions"]) > 10


def test_loader_can_load_all_keys():
    from core.prompt_loader import PromptLoader
    PromptLoader.clear_cache()
    PromptLoader.get("signatures", "DatasetGeneratorSignature")
    PromptLoader.get("signatures", "CodeDatasetGeneratorSignature")
    PromptLoader.get("signatures", "UniversalJudgeSignature")
    PromptLoader.get("signatures", "DynamicAgentSignature")
    PromptLoader.get("signatures", "SpecDocumentationSignature")
    PromptLoader.get("signatures", "SecurityAuditorSignature")
    PromptLoader.get("signatures", "FactGroundingAuditorSignature")
    PromptLoader.get("signatures", "CodeOptimizationSignature")
    PromptLoader.get("signatures", "ContextualJudgeSignature")
    PromptLoader.get("signatures", "DatasetValidatorSignature")
    PromptLoader.get("signatures", "UniversalAgentProgram")
    PromptLoader.get("signatures", "SpecSectionSignature")
    PromptLoader.get("signatures", "SpecSectionQualitySignature")
    PromptLoader.get("skills", "SurgicalFileModifierSkill")
    PromptLoader.get("skills", "ModelConnectorSkill")
    PromptLoader.get("skills", "SpecStructuralIsolationSkill")
    PromptLoader.get("skills", "DatasetLoggingSkill")
    PromptLoader.get("skills", "DirectoryScannerSkill")
    PromptLoader.get("skills", "VerificationSkill")
    PromptLoader.get("skills", "Registry")
    PromptLoader.get("tools", "optimize_agent_file")
    PromptLoader.get("tools", "optimize_specification_file")
    PromptLoader.get("tools", "optimize_skill_logic")
    PromptLoader.get("tools", "verify_prompt_generalization")
    PromptLoader.get("tools", "optimize_agents_file_by_section")
    PromptLoader.get("tools", "generate_training_dataset")
    PromptLoader.get("tools", "validate_generated_dataset")
    PromptLoader.get("agent_brain", "system_prompt")
    PromptLoader.get("agent_brain", "optimize_agent_file_tool")
    PromptLoader.get("agent_brain", "optimize_skill_logic_tool")
    PromptLoader.get("agent_brain", "optimize_entire_skill_directory_tool")
    PromptLoader.get("agent_brain", "verify_prompt_generalization_tool")
    PromptLoader.get("agent_brain", "generate_training_dataset_tool")
    PromptLoader.get("agent_brain", "validate_generated_dataset_tool")
    PromptLoader.get("defaults", "baseline_instructions")
