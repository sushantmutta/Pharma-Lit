"""
rag/embeddings.py
Shared, lazy-loaded SentenceTransformer instance.

Importing this module does NOT load the model into memory.
The model is loaded only on the first call to get_embedding_model(),
then cached for the process lifetime. This prevents double-loading
when both ingestor.py and retriever.py are imported at startup.
"""
from __future__ import annotations
from rich.console import Console

console = Console()

_model = None


def get_embedding_model():
    """
    Returns the shared SentenceTransformer instance, loading it on first call.
    Thread-safe for single-process usage (FastAPI runs async, not threaded).
    """
    global _model
    if _model is None:
        console.print("[dim]Loading embedding model (all-MiniLM-L6-v2)...[/dim]")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        console.print("[dim]Embedding model loaded.[/dim]")
    return _model
