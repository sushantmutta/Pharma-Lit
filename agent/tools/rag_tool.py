from rag.retriever import search_rag as internal_search_rag
from rich.console import Console

console = Console()

async def search_rag(query: str, n_results: int = 5) -> list:
    """
    Searches the internal knowledge base (ChromaDB) for specific mechanistic details
    or findings from previously ingested papers and internal docs.
    """
    console.print(f"[cyan]Searching internal RAG KB for:[/cyan] {query}")
    results = internal_search_rag(query, n_results=n_results)
    for r in results:
        console.print(f"[dim]RAG match:[/dim] {r['title']} (Score: {r['score']})")
    return results

# No FunctionTool wrapper needed — BedrockAgent uses the raw async function directly
