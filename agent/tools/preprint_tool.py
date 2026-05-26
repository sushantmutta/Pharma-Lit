import asyncio
import httpx
from datetime import datetime, timedelta
from rich.console import Console

console = Console()

async def search_preprints(query: str, days_back: int = 180, max_results: int = 10) -> list[dict]:
    """
    Searches bioRxiv and medRxiv for recent preprints on a disease/target area via Europe PMC.
    Use this to find cutting-edge research not yet peer-reviewed — preprints often appear
    6-12 months before journal publication. Returns a list of preprints with metadata.
    Tag all preprint findings as [PREPRINT - not peer reviewed] in your output.
    """
    console.print(f"[cyan]Searching preprints for:[/cyan] {query}")

    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    search_query = f"({query}) SRC:PPR FIRST_PDATE:[{cutoff_date} TO *]"

    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": search_query,
        "resulttype": "lite",
        "format": "json",
        "pageSize": max_results,
        "sort": "P_PDATE_D desc",  # newest first
        "cursorMark": "*",
        "synonym": "true",
    }

    results = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            data = response.json()

        items = data.get("resultList", {}).get("result", [])
        for item in items:
            preprint = {
                "pmid": item.get("id", "N/A"),
                "title": item.get("title", "N/A"),
                "authors": item.get("authorString", ""),
                "journal": item.get("source", "N/A"),  # BIORXIV or MEDRXIV
                "date": item.get("firstPublicationDate", "N/A"),
                "abstract": item.get("abstractText", ""),
                "doi": item.get("doi", "N/A"),
                "source": "preprint",
                "server": item.get("source", "Unknown"),
            }
            results.append(preprint)
            safe_title = preprint['title'][:80].encode('ascii', errors='replace').decode('ascii')
            console.print(
                f"[dim][PREPRINT][/dim] {preprint['server']}: {safe_title}..."
            )

        console.print(f"[green]Found {len(results)} preprints[/green]")
    except Exception as e:
        console.print(f"[yellow]Preprint search failed: {e}[/yellow]")

    return results


# No FunctionTool wrapper needed — BedrockAgent uses the raw async function directly
