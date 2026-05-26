"""
pipeline/runner.py
Main orchestration pipeline.

MVP improvements over POC:
- PubMed + preprints + trials fetched in parallel (asyncio.gather)
- Genes discovered and scored BEFORE LLM call (pre-scores injected into prompt)
- brief sanitized to strip chatbot epilogues
- target_scores returned in result dict (was missing in POC)
- Runner session uses unique IDs to avoid stale state
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from agent.main_agent import AGENT_TOOLS, system_prompt
from agent.bedrock_agent import run_bedrock_agent
from agent.tools.pubmed_tool import search_pubmed
from agent.tools.preprint_tool import search_preprints
from agent.tools.trials_tool import search_clinical_trials
from rag.ingestor import ingest_papers
from pipeline.brief_generator import save_brief
from pipeline.brief_sanitize import sanitize_brief
from pipeline.target_scores import enforce_target_scores
from rich.console import Console
import json

console = Console()


def _filter_papers_by_date(papers: list, days_back: int) -> list:
    """Post-filter papers by date since biomcp doesn't support date-range filtering."""
    if not days_back:
        return papers
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    filtered = []
    for p in papers:
        date_str = p.get("date", "")
        if not date_str or date_str == "N/A":
            filtered.append(p)
            continue
        try:
            pub_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if pub_date >= cutoff:
                filtered.append(p)
        except Exception:
            filtered.append(p)
    return filtered


async def _fetch_pubmed(query: str, days_back: int, max_papers: int, steps: list) -> list:
    """Fetch PubMed papers with retry and date filtering."""
    try:
        # Broader query — no year restriction; days_back filter handles recency
        prefetch_query = f"{query} drug target"
        all_papers = await search_pubmed(prefetch_query, days_back=days_back, max_results=max_papers)
        papers = _filter_papers_by_date(all_papers, days_back) if days_back > 0 else all_papers

        if not papers and all_papers:
            console.print("[yellow]Date filter removed all papers — using unfiltered results.[/yellow]")
            papers = all_papers[:max_papers]
            steps.append({
                "icon": "⚠️", "label": f"No papers within {days_back}-day window — using broader results",
                "detail": f"Fetched {len(papers)} papers without date filter", "status": "warn"
            })
        else:
            steps.append({
                "icon": "🔍", "label": f"Fetched {len(papers)} papers from PubMed",
                "detail": f"Query: '{prefetch_query}'", "status": "ok" if papers else "warn"
            })
        return papers
    except Exception as e:
        console.print(f"[red]PubMed fetch failed: {e}[/red]")
        steps.append({"icon": "❌", "label": "PubMed fetch failed", "detail": str(e), "status": "error"})
        return []


async def _fetch_preprints(query: str, days_back: int, steps: list) -> list:
    """Fetch preprints from bioRxiv/medRxiv via Europe PMC."""
    try:
        preprints = await search_preprints(query, days_back=days_back, max_results=15)
        steps.append({
            "icon": "📄", "label": f"Fetched {len(preprints)} preprints from bioRxiv / medRxiv",
            "detail": "Via Europe PMC — tagged as unreviewed in brief",
            "status": "ok" if preprints else "warn"
        })
        return preprints
    except Exception as e:
        console.print(f"[yellow]Preprint fetch failed: {e}[/yellow]")
        steps.append({"icon": "⚠️", "label": "Preprint fetch failed", "detail": str(e), "status": "warn"})
        return []


async def _fetch_trials(query: str, steps: list) -> list:
    """Fetch clinical trials from ClinicalTrials.gov."""
    try:
        trials = await search_clinical_trials(condition=query)
        steps.append({
            "icon": "🏥", "label": f"Found {len(trials)} active/recruiting clinical trials",
            "detail": f"Condition: {query}", "status": "ok" if trials else "warn"
        })
        return trials
    except Exception as e:
        console.print(f"[yellow]Trials fetch failed: {e}[/yellow]")
        steps.append({"icon": "⚠️", "label": "Clinical trials fetch failed", "detail": str(e), "status": "warn"})
        return []


