"""
run.py
PharmaLit MVP — launcher

Usage:
    python run.py --api          # Launch FastAPI backend (serves frontend at http://localhost:8000)
    python run.py --api --port 8080   # Custom port
    python run.py --demo         # (legacy) print demo info
    python run.py --help         # show help
"""
import argparse
import subprocess
import os
import sys
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()
console = Console()

ROOT = os.path.dirname(os.path.abspath(__file__))


def start_api(port: int = 8000, reload: bool = True):
    """Launch FastAPI + uvicorn. Serves both API and frontend at same port."""
    console.print(f"\n[bold cyan]PharmaLit MVP — FastAPI[/bold cyan]")
    console.print(f"[green]> API + Frontend:[/green] http://localhost:{port}")
    console.print(f"[green]> API docs:[/green]      http://localhost:{port}/docs")
    console.print(f"[green]> Health check:[/green]  http://localhost:{port}/api/health")
    console.print(f"\n[dim]Press Ctrl+C to stop[/dim]\n")

    # Check uvicorn is installed
    try:
        import uvicorn
    except ImportError:
        console.print("[red]uvicorn not found. Run: pip install uvicorn[standard][/red]")
        sys.exit(1)

    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        reload=reload,
        reload_dirs=[ROOT] if reload else None,
    )


def main():
    parser = argparse.ArgumentParser(
        description="PharmaLit MVP launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py --api              Start FastAPI on port 8000
  python run.py --api --port 8080  Start on custom port
  python run.py --no-reload        Start without auto-reload
  python run.py --check            Run API health check
        """
    )
    parser.add_argument("--api",      action="store_true", help="Launch FastAPI backend (default mode)")
    parser.add_argument("--port",     type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--no-reload",action="store_true", help="Disable auto-reload on file changes")
    parser.add_argument("--check",    action="store_true", help="Run API health check and exit")
    parser.add_argument("--demo",     action="store_true", help="(Legacy) Print demo info")
    args = parser.parse_args()

    if args.check:
        import asyncio
        from check_apis import main as check_main
        asyncio.run(check_main())
        return

    if args.demo:
        console.print("[yellow]Demo mode not available in MVP — use: python run.py --api[/yellow]")
        return

    # Default: always start API
    start_api(port=args.port, reload=not args.no_reload)


if __name__ == "__main__":
    main()