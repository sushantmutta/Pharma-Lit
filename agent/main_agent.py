import os
from google.adk.agents import LlmAgent
from agent.tools.pubmed_tool import pubmed_search_tool
from agent.tools.trials_tool import trials_search_tool
from agent.tools.rag_tool import rag_search_tool
from agent.tools.scoring_tool import score_target_tool
from agent.tools.preprint_tool import preprint_search_tool

prompt_path = os.path.join(os.path.dirname(
    __file__), "prompts", "system_prompt.txt")
with open(prompt_path, "r", encoding="utf-8") as f:
    system_prompt = f.read()

agent = LlmAgent(
    name="PharmaLitAgent",
    model="gemini-2.5-flash",
    instruction=system_prompt,
    tools=[
        pubmed_search_tool,
        preprint_search_tool,
        trials_search_tool,
        rag_search_tool,
        score_target_tool,
    ]
)
