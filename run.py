import argparse
import subprocess
import os
import time
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()
console = Console()

# Streamlit executable
_VENV_STREAMLIT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    ".venv",
    "Scripts",
    "streamlit.exe"
)

STREAMLIT_CMD = (
    _VENV_STREAMLIT
    if os.path.exists(_VENV_STREAMLIT)
    else "streamlit"
)

# -----------------------------
# Backend Init
# -----------------------------
def start_backend():
    console.print(
        "[bold cyan][BACKEND] Backend services initialized[/bold cyan]"
    )

    # Add:
    # - DB connections
    # - Chroma initialization
    # - model loading
    # - cache init
    # here if needed


# -----------------------------
# UI Startup
# -----------------------------
def start_ui():
    console.print(
        "[bold magenta][UI] Launching Streamlit UI[/bold magenta]"
    )

    subprocess.Popen([
        STREAMLIT_CMD,
        "run",
        "ui/app.py",
        "--server.fileWatcherType=none"
    ])


# -----------------------------
# Main
# -----------------------------
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--skip-backend",
        action="store_true",
        help="Launch only UI"
    )

    args = parser.parse_args()

    try:
        # Initialize backend
        if not args.skip_backend:
            start_backend()

        # Launch UI
        start_ui()

        console.print(
            "[bold green][READY] Pharma R&D Agent Running[/bold green]"
        )

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        console.print(
            "\n[red]Shutting down system...[/red]"
        )


if __name__ == "__main__":
    main()