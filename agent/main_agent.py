"""
agent/main_agent.py — Tool list for the Gemini agent.
score_target is available so agent can score genes not pre-discovered by the pipeline.
"""
import os

prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.txt")
with open(prompt_path, "r", encoding="utf-8") as f:
    system_prompt = f.read()

AGENT_TOOLS = []
