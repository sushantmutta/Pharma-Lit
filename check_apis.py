"""
check_apis.py
PharmaLit MVP — API Health Check Script

Smoke-tests all external APIs used by the pipeline.
No API keys required for Open Targets, UniProt, Europe PMC, or ClinicalTrials.gov.
GOOGLE_API_KEY is checked in .env but not called here.
NCBI_API_KEY is optional (improves PubMed rate limits).

Usage:
    python check_apis.py
"""
import asyncio
import time
import os
import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()
console = Console()


async def check_open_targets() -> dict:
    """Test Open Targets GraphQL — search for PCSK9."""
    name = "Open Targets (GraphQL)"
    url = "https://api.platform.opentargets.org/api/v4/graphql"
    query = """
    query { search(queryString: "PCSK9", entityNames: ["target"]) {
        hits { id name }
    }}
    """
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(url, json={"query": query})
        hits = resp.json().get("data", {}).get("search", {}).get("hits", [])
        latency = int((time.time() - t0) * 1000)
        if hits:
            return {"name": name, "status": "PASS", "latency_ms": latency, "detail": f"{len(hits)} hits for PCSK9"}
        return {"name": name, "status": "WARN", "latency_ms": latency, "detail": "No hits returned for PCSK9"}
    except Exception as e:
        return {"name": name, "status": "FAIL", "latency_ms": int((time.time() - t0)*1000), "detail": str(e)}


async def check_uniprot() -> dict:
    """Test UniProt REST — human PCSK9."""
    name = "UniProt (REST)"
    url = "https://rest.uniprot.org/uniprotkb/search?query=gene_exact:PCSK9+AND+organism_id:9606&format=json&size=1"
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
        results = resp.json().get("results", [])
        latency = int((time.time() - t0) * 1000)
        if results:
            uid = results[0].get("primaryAccession", "?")
            return {"name": name, "status": "PASS", "latency_ms": latency, "detail": f"PCSK9 → {uid}"}
        return {"name": name, "status": "WARN", "latency_ms": latency, "detail": "No results for PCSK9 human"}
    except Exception as e:
        return {"name": name, "status": "FAIL", "latency_ms": int((time.time() - t0)*1000), "detail": str(e)}


async def check_mygene() -> dict:
    """Test MyGene.info — PCSK9 Ensembl ID resolution."""
    name = "MyGene.info (Ensembl fallback)"
    url = "https://mygene.info/v3/query?q=symbol:PCSK9&species=human&fields=ensembl.gene&size=1"
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url)
        hits = resp.json().get("hits", [])
        latency = int((time.time() - t0) * 1000)
        if hits:
            ensembl = hits[0].get("ensembl", {})
            if isinstance(ensembl, list):
                ensembl = ensembl[0]
            eid = ensembl.get("gene", "?") if isinstance(ensembl, dict) else "?"
            return {"name": name, "status": "PASS", "latency_ms": latency, "detail": f"PCSK9 → {eid}"}
        return {"name": name, "status": "WARN", "latency_ms": latency, "detail": "No hits for PCSK9"}
    except Exception as e:
        return {"name": name, "status": "FAIL", "latency_ms": int((time.time() - t0)*1000), "detail": str(e)}


async def check_europe_pmc() -> dict:
    """Test Europe PMC — preprint search."""
    name = "Europe PMC (preprints)"
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {"query": "NASH SRC:PPR", "resulttype": "lite", "format": "json", "pageSize": "3"}
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(url, params=params)
        items = resp.json().get("resultList", {}).get("result", [])
        latency = int((time.time() - t0) * 1000)
        return {"name": name, "status": "PASS", "latency_ms": latency, "detail": f"{len(items)} preprints returned"}
    except Exception as e:
        return {"name": name, "status": "FAIL", "latency_ms": int((time.time() - t0)*1000), "detail": str(e)}


