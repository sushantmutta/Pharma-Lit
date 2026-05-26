"""
agent/bedrock_agent.py
PharmaLit MVP — AWS Bedrock Converse API agent loop.

Replaces the Google ADK LlmAgent/InMemoryRunner while keeping all
tool functions intact.  The loop:
  1. Converts Python async functions → Bedrock tool definitions (JSON Schema)
  2. Sends system prompt + user message to Claude via bedrock-runtime Converse
  3. Calls matching tool functions on every ToolUse block
  4. Feeds results back to Claude in the next turn
  5. Returns the final text and a trace of all tool calls
"""
from __future__ import annotations

import asyncio
import inspect
import json
import os
import traceback
from typing import Any, Callable

import boto3
from rich.console import Console

console = Console()

# ── Model configuration ────────────────────────────────────────────────────────
# Claude 3 Haiku: fastest + cheapest; good for structured tool-call pipelines
# Claude 3.5 Sonnet: higher reasoning (change MODEL_ID if desired)
MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID",
    "us.anthropic.claude-3-haiku-20240307-v1:0",   # cross-region inference profile
)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
MAX_TOKENS = int(os.getenv("BEDROCK_MAX_TOKENS", "4096"))

# ── Type helpers ───────────────────────────────────────────────────────────────
PYTHON_TO_JSON = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
    "NoneType": "null",
}


def _python_type_to_json(annotation) -> str:
    """Convert a Python type annotation to a JSON Schema type string."""
    if annotation is inspect.Parameter.empty:
        return "string"
    name = getattr(annotation, "__name__", str(annotation))
    # handle Optional[x] → "string"
    if "Optional" in name or "Union" in name:
        return "string"
    return PYTHON_TO_JSON.get(name, "string")


def _build_tool_spec(fn: Callable) -> dict:
    """
    Auto-generates a Bedrock tool spec from a Python function's signature
    and docstring.
    """
    sig = inspect.signature(fn)
    doc = (fn.__doc__ or "").strip().split("\n")[0]  # first line only

    props: dict[str, Any] = {}
    required: list[str] = []

    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue
        json_type = _python_type_to_json(param.annotation)
        props[name] = {"type": json_type, "description": name}
        if param.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "toolSpec": {
            "name": fn.__name__,
            "description": doc,
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": props,
                    "required": required,
                }
            },
        }
    }


# ── Bedrock agent loop ─────────────────────────────────────────────────────────

async def run_bedrock_agent(
    user_message: str,
    system_prompt: str,
    tool_functions: list[Callable],
    steps: list[dict],
    trace_lines: list[str],
) -> str:
    """
    Runs a Converse-based tool-calling loop against AWS Bedrock.

    Args:
        user_message:    The user's query/prompt string.
        system_prompt:   The system instruction loaded from system_prompt.txt.
        tool_functions:  List of async Python functions to expose as tools.
        steps:           Mutable list; tool events appended here for the UI.
        trace_lines:     Mutable list; raw trace lines appended here.

    Returns:
        Final text output from the model (the hypothesis brief).
    """
    # Build Bedrock client
    try:
        bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    except Exception as e:
        raise RuntimeError(f"Failed to create Bedrock client: {e}") from e

    # Build tool map  name → function
    tool_map: dict[str, Callable] = {fn.__name__: fn for fn in tool_functions}
    tool_config = {"tools": [_build_tool_spec(fn) for fn in tool_functions]}

    messages: list[dict] = [{"role": "user", "content": [{"text": user_message}]}]
    final_text = ""
    max_turns = 15  # safety cap on tool-calling iterations

    for turn in range(max_turns):
        # Call Bedrock Converse API (sync boto3 → run in executor)
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: bedrock.converse(
                    modelId=MODEL_ID,
                    system=[{"text": system_prompt}],
                    messages=messages,
                    toolConfig=tool_config,
                    inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": 0.1},
                ),
            )
        except Exception as e:
            err = f"Bedrock Converse call failed: {e}"
            console.print(f"[red]{err}[/red]")
            traceback.print_exc()
            steps.append({"icon": "X", "label": err, "detail": str(e), "status": "error"})
            return f"# Bedrock Error\n\n{e}"

        output_msg = response.get("output", {}).get("message", {})
        stop_reason = response.get("stopReason", "end_turn")
        content_blocks = output_msg.get("content", [])

        # Collect text blocks
        for block in content_blocks:
            if "text" in block:
                final_text += block["text"]

        # No tool calls → done
        if stop_reason == "end_turn" or not any("toolUse" in b for b in content_blocks):
            console.print(f"[green]Bedrock finished after {turn + 1} turn(s)[/green]")
            break

        # Append assistant turn to conversation
        messages.append({"role": "assistant", "content": content_blocks})

        # Execute all tool calls in this turn
        tool_results = []
        for block in content_blocks:
            if "toolUse" not in block:
                continue

            tool_use = block["toolUse"]
            tool_name = tool_use["name"]
            tool_input = tool_use.get("input", {})
            tool_use_id = tool_use["toolUseId"]

            trace_line = f"[TOOL CALL] {tool_name}({json.dumps(tool_input)[:120]})"
            trace_lines.append(trace_line)
            console.print(f"[cyan]{trace_line}[/cyan]")
            steps.append({
                "icon": "T",
                "label": f"Tool: {tool_name}",
                "detail": ", ".join(f"{k}={str(v)[:60]}" for k, v in tool_input.items()),
                "status": "ok",
            })

            # Execute the tool
            fn = tool_map.get(tool_name)
            if fn is None:
                result_content = [{"text": f"Error: unknown tool '{tool_name}'"}]
            else:
                try:
                    result = await fn(**tool_input)
                    if isinstance(result, (dict, list)):
                        result_text = json.dumps(result, default=str)[:4000]
                    else:
                        result_text = str(result)[:4000]
                    result_content = [{"text": result_text}]
                    trace_lines.append(f"[TOOL RESULT] {tool_name}: {result_text[:200]}")
                    steps.append({
                        "icon": "OK",
                        "label": f"Result: {tool_name}",
                        "detail": f"{len(result_text)} chars",
                        "status": "ok",
                    })
                except Exception as e:
                    err_msg = f"Tool {tool_name} error: {e}"
                    console.print(f"[red]{err_msg}[/red]")
                    result_content = [{"text": err_msg}]
                    steps.append({"icon": "X", "label": err_msg, "detail": str(e), "status": "error"})

            tool_results.append({
                "toolUseId": tool_use_id,
                "content": result_content,
            })

        # Feed tool results back to Claude
        messages.append({
            "role": "user",
            "content": [{"toolResult": tr} for tr in tool_results],
        })

    return final_text.strip()
