import asyncio
import httpx
from google.adk.tools import FunctionTool
from rich.console import Console

console = Console()

# Common non-gene acronyms to skip during any upstream gene validation
_NON_GENE_ACRONYMS = {
    "NASH", "NSCLC", "FDA", "DNA", "RNA", "mRNA", "PCR", "HIV", "COVID",
    "ICU", "BMI", "LDL", "HDL", "ECG", "MRI", "CT", "PET", "IND", "NDA",
    "ADME", "PK", "PD", "GLP", "GMP", "CRO", "CMO", "API", "IND",
    "ANDA", "BLA", "MAA", "EMA", "WHO", "NIH", "CDC", "AHA", "ACC",
    "NAFLD", "MASLD", "CVD", "T2D", "HCC", "CKD", "IBD", "SLE", "RA",
}


async def _resolve_ensembl_id(gene_symbol: str) -> str | None:
    """Resolve gene symbol → Ensembl ID via MyGene.info (no API key required)."""
    try:
        url = f"https://mygene.info/v3/query?q=symbol:{gene_symbol}&species=human&fields=ensembl.gene&size=1"
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url)
        data = resp.json()
        hits = data.get("hits", [])
        if hits:
            ensembl = hits[0].get("ensembl")
            if isinstance(ensembl, list):
                ensembl = ensembl[0]
            if isinstance(ensembl, dict):
                return ensembl.get("gene")
    except Exception as e:
        console.print(f"[yellow]MyGene.info lookup failed for {gene_symbol}: {e}[/yellow]")
    return None


async def _query_open_targets_by_symbol(gene_symbol: str) -> dict:
    """Text-search OT by gene symbol. Returns tractability dict + ensembl id."""
    ot_url = "https://api.platform.opentargets.org/api/v4/graphql"
    query = """
    query targetSearch($queryString: String!) {
        search(queryString: $queryString, entityNames: ["target"]) {
            hits {
                id
                name
                tractability {
                    smallmolecule {
                        buckets
                        highQualityMols
                        topBucket
                    }
                    antibody {
                        buckets
                        highQualityMols
                        topBucket
                    }
                }
            }
        }
    }
    """
    async with httpx.AsyncClient(timeout=12.0) as client:
        resp = await client.post(ot_url, json={"query": query, "variables": {"queryString": gene_symbol}})
    data = resp.json()
    hits = data.get("data", {}).get("search", {}).get("hits", [])
    if hits:
        return {"ensembl_id": hits[0].get("id", ""), "tractability": hits[0].get("tractability") or {}}
    return {}


async def _query_open_targets_by_ensembl(ensembl_id: str) -> dict:
    """Direct OT lookup by Ensembl ID — more reliable than text search for genes like PCSK9."""
    ot_url = "https://api.platform.opentargets.org/api/v4/graphql"
    query = """
    query targetById($ensemblId: String!) {
        target(ensemblId: $ensemblId) {
            id
            approvedSymbol
            tractability {
                smallmolecule {
                    buckets
                    highQualityMols
                    topBucket
                }
                antibody {
                    buckets
                    highQualityMols
                    topBucket
                }
            }
        }
    }
    """
    async with httpx.AsyncClient(timeout=12.0) as client:
        resp = await client.post(ot_url, json={"query": query, "variables": {"ensemblId": ensembl_id}})
    data = resp.json()
    target = data.get("data", {}).get("target")
    if target:
        return {"ensembl_id": ensembl_id, "tractability": target.get("tractability") or {}}
    return {}


