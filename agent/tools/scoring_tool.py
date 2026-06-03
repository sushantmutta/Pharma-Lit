"""
agent/tools/scoring_tool.py

Scores a drug target using two free public databases:
  - Open Targets  → tells us if any drugs already exist for this protein
  - UniProt       → confirms the protein is real and well-characterised in humans

All scoring labels use plain English — no pharma jargon.
"""
import asyncio
import httpx
from rich.console import Console

console = Console()

# Acronyms that should never be treated as gene/protein symbols
_NON_GENE_ACRONYMS = {
    "NASH", "NSCLC", "FDA", "DNA", "RNA", "MRNA", "PCR", "HIV", "COVID",
    "ICU", "BMI", "LDL", "HDL", "ECG", "MRI", "CT", "PET", "IND", "NDA",
    "ADME", "PK", "PD", "GLP", "GMP", "CRO", "CMO", "API",
    "ANDA", "BLA", "MAA", "EMA", "WHO", "NIH", "CDC", "AHA", "ACC",
    "NAFLD", "MASLD", "CVD", "T2D", "HCC", "CKD", "IBD", "SLE", "RA",
}


# ── Database Query Functions ───────────────────────────────────────────────────

async def _resolve_ensembl_id(gene_symbol: str) -> str | None:
    """Resolve gene symbol → Ensembl ID via MyGene.info (free, no API key)."""
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
    """
    Query Open Targets by gene symbol.
    Open Targets is a public database that tracks which proteins have drugs
    or drug candidates targeting them, and how 'druggable' they are.
    """
    ot_url = "https://api.platform.opentargets.org/api/v4/graphql"
    query = """
    query targetSearch($queryString: String!) {
        search(queryString: $queryString, entityNames: ["target"]) {
            hits {
                id
                name
                tractability {
                    label
                    modality
                    value
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
    """Direct Open Targets lookup by Ensembl gene ID — more reliable than text search."""
    ot_url = "https://api.platform.opentargets.org/api/v4/graphql"
    query = """
    query targetById($ensemblId: String!) {
        target(ensemblId: $ensemblId) {
            id
            approvedSymbol
            tractability {
                label
                modality
                value
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
    """
    Query UniProt for this protein's human entry.
    UniProt is the gold-standard protein database — if a protein has a
    well-documented UniProt entry it confirms the target is real and
    well-characterised in human biology.
    """
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


# ── Plain-English Score Computation ───────────────────────────────────────────

def _compute_tractability_score(tractability: list) -> tuple[int, str, list[dict], str]:
    """
    Converts Open Targets druggability data into a score with plain-English labels.
    """
    breakdown = []
    total = 0
    
    if not isinstance(tractability, list):
        tractability = []

    sm_approved = any(t.get("label") == "Approved Drug" and t.get("modality") == "SM" and t.get("value") for t in tractability)
    sm_advanced = any(t.get("label") == "Advanced Clinical" and t.get("modality") == "SM" and t.get("value") for t in tractability)
    sm_phase1 = any(t.get("label") == "Phase 1 Clinical" and t.get("modality") == "SM" and t.get("value") for t in tractability)
    sm_hq = any(t.get("label") == "High-Quality Ligand" and t.get("modality") == "SM" and t.get("value") for t in tractability)
    
    ab_approved = any(t.get("label") == "Approved Drug" and t.get("modality") == "AB" and t.get("value") for t in tractability)
    ab_advanced = any(t.get("label") == "Advanced Clinical" or t.get("label") == "Phase 1 Clinical" and t.get("modality") == "AB" and t.get("value") for t in tractability)

    is_sm = sm_approved or sm_advanced or sm_phase1
    is_ab = ab_approved or ab_advanced

    if is_sm:
        label = "Small Molecule Druggable"
        if sm_approved:
            pts = 5
            row_label = "Approved drugs already target this protein"
            row_detail = "At least one FDA/EMA-approved pill-based drug acts on this protein. This is the strongest possible confidence."
        elif sm_advanced or sm_phase1:
            pts = 4
            row_label = "Drug candidates in human clinical trials"
            row_detail = "Small-molecule drugs against this protein are currently being tested in people. Strong evidence."
        breakdown.append({"label": row_label, "points": pts, "source": "Open Targets", "detail": row_detail})
        total += pts

        if sm_hq:
            breakdown.append({
                "label": "High-quality drug candidates exist",
                "points": 2,
                "source": "Open Targets",
                "detail": "High-quality, drug-like molecules are documented in global databases for this target.",
            })
            total += 2

    elif is_ab:
        label = "Biologic / Antibody Druggable"
        if ab_approved:
            pts = 5
            row_label = "Approved biologics target this protein"
        else:
            pts = 3
            row_label = "Biologic therapies in clinical trials"
            
        breakdown.append({
            "label": row_label,
            "points": pts,
            "source": "Open Targets",
            "detail": "This protein is accessible to large-molecule drugs like monoclonal antibodies.",
        })
        total += pts

    else:
        label = "Undruggable / No precedent"
        breakdown.append({
            "label": "No drug has successfully targeted this protein yet",
            "points": 0,
            "source": "Open Targets",
            "detail": "Open Targets finds no approved drugs or clinical trials targeting this protein.",
        })

    ot_score_str = "High confidence" if (sm_approved or ab_approved) else ("Moderate confidence" if (sm_advanced or ab_advanced) else "No precedent")
    return total, label, breakdown, ot_score_str


# ── Main Scoring Function ──────────────────────────────────────────────────────

async def score_target_async(target_gene: str, disease: str) -> dict:
    """
    Score a drug target protein using Open Targets + UniProt.

    Returns a dict with:
      - gene: the protein symbol
      - score: 1–10 confidence score
      - tractability: plain-English category
      - breakdown: list of scoring reasons in plain English
      - uniprot_id, protein_function, ensembl_id: identifiers + description
    """
    if target_gene.upper() in _NON_GENE_ACRONYMS:
        return {
            "gene": target_gene, "score": 1, "score_raw": 0,
            "ot_score": "Skipped — not a protein symbol",
            "tractability": "Not a drug target",
            "uniprot_id": "N/A",
            "protein_function": "N/A",
            "breakdown": [{
                "label": "Not a protein target — skipped",
                "points": 0,
                "source": "Filter",
                "detail": "This is a disease abbreviation or acronym, not a protein that can be drugged.",
            }]
        }

    console.print(f"[cyan]Scoring target:[/cyan] {target_gene} for {disease}")

    # Query Open Targets + UniProt simultaneously (parallel)
    ot_result, uniprot_result = await asyncio.gather(
        _query_open_targets_by_symbol(target_gene),
        _query_uniprot(target_gene),
        return_exceptions=True
    )

    if isinstance(ot_result, Exception):
        console.print(f"[yellow]Open Targets lookup failed: {ot_result}[/yellow]")
        ot_result = {}
    if isinstance(uniprot_result, Exception):
        console.print(f"[yellow]UniProt lookup failed: {uniprot_result}[/yellow]")
        uniprot_result = {}

    tractability = ot_result.get("tractability", [])
    if not isinstance(tractability, list):
        tractability = []
        
    has_tractability = any(t.get("value") for t in tractability if isinstance(t, dict))

    # If symbol search found no druggability data, try Ensembl ID lookup (more reliable)
    if not has_tractability:
        console.print(f"[yellow]No druggability data for {target_gene} via name — trying gene ID lookup[/yellow]")
        ensembl_id = ot_result.get("ensembl_id") or await _resolve_ensembl_id(target_gene)
        if ensembl_id:
            ot_by_id = await _query_open_targets_by_ensembl(ensembl_id)
            if isinstance(ot_by_id, dict) and ot_by_id.get("tractability"):
                tractability = ot_by_id["tractability"]
                ot_result["ensembl_id"] = ensembl_id
                console.print(f"[green]Gene ID lookup succeeded for {target_gene} ({ensembl_id})[/green]")

    # Compute plain-English score
    ot_pts, tractability_label, breakdown, ot_score_str = _compute_tractability_score(tractability)

    # UniProt — does this protein exist and is it characterised in humans?
    uniprot_id = uniprot_result.get("uniprot_id", "Unknown")
    protein_function = uniprot_result.get("protein_function", "Unknown")
    uniprot_pts = 0

    if uniprot_id and uniprot_id != "Unknown":
        uniprot_pts += 2
        breakdown.append({
            "label": "Confirmed human protein with a UniProt database entry",
            "points": 2,
            "source": "UniProt",
            "detail": (
                f"UniProt ID: {uniprot_id} — this protein is documented in the gold-standard "
                f"human protein database, confirming it is real and relevant to human biology."
            ),
        })
        if protein_function and protein_function != "Unknown":
            uniprot_pts += 1
            breakdown.append({
                "label": "Protein function is well-documented",
                "points": 1,
                "source": "UniProt",
                "detail": protein_function[:150] + ("..." if len(protein_function) > 150 else ""),
            })
    else:
        breakdown.append({
            "label": "Protein not yet documented in UniProt",
            "points": 0,
            "source": "UniProt",
            "detail": "No confirmed human protein entry found. May be a very novel or poorly-characterised target.",
        })

    score_raw = ot_pts + uniprot_pts
    score_final = max(1, min(10, score_raw)) if score_raw > 0 else 1

    if score_raw == 0:
        breakdown.append({
            "label": "Minimum baseline score assigned",
            "points": 1,
            "source": "Pipeline",
            "detail": "No evidence found in either database. This target is speculative — needs experimental validation.",
        })

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

    console.print(f"[green]Score for {target_gene}:[/green] {score_final}/10 (raw={score_raw})")
    return result


# Expose as score_target (async function used directly by Gemini agent)
score_target = score_target_async
