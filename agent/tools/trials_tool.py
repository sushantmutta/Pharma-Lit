import asyncio
import json
from google.adk.tools import FunctionTool
from biomcp.trials.search import search_trials, TrialQuery
from rich.console import Console

console = Console()

async def search_clinical_trials(condition: str, intervention: str = "", status: str = "RECRUITING,ACTIVE_NOT_RECRUITING") -> list[dict]:
    """
    Searches ClinicalTrials.gov to find active or recruiting trials for a given disease and optional target intervention. Checks clinical precedence.
    """
    console.print(f"[cyan]Searching Clinical Trials for condition:[/cyan] {condition} [cyan]intervention:[/cyan] {intervention}")
    
    request = TrialQuery(
        conditions=[condition],
        interventions=[intervention] if intervention else None
    )
    try:
        raw_results_str = await search_trials(query=request, output_json=True)
        results = []
        try:
            raw_results = json.loads(raw_results_str)
        except:
            return [{"result": raw_results_str}]
            
        if isinstance(raw_results, dict) and "studies" in raw_results:
            raw_results = raw_results["studies"]
        elif isinstance(raw_results, dict) and "results" in raw_results:
            raw_results = raw_results["results"]
            
        for item in raw_results:
            if not isinstance(item, dict): continue
            trial = {
                "nct_id": item.get("NCT Number", "N/A"),
                "title": item.get("Study Title", "N/A"),
                "phase": item.get("Phases", "N/A"),
                "status": item.get("Study Status", "N/A"),
                "sponsor": item.get("Sponsor", "N/A"),
                "conditions": item.get("Conditions", "N/A"),
                "interventions": item.get("Interventions", "N/A"),
                "start_date": item.get("Start Date", "N/A"),
                "url": item.get("Study URL", ""),
            }
            results.append(trial)
            safe_title = trial['title'][:60].encode('ascii', errors='replace').decode('ascii')
            console.print(f"[dim]Found Trial:[/dim] {trial['nct_id']} - {safe_title}")
            
        return results
    except Exception as e:
        console.print(f"[red]Error searching clinical trials: {e}[/red]")
        return []

trials_search_tool = FunctionTool(func=search_clinical_trials)