async def check_pubmed_biomcp() -> dict:
    """Test PubMed via BioMCP."""
    name = "PubMed (BioMCP)"
    t0 = time.time()
    try:
        from biomcp.articles.search import search_articles, PubmedRequest
        import json as _json
        req = PubmedRequest(keywords=["NASH drug target"])
        raw = await search_articles(request=req, limit=3, output_json=True)
        latency = int((time.time() - t0) * 1000)
        try:
            data = _json.loads(raw)
            if isinstance(data, dict):
                results = data.get("results", data.get("items", []))
            else:
                results = data if isinstance(data, list) else []
            count = len(results)
        except Exception:
            count = 1 if raw else 0
        status = "PASS" if count > 0 else "WARN"
        return {"name": name, "status": status, "latency_ms": latency, "detail": f"{count} papers returned"}
    except Exception as e:
        return {"name": name, "status": "FAIL", "latency_ms": int((time.time() - t0)*1000), "detail": str(e)}


async def check_clinicaltrials_biomcp() -> dict:
    """Test ClinicalTrials.gov via BioMCP."""
    name = "ClinicalTrials.gov (BioMCP)"
    t0 = time.time()
    try:
        from biomcp.trials.search import search_trials, TrialQuery
        import json as _json
        req = TrialQuery(conditions=["NASH"])
        raw = await search_trials(query=req, output_json=True)
        latency = int((time.time() - t0) * 1000)
        try:
            data = _json.loads(raw)
            if isinstance(data, dict):
                results = data.get("studies", data.get("results", []))
            else:
                results = data if isinstance(data, list) else []
            count = len(results)
        except Exception:
            count = 1 if raw else 0
        status = "PASS" if count > 0 else "WARN"
        return {"name": name, "status": status, "latency_ms": latency, "detail": f"{count} trials returned"}
    except Exception as e:
        return {"name": name, "status": "FAIL", "latency_ms": int((time.time() - t0)*1000), "detail": str(e)}


def check_env_keys() -> list[dict]:
    """Check environment variables."""
    results = []
    google_key = os.getenv("GOOGLE_API_KEY", "")
    results.append({
        "name": "GOOGLE_API_KEY (.env)",
        "status": "PASS" if google_key else "WARN",
        "latency_ms": 0,
        "detail": f"Set ({len(google_key)} chars)" if google_key else "Not set — Gemini will fail"
    })
    ncbi_key = os.getenv("NCBI_API_KEY", "")
    results.append({
        "name": "NCBI_API_KEY (.env)",
        "status": "PASS" if ncbi_key else "INFO",
        "latency_ms": 0,
        "detail": "Set (higher PubMed rate limits)" if ncbi_key else "Not set — optional, default rate limits apply"
    })
    return results


STATUS_ICONS = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌", "INFO": "ℹ️ "}
STATUS_STYLES = {"PASS": "green", "WARN": "yellow", "FAIL": "red", "INFO": "cyan"}


async def main():
    console.print("\n[bold cyan]PharmaLit API Health Check[/bold cyan]\n")

    # Run all async checks concurrently
    api_results = await asyncio.gather(
        check_open_targets(),
        check_uniprot(),
        check_mygene(),
        check_europe_pmc(),
        check_pubmed_biomcp(),
        check_clinicaltrials_biomcp(),
    )

    env_results = check_env_keys()
    all_results = list(api_results) + env_results

    # Build rich table
    table = Table(title="API Health Status", show_header=True, header_style="bold magenta")
    table.add_column("Status", width=6)
    table.add_column("Service", width=35)
    table.add_column("Latency", width=10, justify="right")
    table.add_column("Detail")

    for r in all_results:
        icon = STATUS_ICONS.get(r["status"], "•")
        style = STATUS_STYLES.get(r["status"], "white")
        latency = f"{r['latency_ms']}ms" if r["latency_ms"] > 0 else "—"
        table.add_row(icon, r["name"], latency, r["detail"], style=style)

    console.print(table)

    fails = [r for r in all_results if r["status"] == "FAIL"]
    warns = [r for r in all_results if r["status"] == "WARN"]
    passes = [r for r in all_results if r["status"] == "PASS"]

    console.print(f"\n[green]PASS: {len(passes)}[/green]  [yellow]WARN: {len(warns)}[/yellow]  [red]FAIL: {len(fails)}[/red]\n")

    if fails:
        console.print("[red]Action required:[/red] Fix FAIL items before running the pipeline.")
    elif warns:
        console.print("[yellow]Pipeline may run with degraded results. Review WARN items.[/yellow]")
    else:
        console.print("[bold green]All systems go! ✓[/bold green]")


if __name__ == "__main__":
    asyncio.run(main())
