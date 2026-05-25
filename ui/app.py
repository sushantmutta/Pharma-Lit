from dotenv import load_dotenv
from datetime import datetime
import chromadb
import threading
import asyncio
import streamlit as st
from pipeline.runner import run_pipeline
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


load_dotenv()


# ─── Helpers ──────────────────────────────────────────────────────────────────


def run_async_safely(coro):
    """Runs an async coroutine safely in a new thread to avoid Streamlit event loop conflicts."""
    result, exc = None, None

    def _run():
        nonlocal result, exc
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(coro)
            pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
            if pending:
                loop.run_until_complete(asyncio.wait(pending, timeout=5))
                for task in pending:
                    if not task.done():
                        task.cancel()
                loop.run_until_complete(asyncio.gather(
                    *pending, return_exceptions=True))
            loop.close()
        except Exception as e:
            exc = e
    t = threading.Thread(target=_run)
    t.start()
    t.join()
    if exc:
        raise exc
    return result


def get_rag_stats():
    """Return how many papers/chunks are in ChromaDB."""
    try:
        chroma_path = os.path.join(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))), "data", "chroma")
        client = chromadb.PersistentClient(path=chroma_path)
        col = client.get_or_create_collection("pharmalit")
        count = col.count()
        if count > 0:
            results = col.get(include=["metadatas"], limit=count)
            pmids = {m.get("pmid", "N/A")
                     for m in results["metadatas"] if m.get("pmid", "N/A") != "N/A"}
            return count, len(pmids)
        return 0, 0
    except Exception:
        return 0, 0


def clear_rag():
    try:
        chroma_path = os.path.join(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))), "data", "chroma")
        client = chromadb.PersistentClient(path=chroma_path)
        client.delete_collection("pharmalit")
        return True
    except Exception:
        return False


# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PharmaLit Intelligence Agent",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🧬 PharmaLit Agent")
    # st.caption("Powered by Google ADK · Gemini 2.0 Flash · BioMCP · ChromaDB")

    st.divider()

    # Knowledge base status
    chunk_count, paper_count = get_rag_stats()
    if chunk_count > 0:
        st.success(
            f"📦 Knowledge base: **{paper_count} papers** · {chunk_count} chunks")
        if st.button("🗑️ Clear knowledge base", use_container_width=True):
            if clear_rag():
                st.success("Knowledge base cleared.")
                st.rerun()
    else:
        st.info("📦 Knowledge base empty — first run will fetch from PubMed.")

    st.divider()

    query = st.text_input(
        "🔬 Disease / Target area",
        value="NASH hepatocyte lipid metabolism",
        help="Be specific — e.g. 'KRAS mutant NSCLC' or 'NASH FXR agonist'"
    )

    days_back = st.number_input(
        "Days back to search (PubMed fetch)",
        min_value=1,
        max_value=1825,
        value=180,
        step=30,
        help="Controls how far back to pull papers from PubMed. Default 180 = last 6 months (recent 2025-2026 papers)."
    )

    max_papers = st.slider("Max papers to fetch",
                           min_value=5, max_value=40, value=20, step=5)

    use_rag_only = st.toggle(
        "Use existing knowledge base only",
        value=False,
        help="Skip PubMed fetch — use only papers already in the knowledge base. Faster."
    )

    st.divider()
    run_btn = st.button("🔍 Run Analysis", type="primary",
                        use_container_width=True)

    st.divider()
    st.caption("Powered by Google ADK + Gemini 2.0 Flash + BioMCP + ChromaDB")
    st.caption(f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_brief, tab_papers, tab_preprints, tab_trials, tab_trace = st.tabs([
    "📝 Target Brief",
    "📚 Papers Found",
    "🧪 Preprints",
    "🏥 Clinical Trials",
    "🤖 Agent Trace",
])

if "results" not in st.session_state:
    with tab_brief:
        st.info(
            "👈 Enter a disease/target query in the sidebar and click **Run Analysis**.")
    with tab_papers:
        st.info("Retrieved PubMed papers will appear here.")
    with tab_preprints:
        st.info("Recent preprints from bioRxiv and medRxiv will appear here.")
    with tab_trials:
        st.info("Active and recruiting clinical trials will appear here.")
    with tab_trace:
        st.info("The agent's tool call trace will appear here.")

# ─── Run pipeline ─────────────────────────────────────────────────────────────
if run_btn:
    progress = st.progress(0, text="Starting pipeline...")
    with st.spinner("Agent analysing literature..."):
        try:
            progress.progress(20, text="Searching PubMed...")
            results = run_async_safely(
                run_pipeline(
                    disease_query=query,
                    days_back=int(days_back),
                    max_papers=int(max_papers),
                    fetch_fresh=not use_rag_only,
                )
            )
            progress.progress(100, text="Done!")
            st.session_state["results"] = results
            st.session_state["query"] = query
            st.rerun()
        except Exception as e:
            progress.empty()
            st.error(f"**Pipeline failed:** {e}")

# ─── Display results ──────────────────────────────────────────────────────────
if "results" in st.session_state:
    results = st.session_state["results"]
    query_used = st.session_state.get("query", "")

    # ── Tab 1: Target Brief ──────────────────────────────────────────────────
    with tab_brief:
        brief = results.get("brief", "")
        if not brief or brief.startswith("# Agent returned") or brief.startswith("# Error"):
            st.warning(
                "The agent did not produce a brief. Check the **Agent Trace** tab for details.")
            if brief:
                st.code(brief)
        else:
            col_hdr, col_dl = st.columns([4, 1])
            with col_hdr:
                st.subheader(f"Analysis: {query_used}")
                st.caption(
                    f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · "
                    f"{len(results.get('papers', []))} papers ingested"
                )
            with col_dl:
                st.download_button(
                    "⬇️ Download .md",
                    data=brief,
                    file_name=f"brief_{datetime.now().strftime('%Y%m%d')}_{query_used[:30].replace(' ', '_')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            st.divider()
            st.markdown(brief)

    # ── Tab 2: Papers Found ──────────────────────────────────────────────────
    with tab_papers:
        papers = results.get("papers", [])
        if papers:
            st.caption(
                f"**{len(papers)} papers** retrieved from PubMed and ingested into knowledge base")
            for i, p in enumerate(papers):
                title = p.get("title", "Unknown title")
                pmid = p.get("pmid", "N/A")
                with st.expander(f"📄 {title}", expanded=(i < 2)):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.markdown(f"**Journal:** {p.get('journal', 'N/A')}")
                        date = p.get("date", "N/A")
                        if date and date != "N/A":
                            date = date[:10]
                        st.markdown(f"**Published:** {date}")
                        if pmid != "N/A":
                            st.markdown(
                                f"**PMID:** [{pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)")
                        doi = p.get("doi", "")
                        if doi and doi != "N/A":
                            st.markdown(
                                f"**DOI:** [{doi}](https://doi.org/{doi})")
                    with col2:
                        abstract = p.get("abstract", "")
                        if abstract:
                            st.markdown(
                                f"**Abstract:** {abstract[:500]}{'...' if len(abstract) > 500 else ''}")
        else:
            st.info(
                "No papers retrieved. Make sure 'Use existing knowledge base only' is OFF and run again.")

    # ── Tab 3: Preprints ─────────────────────────────────────────────────────
    with tab_preprints:
        preprints = results.get("preprints", [])
        if preprints:
            st.caption(
                f"**{len(preprints)} preprints** from bioRxiv / medRxiv · ⚠️ Not peer-reviewed")
            for i, p in enumerate(preprints):
                title = p.get("title", "Unknown title")
                server = p.get("server", "Preprint")
                badge = "🔬 bioRxiv" if "biorxiv" in server.lower(
                ) else "🏥 medRxiv" if "medrxiv" in server.lower() else "📄 Preprint"
                with st.expander(f"{badge} {title}", expanded=(i < 3)):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        date = p.get("date", "N/A")
                        if date and date != "N/A":
                            date = date[:10]
                        st.markdown(f"**Server:** {server}")
                        st.markdown(f"**Posted:** {date}")
                        doi = p.get("doi", "")
                        if doi and doi != "N/A":
                            st.markdown(
                                f"**DOI:** [{doi}](https://doi.org/{doi})")
                        st.warning("⚠️ Preprint — not peer reviewed")
                    with col2:
                        authors = p.get("authors", "")
                        if authors:
                            st.markdown(
                                f"**Authors:** {authors[:120]}{'...' if len(authors) > 120 else ''}")
                        abstract = p.get("abstract", "")
                        if abstract:
                            st.markdown(
                                f"**Abstract:** {abstract[:500]}{'...' if len(abstract) > 500 else ''}")
        else:
            st.info(
                "No preprints found for this query. Try broadening the search or increasing 'Days back'.")

    # ── Tab 4: Clinical Trials ───────────────────────────────────────────────
    with tab_trials:
        trials = results.get("trials", [])
        if trials:
            st.caption(
                f"**{len(trials)} active / recruiting trials** on ClinicalTrials.gov")
            for trial in trials:
                nct = trial.get("nct_id", "N/A")
                title = trial.get("title", "Unknown trial")
                phase = trial.get("phase", "N/A")
                status = trial.get("status", "N/A")
                sponsor = trial.get("sponsor", "")
                interventions = trial.get("interventions", "")
                start_date = trial.get("start_date", "")
                url = trial.get("url", "")

                status_color = "🟢" if "RECRUITING" in status.upper(
                ) else "🟡" if "ACTIVE" in status.upper() else "⚪"
                with st.expander(f"{status_color} {title}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        if nct != "N/A":
                            link = url if url else f"https://clinicaltrials.gov/study/{nct}"
                            st.markdown(f"**NCT ID:** [{nct}]({link})")
                        st.markdown(f"**Phase:** {phase}")
                        st.markdown(f"**Status:** {status}")
                        if start_date and start_date != "N/A":
                            st.markdown(f"**Start date:** {start_date}")
                    with col2:
                        if sponsor and sponsor != "N/A":
                            st.markdown(f"**Sponsor:** {sponsor}")
                        if interventions and interventions != "N/A":
                            st.markdown(
                                f"**Interventions:** {interventions[:200]}")
        else:
            st.info(
                "No active trials found for this condition on ClinicalTrials.gov.")

    # ── Tab 5: Agent Trace ───────────────────────────────────────────────────
    with tab_trace:
        steps = results.get("steps", [])
        trace = results.get("trace", "")

        st.subheader("Pipeline Execution Steps")
        if steps:
            for step in steps:
                icon = step.get("icon", "•")
                label = step.get("label", "")
                detail = step.get("detail", "")
                status = step.get("status", "ok")
                if status == "ok":
                    st.success(f"{icon} {label}")
                elif status == "warn":
                    st.warning(f"{icon} {label}")
                else:
                    st.error(f"{icon} {label}")
                if detail:
                    st.caption(f"   ↳ {detail}")

        if trace and trace != "No tool calls traced.":
            st.divider()
            st.markdown("**Raw agent tool call trace:**")
            st.code(trace, language="text")
        elif not steps:
            st.info("Run an analysis to see the agent trace.")
