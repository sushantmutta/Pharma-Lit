"""
pipeline/gene_discovery.py
Discovers candidate gene symbols from query text + paper titles + brief.
Validates against UniProt human entries to reject verbs/acronyms.
Returns top 3 validated gene symbols by mention frequency.
"""
import re
import asyncio
import httpx
from collections import Counter
from rich.console import Console

console = Console()

# Regex: 2-8 uppercase letters, optionally followed by digits (e.g. PCSK9, FXR, BRCA1)
_GENE_PATTERN = re.compile(r'\b([A-Z][A-Z0-9]{1,7})\b')

# Common non-gene acronyms to always skip
_BLOCKLIST = {
    "NASH", "NSCLC", "FDA", "DNA", "RNA", "PCR", "HIV", "COVID", "ICU", "BMI",
    "LDL", "HDL", "ECG", "MRI", "CT", "PET", "IND", "NDA", "ADME", "PK", "PD",
    "GLP", "GMP", "CRO", "CMO", "API", "ANDA", "BLA", "MAA", "EMA", "WHO", "NIH",
    "CDC", "AHA", "ACC", "NAFLD", "MASLD", "CVD", "T2D", "HCC", "CKD", "IBD",
    "SLE", "RA", "CI", "OR", "HR", "RR", "SD", "SE", "AUC", "IC", "EC", "KD",
    "US", "UK", "EU", "USA", "THE", "AND", "FOR", "NOT", "WITH", "FROM", "THAT",
    "THIS", "ARE", "WAS", "HAS", "HAD", "BUT", "CAN", "WILL", "MAY", "BEEN",
    "HAVE", "INTO", "THAN", "ALSO", "BOTH", "EACH", "MORE", "SUCH", "WHEN",
    "ALL", "NEW", "ANY", "TWO", "HOW", "ITS", "OUR", "OUT", "SRC", "PPR",
    "SM", "AB", "OT", "KB", "DB", "ID",
}


async def _validate_gene_uniprot(gene_symbol: str) -> bool:
    """Returns True if gene symbol resolves to a human protein in UniProt."""
    try:
        url = (
            f"https://rest.uniprot.org/uniprotkb/search"
            f"?query=gene_exact:{gene_symbol}+AND+organism_id:9606"
            f"&format=json&size=1"
        )
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url)
        data = resp.json()
        return len(data.get("results", [])) > 0
    except Exception:
        return False


def _extract_candidates(text: str) -> list[str]:
    """Extract all potential gene symbols from a text string."""
    tokens = _GENE_PATTERN.findall(text)
    return [t for t in tokens if t not in _BLOCKLIST and len(t) >= 2]


async def discover_candidate_genes(
    query: str,
    papers: list[dict],
    brief: str = "",
) -> list[str]:
    """
    Discovers up to 3 validated candidate gene symbols from query + papers + brief.

    Args:
        query: The user's disease/target query string.
        papers: List of paper dicts (uses 'title' and 'abstract' fields).
        brief: Optional agent-generated brief text.

    Returns:
        List of up to 3 validated gene symbol strings, sorted by mention frequency.
    """
    all_text_parts = [query]

    # Add paper titles and abstracts
    for p in papers:
        title = p.get("title", "")
        abstract = p.get("abstract", "")
        if title:
            all_text_parts.append(title)
        if abstract:
            all_text_parts.append(abstract[:500])  # limit abstract length

    # Add brief (first 3000 chars to avoid noise)
    if brief:
        all_text_parts.append(brief[:3000])

    combined = " ".join(all_text_parts)
    candidates = _extract_candidates(combined)

    if not candidates:
        console.print("[yellow]Gene discovery: no candidate symbols found.[/yellow]")
        return []

    # Count mention frequency
    freq = Counter(candidates)
    # Sort by frequency descending, take top candidates to validate
    top_candidates = [gene for gene, _ in freq.most_common(10)]

    console.print(f"[cyan]Gene discovery candidates:[/cyan] {top_candidates[:10]}")

    # Validate top candidates against UniProt concurrently (batch of up to 6)
    to_validate = top_candidates[:6]
    validation_tasks = [_validate_gene_uniprot(g) for g in to_validate]
    results = await asyncio.gather(*validation_tasks, return_exceptions=True)

    validated = []
    for gene, is_valid in zip(to_validate, results):
        if isinstance(is_valid, bool) and is_valid:
            validated.append(gene)
            console.print(f"[green]Validated gene:[/green] {gene}")
        else:
            console.print(f"[dim]Rejected (not in UniProt human):[/dim] {gene}")
        if len(validated) >= 3:
            break

    if not validated:
        console.print("[yellow]Gene discovery: no genes passed UniProt validation.[/yellow]")
    else:
        console.print(f"[bold green]Gene discovery result:[/bold green] {validated}")

    return validated
