"""
pipeline/gene_discovery.py
AI-powered drug target discovery — uses Gemini to extract RECEPTOR/ENZYME
targets from the query and paper titles/abstracts.

Why AI, not rules:
- A lookup table only works for hormones you pre-listed.
- A query like "STING pathway NSCLC" or "cGAS inhibitor colorectal" needs
  genuine understanding of pharmacology, not string matching.
- Gemini knows that GLP-1 → GLP1R, VEGF → KDR, TNF-α → TNFRSF1A etc.
  from its training, and generalises to targets we never anticipated.

The lookup table is kept ONLY as a fast, zero-latency boost layer for the
most common metabolic targets — it supplements the AI, it does not replace it.
"""
import asyncio
import os
import re
from rich.console import Console

console = Console()

# ── Fast boost layer (only for ultra-common metabolic hormones) ───────────────
# This is NOT the main logic. It's a zero-cost supplement for the 5 most
# common cases where the AI might return the hormone instead of the receptor.
_QUICK_RECEPTOR_MAP = {
    "GLP-1": "GLP1R", "GLP1": "GLP1R",
    "GIP": "GIPR",
    "GLUCAGON": "GCGR",
    "INSULIN": "INSR",
    "LEPTIN": "LEPR",
}

# Acronyms that should NEVER be treated as gene symbols
_NON_GENE = {
    "NASH", "NAFLD", "MASLD", "NSCLC", "T2D", "T2DM", "CVD", "HCC",
    "CKD", "IBD", "SLE", "RA", "COPD", "IPF", "ALS", "MS",
    "FDA", "EMA", "WHO", "NIH", "DNA", "RNA", "MRNA", "PCR",
    "ICU", "BMI", "LDL", "HDL", "ADME", "PK", "PD", "GMP", "GLP",
}


async def _gemini_extract_targets(query: str, paper_context: str) -> list[str]:
    """
    Ask Gemini to extract the top druggable RECEPTOR / ENZYME targets from
    the disease query and a sample of paper titles.

    Returns a list of HGNC gene symbols (e.g. ['GLP1R', 'GIPR', 'PCSK9']).
    Falls back to empty list on any error.
    """
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        return []

    prompt = f"""You are a pharmaceutical target identification expert.

Given this disease/drug query:
"{query}"

And these recent paper titles:
{paper_context}

Identify the top 5 DRUGGABLE RECEPTOR or ENZYME targets that drugs in this disease area act ON.

CRITICAL RULES:
- Return RECEPTORS and ENZYMES — NOT hormones or ligands.
  GLP-1 is a hormone → return GLP1R (its receptor)
  GIP is a hormone → return GIPR (its receptor)
  TNF-alpha is a cytokine → return TNFRSF1A or TNFRSF1B (its receptor)
  VEGF is a growth factor → return KDR or FLT1 (its receptor)
  Amyloid-beta is a peptide → return BACE1 (enzyme that produces it)
- Return only valid HGNC gene symbols (e.g. GLP1R, PCSK9, EGFR)
- Return ONLY the gene symbols, comma-separated, nothing else
- Maximum 5 symbols
- If you cannot identify any, return: NONE

Examples:
  Query: "Type 2 diabetes GLP-1 receptor agonist" → GLP1R,GIPR,GCGR,INSR,DPP4
  Query: "NASH FXR agonist liver fibrosis" → NR1H4,PPARA,TGFBR1,ACTA2,COL1A1
  Query: "KRAS mutant NSCLC" → KRAS,EGFR,BRAF,MEK1,PIK3CA

Respond with ONLY the comma-separated gene symbols:"""

    text = ""
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                    contents=prompt,
                )
            )
            text = (response.text or "").strip()
        except Exception as e:
            console.print(f"[yellow]Gemini target extraction failed: {e}. Falling back to Groq...[/yellow]")

    if not text:
        groq_key = os.getenv("GROQ_API_KEY", "")
        if groq_key:
            import httpx
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {groq_key}"},
                        json={
                            "model": "llama-3.3-70b-versatile",
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.1
                        }
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                console.print(f"[red]Groq extraction fallback failed: {e}[/red]")

    if text.upper() == "NONE" or not text:
        return []

    # Parse comma-separated symbols
    raw = [s.strip().upper() for s in text.split(",")]
    # Filter: must look like a gene symbol (letters + digits, 2-10 chars)
    valid = [
        s for s in raw
        if re.match(r'^[A-Z][A-Z0-9]{1,9}$', s)
        and s not in _NON_GENE
    ]
    console.print(f"[cyan]AI target extraction:[/cyan] {valid}")
    return valid[:5]


