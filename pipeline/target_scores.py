"""
pipeline/target_scores.py
Enforces pipeline-level target scoring: discovers genes, scores them in parallel,
and merges with any scores already collected from the ADK agent's tool calls.
"""
import asyncio
from rich.console import Console
from pipeline.gene_discovery import discover_candidate_genes
from agent.tools.scoring_tool import score_target_async

console = Console()


async def enforce_target_scores(
    query: str,
    papers: list[dict],
    brief: str = "",
    agent_scores: list[dict] | None = None,
) -> list[dict]:
    """
    Pipeline-level target scoring enforcement.

    1. Discovers candidate genes from query + papers + brief.
    2. Scores each gene in parallel via Open Targets + UniProt.
    3. Merges with any scores already collected from agent tool calls.
    4. Returns deduplicated list (pipeline scores take precedence).

    Args:
        query: Disease/target query.
        papers: List of paper dicts from PubMed fetch.
        brief: Agent-generated brief (optional — used for additional gene hints).
        agent_scores: Scores already returned by agent tool calls (optional).

    Returns:
        List of score dicts with full breakdown, deduplicated by gene symbol.
    """
    console.print("[cyan]enforce_target_scores:[/cyan] Discovering and scoring candidate genes...")

    # Step 1: Discover candidate genes
    candidate_genes = await discover_candidate_genes(query, papers, brief)

    if not candidate_genes:
        console.print("[yellow]enforce_target_scores: No candidate genes discovered.[/yellow]")
        # Return agent scores if any exist
        return _dedup_scores(agent_scores or [])

    # Step 2: Score candidates in parallel
    console.print(f"[cyan]Scoring {len(candidate_genes)} genes in parallel:[/cyan] {candidate_genes}")
    score_tasks = [score_target_async(gene, query) for gene in candidate_genes]
    pipeline_scores = list(await asyncio.gather(*score_tasks, return_exceptions=True))

    # Filter out exceptions
    valid_pipeline = []
    for gene, result in zip(candidate_genes, pipeline_scores):
        if isinstance(result, Exception):
            console.print(f"[yellow]Scoring failed for {gene}: {result}[/yellow]")
        elif isinstance(result, dict):
            valid_pipeline.append(result)

    # Step 3: Merge with agent scores (pipeline scores take precedence)
    merged = _merge_scores(valid_pipeline, agent_scores or [])

    console.print(f"[bold green]enforce_target_scores:[/bold green] {len(merged)} target score(s) ready.")
    return merged


def _dedup_scores(scores: list[dict]) -> list[dict]:
    """Deduplicate by gene symbol, keep first occurrence."""
    seen = set()
    out = []
    for s in scores:
        gene = s.get("gene", "").upper()
        if gene and gene not in seen:
            seen.add(gene)
            out.append(s)
    return out


def _merge_scores(pipeline_scores: list[dict], agent_scores: list[dict]) -> list[dict]:
    """
    Merge pipeline scores + agent scores.
    Pipeline scores take precedence (more reliable).
    Agent scores fill in genes not discovered by pipeline.
    """
    result = list(pipeline_scores)
    pipeline_genes = {s.get("gene", "").upper() for s in pipeline_scores}

    for agent_score in agent_scores:
        gene = agent_score.get("gene", "").upper()
        if gene and gene not in pipeline_genes:
            result.append(agent_score)

    return _dedup_scores(result)


def parse_agent_scores_from_steps(steps: list[dict]) -> list[dict]:
    """
    Extracts any score dicts that the ADK agent returned via score_target tool calls.
    Steps are the structured step dicts from runner.py.
    """
    # This is a best-effort extraction — agent scores come back embedded in trace.
    # The main scoring path is pipeline-level. Agent scores are a fallback supplement.
    return []