async def run_pipeline(
    disease_query: str,
    days_back: int = 180,
    max_papers: int = 20,
    fetch_fresh: bool = True,
) -> dict:
    """
    Runs the full intelligence pipeline.

    Returns:
        dict with keys: brief, papers, preprints, trials, target_scores, steps, trace, filepath
    """
    console.print(f"[bold green]Starting PharmaLit MVP Pipeline:[/bold green] {disease_query}")

    steps = []

    # ── Step 1: PARALLEL fetch — PubMed + preprints + trials ─────────────────
    papers = []
    preprints = []
    trials = []

    if fetch_fresh:
        console.print("[bold]Fetching PubMed + preprints + trials in parallel...[/bold]")
        papers, preprints, trials = await asyncio.gather(
            _fetch_pubmed(disease_query, days_back, max_papers, steps),
            _fetch_preprints(disease_query, days_back, steps),
            _fetch_trials(disease_query, steps),
        )
    else:
        steps.append({
            "icon": "📦", "label": "Using existing knowledge base (no new fetch)",
            "detail": "Toggle fetch_fresh=True to pull new data", "status": "ok"
        })
        # Still fetch trials as they're fast and always useful
        trials = await _fetch_trials(disease_query, steps)

    # ── Step 2: Ingest papers into ChromaDB ───────────────────────────────────
    if papers:
        console.print(f"[bold]Ingesting {len(papers)} papers into ChromaDB...[/bold]")
        ingest_papers(papers)
        steps.append({
            "icon": "💾", "label": f"Ingested {len(papers)} papers into knowledge base (ChromaDB)",
            "detail": "Duplicate PMIDs skipped automatically", "status": "ok"
        })

    # ── Step 3: PRE-SCORE genes BEFORE LLM call ───────────────────────────────
    console.print("[bold]Pre-scoring candidate genes before LLM call...[/bold]")
    steps.append({
        "icon": "🧬", "label": "Discovering and pre-scoring candidate genes",
        "detail": "Parallel Open Targets + UniProt queries", "status": "ok"
    })

    pre_scores = await enforce_target_scores(disease_query, papers, brief="")

    if pre_scores:
        scored_genes = [s["gene"] for s in pre_scores]
        steps.append({
            "icon": "📊", "label": f"Pre-scored {len(pre_scores)} target(s): {', '.join(scored_genes)}",
            "detail": "Scores injected into LLM prompt — agent will not need to re-score these",
            "status": "ok"
        })
        # Format pre-scores for prompt injection
        pre_score_lines = []
        for s in pre_scores:
            pre_score_lines.append(
                f"  - {s['gene']}: {s['score']}/10 | {s['tractability']} | UniProt: {s['uniprot_id']}"
            )
        pre_score_text = "Pre-computed target scores (DO NOT re-score these genes with score_target tool):\n" + "\n".join(pre_score_lines)
    else:
        pre_score_text = ""
        steps.append({
            "icon": "⚠️", "label": "No genes pre-scored — agent will score during analysis",
            "detail": "Gene discovery found no validated candidates", "status": "warn"
        })

    # ── Step 4: Run Bedrock agent ─────────────────────────────────────────────
    console.print("[bold]Starting Bedrock Agent (Claude)...[/bold]")
    steps.append({
        "icon": "R", "label": "Agent started — querying RAG, PubMed, Open Targets, UniProt",
        "detail": f"Model: {__import__('os').getenv('BEDROCK_MODEL_ID', 'claude-3-haiku')} | Disease: {disease_query}",
        "status": "ok"
    })

    prompt_parts = [
        f"Analyze the following disease area and produce a full hypothesis brief: {disease_query}\n",
        f"IMPORTANT: When calling search_pubmed, use days_back={days_back} and max_results={max_papers}.",
    ]
    if pre_score_text:
        prompt_parts.append(f"\n{pre_score_text}")

    prompt = "\n".join(prompt_parts)
    trace_lines = []
    brief_content = ""

    try:
        brief_content = await run_bedrock_agent(
            user_message=prompt,
            system_prompt=system_prompt,
            tool_functions=AGENT_TOOLS,
            steps=steps,
            trace_lines=trace_lines,
        )

        if not brief_content:
            brief_content = (
                "# Agent returned empty content\n\n"
                "The model ran but produced no text. Possible causes:\n"
                "- Knowledge base is empty (set fetch_fresh=True)\n"
                "- AWS credentials not configured\n"
                "- Model produced only tool calls with no final synthesis\n\n"
                "**Pipeline steps:**\n"
                + "\n".join(f"- {s['label']}" for s in steps)
            )
            steps.append({
                "icon": "X", "label": "Agent returned no brief content",
                "detail": "Check AWS credentials and knowledge base status", "status": "error"
            })
        else:
            steps.append({
                "icon": "OK", "label": "Hypothesis brief generated successfully",
                "detail": f"{len(brief_content)} characters", "status": "ok"
            })

    except Exception as e:
        console.print(f"[red]Bedrock agent execution failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        brief_content = f"# Error generating brief\n\n{e}"
        steps.append({"icon": "X", "label": "Bedrock agent failed", "detail": str(e), "status": "error"})

    agent_scores_raw = []  # Bedrock agent may score via score_target tool; captured in trace

    # ── Step 5: Sanitize brief ────────────────────────────────────────────────
    brief_content = sanitize_brief(brief_content)

    # ── Step 6: Final target score enforcement ────────────────────────────────
    # Run again with brief for any genes mentioned there that we missed
    if pre_scores:
        # Supplement with any agent scores for genes not already in pre_scores
        from pipeline.target_scores import _merge_scores
        target_scores = _merge_scores(pre_scores, agent_scores_raw)
    else:
        # No pre-scores — try to discover from brief now
        target_scores = await enforce_target_scores(
            disease_query, papers, brief=brief_content, agent_scores=agent_scores_raw
        )

    if target_scores:
        steps.append({
            "icon": "🎯", "label": f"Target scoreboard ready: {len(target_scores)} target(s)",
            "detail": ", ".join(f"{s['gene']} {s['score']}/10" for s in target_scores),
            "status": "ok"
        })

    # ── Step 7: Save brief ────────────────────────────────────────────────────
    filepath = save_brief(disease_query, brief_content)
    console.print(f"[green]Brief saved to {filepath}[/green]")
    steps.append({
        "icon": "💾", "label": "Brief saved to disk",
        "detail": filepath, "status": "ok"
    })

    trace_text = "\n".join(trace_lines) if trace_lines else "No tool calls traced."

    return {
        "brief": brief_content,
        "papers": papers,
        "preprints": preprints,
        "trials": trials,
        "target_scores": target_scores,   # ← Was missing in POC — now included
        "steps": steps,
        "trace": trace_text,
        "filepath": filepath,
    }