async def _query_uniprot(gene_symbol: str) -> dict:
    """Query UniProt for human protein entry (organism_id:9606)."""
    url = (
        f"https://rest.uniprot.org/uniprotkb/search"
        f"?query=gene_exact:{gene_symbol}+AND+organism_id:9606"
        f"&format=json&size=1"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
    data = resp.json()
    results = data.get("results", [])
    if results:
        protein = results[0]
        uniprot_id = protein.get("primaryAccession", "Unknown")
        func_text = ""
        for comment in protein.get("comments", []):
            if comment.get("commentType") == "FUNCTION":
                texts = comment.get("texts", [])
                if texts:
                    func_text = texts[0].get("value", "")[:300]
                    break
        return {"uniprot_id": uniprot_id, "protein_function": func_text}
    return {}


def _compute_tractability_score(tractability: dict) -> tuple[int, str, list[dict]]:
    """
    Returns (points, tractability_label, breakdown_entries).
    Breakdown entries: [{label, points, source, detail}]
    """
    sm = tractability.get("smallmolecule") or {}
    ab = tractability.get("antibody") or {}

    sm_buckets = sm.get("buckets") or []
    ab_buckets = ab.get("buckets") or []
    sm_hq = sm.get("highQualityMols") or 0
    sm_top = sm.get("topBucket") or 99

    breakdown = []
    total = 0

    if sm_buckets and any(sm_buckets):
        label = "Small Molecule Druggable"
        if sm_top <= 2:
            pts = 5
            detail = f"Bucket {sm_top} — clinical drugs exist (strongest precedent)"
        elif sm_top <= 4:
            pts = 4
            detail = f"Bucket {sm_top} — preclinical/Phase 1-2 precedent"
        else:
            pts = 2
            detail = f"Bucket {sm_top} — weak precedent (bucket >4)"
        breakdown.append({"label": "OT Small Molecule Tractability", "points": pts, "source": "Open Targets", "detail": detail})
        total += pts

        if sm_hq > 0:
            breakdown.append({"label": "High Quality Molecules Bonus", "points": 2, "source": "Open Targets", "detail": f"{sm_hq} high-quality molecules in OT"})
            total += 2

    elif ab_buckets and any(ab_buckets):
        label = "Antibody Druggable"
        ab_top = ab.get("topBucket") or 99
        breakdown.append({"label": "OT Antibody Tractability", "points": 3, "source": "Open Targets", "detail": f"Antibody bucket {ab_top}"})
        total += 3

    else:
        label = "Undruggable / Unknown"
        breakdown.append({"label": "OT Tractability", "points": 0, "source": "Open Targets", "detail": "No tractability buckets found in Open Targets"})

    ot_score_str = f"Bucket {sm_top} (lower = more druggable)" if sm_buckets and any(sm_buckets) else "No SM bucket"
    return total, label, breakdown, ot_score_str


async def score_target_async(target_gene: str, disease: str) -> dict:
    """
    Async version: scores a candidate target gene using Open Targets + UniProt.
    Returns full payload with breakdown list for transparent scoring.
    """
    if target_gene.upper() in _NON_GENE_ACRONYMS:
        return {
            "gene": target_gene, "score": 1, "score_raw": 0,
            "ot_score": "Skipped — not a gene symbol",
            "tractability": "Unknown", "uniprot_id": "Unknown",
            "protein_function": "Unknown",
            "breakdown": [{"label": "Skipped", "points": 0, "source": "Filter", "detail": "Common non-gene acronym"}]
        }

    console.print(f"[cyan]Scoring target:[/cyan] {target_gene} for {disease}")

    # Run OT (symbol) + UniProt concurrently
    ot_result, uniprot_result = await asyncio.gather(
        _query_open_targets_by_symbol(target_gene),
        _query_uniprot(target_gene),
        return_exceptions=True
    )

    # Handle exceptions from gather
    if isinstance(ot_result, Exception):
        console.print(f"[yellow]OT symbol search failed: {ot_result}[/yellow]")
        ot_result = {}
    if isinstance(uniprot_result, Exception):
        console.print(f"[yellow]UniProt lookup failed: {uniprot_result}[/yellow]")
        uniprot_result = {}

    tractability = ot_result.get("tractability", {})
    sm_buckets = (tractability.get("smallmolecule") or {}).get("buckets") or []
    ab_buckets = (tractability.get("antibody") or {}).get("buckets") or []
    has_tractability = bool(sm_buckets and any(sm_buckets)) or bool(ab_buckets and any(ab_buckets))

    # Ensembl ID fallback if text search had no tractability
    if not has_tractability:
        console.print(f"[yellow]No OT tractability via symbol search for {target_gene} — trying Ensembl ID fallback[/yellow]")
        ensembl_id = ot_result.get("ensembl_id") or await _resolve_ensembl_id(target_gene)
        if ensembl_id:
            ot_by_id = await _query_open_targets_by_ensembl(ensembl_id)
            if isinstance(ot_by_id, dict) and ot_by_id.get("tractability"):
                tractability = ot_by_id["tractability"]
                ot_result["ensembl_id"] = ensembl_id
                console.print(f"[green]Ensembl fallback succeeded for {target_gene} ({ensembl_id})[/green]")

    # Compute tractability score + breakdown
    ot_pts, tractability_label, breakdown, ot_score_str = _compute_tractability_score(tractability)

    # UniProt scoring
    uniprot_id = uniprot_result.get("uniprot_id", "Unknown")
    protein_function = uniprot_result.get("protein_function", "Unknown")
    uniprot_pts = 0

    if uniprot_id and uniprot_id != "Unknown":
        uniprot_pts += 2
        breakdown.append({"label": "UniProt Entry", "points": 2, "source": "UniProt", "detail": f"Validated human protein entry: {uniprot_id}"})
        if protein_function and protein_function != "Unknown":
            uniprot_pts += 1
            breakdown.append({"label": "Functional Annotation", "points": 1, "source": "UniProt", "detail": protein_function[:120] + "..."})
    else:
        breakdown.append({"label": "UniProt Entry", "points": 0, "source": "UniProt", "detail": "No human protein entry found"})

    score_raw = ot_pts + uniprot_pts
    score_final = max(1, min(10, score_raw)) if score_raw > 0 else 1

    if score_raw == 0:
        breakdown.append({"label": "Baseline Score", "points": 1, "source": "Pipeline", "detail": "Minimum score assigned — no evidence found in OT or UniProt"})

    result = {
        "gene": target_gene,
        "score": score_final,
        "score_raw": score_raw,
        "ot_score": ot_score_str,
        "tractability": tractability_label,
        "uniprot_id": uniprot_id,
        "protein_function": protein_function,
        "breakdown": breakdown,
        "ensembl_id": ot_result.get("ensembl_id", ""),
    }

    console.print(f"[green]Score for {target_gene}:[/green] {score_final}/10 (raw={score_raw}, OT={ot_pts}, UniProt={uniprot_pts})")
    return result


def score_target(target_gene: str, disease: str) -> dict:
    """
    Sync wrapper for ADK FunctionTool compatibility.
    Scores a candidate target gene using Open Targets + UniProt.
    Returns a score from 1-10 with full breakdown for transparent scoring.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're inside an async context (ADK agent) — use run_in_executor workaround
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, score_target_async(target_gene, disease))
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(score_target_async(target_gene, disease))
    except Exception as e:
        console.print(f"[red]score_target failed for {target_gene}: {e}[/red]")
        return {
            "gene": target_gene, "score": 1, "score_raw": 0,
            "ot_score": "Error", "tractability": "Unknown",
            "uniprot_id": "Unknown", "protein_function": "Unknown",
            "breakdown": [{"label": "Error", "points": 0, "source": "Pipeline", "detail": str(e)}],
        }


score_target_tool = FunctionTool(func=score_target)
