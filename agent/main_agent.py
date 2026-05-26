"""
agent/main_agent.py
PharmaLit MVP — Agent configuration.

Previously used Google ADK LlmAgent (Gemini).
Now exports the raw tool list used by BedrockAgent.
Google ADK is still used for MCP/orchestration elsewhere.
"""
import os

from agent.tools.pubmed_tool import search_pubmed
from agent.tools.preprint_tool import search_preprints
from agent.tools.trials_tool import search_clinical_trials
from agent.tools.rag_tool import search_rag
from agent.tools.scoring_tool import score_target

# Load system prompt
prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.txt")
with open(prompt_path, "r", encoding="utf-8") as f:
    system_prompt = f.read()

# All async tool functions available to the Bedrock agent
AGENT_TOOLS = [
    search_pubmed,
    search_preprints,
    search_clinical_trials,
    search_rag,
    score_target,
]