_GENE_PATTERN = re.compile(r'\b([A-Z][A-Z0-9]{1,9}(?:[A-Z0-9]|\d)?)\b')
_KNOWN_DRUG_TARGETS = {
    "GLP1R", "GIPR", "GCGR", "INSR", "LEPR", "GHSR", "CALCR",
    "PCSK9", "ANGPTL3", "LPL",
    "KRAS", "BRAF", "EGFR", "ALK", "RET", "MET", "FGFR1", "FGFR2",
    "BACE1", "DRD2", "HTR2A",
    "IL5RA", "IL13RA1", "IL4R", "IL6R", "IL17RA", "TNFRSF1A",
    "FCER1A", "KDR", "ERBB2", "PDCD1", "CD274",
    "NR1H4", "TGFBR1", "FXR", "PPARG", "SGLT2", "DPP4", "VEGFR2"
}

def _extract_gene_symbols(text: str, max_genes: int = 10) -> list[str]:
    """Rule-based fallback: Extract known drug target symbols from text."""
    candidates = _GENE_PATTERN.findall(text)
    genes = []
    seen = set()
    for c in candidates:
        if c in _NON_GENE or len(c) < 3 or c in seen:
            continue
        seen.add(c)
        if c in _KNOWN_DRUG_TARGETS:
            genes.append(c)
        if len(genes) >= max_genes:
            break
    return genes


def _quick_boost(query: str) -> list[str]:
    """
    Fast supplement: map ultra-common hormone mentions in the query
    to their receptors using the small lookup table.
    Only adds targets NOT already found by AI.
    """
    query_upper = query.upper()
    found = []
    for hormone, receptor in _QUICK_RECEPTOR_MAP.items():
        if hormone in query_upper:
            found.append(receptor)
    return found


async def discover_candidate_genes(
    query: str,
    papers: list[dict],
    brief: str = "",
) -> list[str]:
    """
    AI-powered discovery of candidate drug targets.

    Strategy:
    1. Ask Gemini to extract receptor/enzyme targets from query + paper titles
       (intelligent, generalizable — handles any disease area)
    2. Supplement with quick lookup for ultra-common metabolic hormones
       (zero-latency safety net for GLP-1, GIP etc.)
    3. Deduplicate, cap at 6 candidates

    This is genuinely AI-powered: Gemini understands pharmacology and knows
    that hormones → receptors, growth factors → receptors, etc.
    """
    # Build paper context (top 10 titles)
    titles = []
    for p in papers[:10]:
        t = p.get("title", "")
        if t:
            titles.append(f"- {t}")
    paper_context = "\n".join(titles) if titles else "(no papers fetched yet)"

    # Step 1: AI extraction (primary method)
    ai_targets = await _gemini_extract_targets(query, paper_context)

    # Step 2: Quick boost for common hormones (supplement, not replace)
    boost = _quick_boost(query)
    for r in boost:
        if r not in ai_targets:
            ai_targets.append(r)

    # Step 3: Rule-based fallback if AI failed completely
    if not ai_targets:
        console.print("[yellow]AI extraction empty/failed — using rule-based fallback[/yellow]")
        fallback_targets = _extract_gene_symbols(query.upper())
        for p in papers[:10]:
            fallback_targets.extend(_extract_gene_symbols(p.get("title", "").upper()))
        
        # Deduplicate
        seen = set()
        for t in fallback_targets:
            if t not in seen:
                seen.add(t)
                ai_targets.append(t)

    # Cap at 6
    candidates = ai_targets[:6]

    if candidates:
        console.print(f"[bold cyan]Final candidates (AI-extracted receptors):[/bold cyan] {candidates}")
    else:
        console.print("[yellow]No candidate targets found — agent will score from context[/yellow]")

    return candidates
