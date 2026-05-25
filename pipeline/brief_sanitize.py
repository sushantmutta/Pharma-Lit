"""
pipeline/brief_sanitize.py
Strips chatbot epilogue patterns from LLM-generated hypothesis briefs.
Ensures output ends cleanly after the Citations section.
"""
import re
from rich.console import Console

console = Console()

# Patterns that signal chatbot-style follow-up questions / meta-commentary
_CHATBOT_PATTERNS = [
    r"would you like (me|us) to",
    r"should i (focus|elaborate|explore|investigate|provide|look|discuss)",
    r"do you (want|need|have|wish)",
    r"let me know if",
    r"feel free to",
    r"i (can|could|would) (also|be happy to|further|provide)",
    r"is there anything (else|specific|more)",
    r"if you('d| would) like",
    r"please (let me|feel free|note that you can)",
    r"shall i",
    r"i hope this",
    r"i trust this",
    r"this (report|brief|analysis|summary) (should|provides|covers)",
    r"please (don't hesitate|reach out)",
    r"happy to (help|assist|elaborate|provide)",
    r"any (questions|feedback|clarifications)",
]

_CHATBOT_RE = re.compile(
    "|".join(_CHATBOT_PATTERNS),
    flags=re.IGNORECASE | re.MULTILINE,
)

# Marks the end of the structured brief
_CITATIONS_END_PATTERN = re.compile(
    r"(##\s*citations?.*?)(?=\n##|\Z)",
    flags=re.IGNORECASE | re.DOTALL,
)


def sanitize_brief(text: str) -> str:
    """
    Strips chatbot follow-up epilogues from an LLM-generated brief.
    Truncates cleanly after the Citations section if chatbot text follows.

    Args:
        text: Raw LLM output string (markdown format).

    Returns:
        Cleaned markdown string suitable for display.
    """
    if not text:
        return text

    original_length = len(text)

    # Split into lines and filter out chatbot epilogue lines
    lines = text.split("\n")
    clean_lines = []
    in_citations = False
    citations_ended = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track when we're inside the Citations section
        if re.match(r"^##\s*citations?", stripped, re.IGNORECASE):
            in_citations = True
            citations_ended = False
            clean_lines.append(line)
            continue

        # After citations, detect a new top-level section (another ##)
        if in_citations and re.match(r"^##", stripped) and not re.match(r"^##\s*citations?", stripped, re.IGNORECASE):
            # A new section after citations — likely chatbot append, stop here
            citations_ended = True
            break

        # Check if this line contains chatbot follow-up patterns
        if _CHATBOT_RE.search(stripped):
            # If we're past the main sections, stop entirely
            # If we're in the middle of the brief, skip just this line
            if in_citations or i > len(lines) // 2:
                console.print(f"[yellow]Sanitize: truncating at chatbot line:[/yellow] {stripped[:80]}")
                break
            else:
                console.print(f"[dim]Sanitize: skipped mid-brief chatbot line:[/dim] {stripped[:80]}")
                continue

        clean_lines.append(line)

    result = "\n".join(clean_lines).rstrip()

    # Remove trailing incomplete sentences (ends without . ? ! or ``` block close)
    # Only trim if the last line is very short and doesn't end with punctuation
    result_lines = result.split("\n")
    while result_lines:
        last = result_lines[-1].strip()
        if last and not last.endswith((".", "?", "!", "```", "---", "*", "]")):
            if len(last) < 60 and not last.startswith("#") and not last.startswith("-"):
                result_lines.pop()
                continue
        break
    result = "\n".join(result_lines).rstrip()

    delta = original_length - len(result)
    if delta > 0:
        console.print(f"[green]Sanitize:[/green] removed {delta} chars of chatbot epilogue from brief.")

    return result
