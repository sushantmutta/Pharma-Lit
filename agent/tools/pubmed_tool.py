import asyncio
import json
from datetime import datetime, timedelta
from google.adk.tools import FunctionTool
from biomcp.articles.search import search_articles, PubmedRequest
from rich.console import Console

console = Console()

async def search_pubmed(query: str, days_back: int = 7, max_results: int = 20) -> list[dict]:
    """
    Searches PubMed for recent biomedical papers. Use this to find the latest research on a disease or target. Returns a list of papers with abstracts.
    """
    console.print(f"[cyan]Searching PubMed for:[/cyan] {query}")
    
    request = PubmedRequest(keywords=[query])
    retries = 3
    results = []
    
    for attempt in range(retries):
        try:
            raw_results_str = await search_articles(request=request, limit=max_results, output_json=True)
            try:
                raw_results = json.loads(raw_results_str)
            except Exception:
                return [{"abstract": raw_results_str}]
            
            if isinstance(raw_results, dict) and "results" in raw_results:
                raw_results = raw_results["results"]
            elif isinstance(raw_results, dict) and "items" in raw_results:
                raw_results = raw_results["items"]
                
            for item in raw_results:
                if not isinstance(item, dict): continue
                paper = {
                    "pmid": item.get("pmid", "N/A"),
                    "title": item.get("title", "N/A"),
                    "authors": item.get("authors", []),
                    "journal": item.get("journal", "N/A"),
                    "date": item.get("date", "N/A"),
                    "abstract": item.get("abstract", ""),
                    "doi": item.get("doi", "N/A")
                }
                results.append(paper)
                safe_title = paper['title'].encode('ascii', errors='replace').decode('ascii')
                console.print(f"[dim]Found:[/dim] {safe_title}")
                
            return results
        except Exception as e:
            console.print(f"[yellow]PubMed search failed: {e}[/yellow]")
            await asyncio.sleep(2 ** attempt)
            
    return []

pubmed_search_tool = FunctionTool(func=search_pubmed)
