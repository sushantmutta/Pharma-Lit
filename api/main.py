"""
api/main.py
PharmaLit MVP — FastAPI backend

Endpoints:
  POST /api/analyze      → run full pipeline
  GET  /api/health       → smoke-test all external APIs
  GET  /api/rag/stats    → ChromaDB chunk/paper counts
  DELETE /api/rag/clear  → wipe ChromaDB collection
"""
import asyncio
import os
import sys
import chromadb

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.runner import run_pipeline

app = FastAPI(
    title="PharmaLit API",
    description="Pharmaceutical R&D intelligence — local-first pipeline API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response models ─────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Disease/target query")
    days_back: int = Field(default=180, ge=1, le=1825)
    max_papers: int = Field(default=20, ge=1, le=50)
    fetch_fresh: bool = Field(default=True)


class AnalyzeResponse(BaseModel):
    brief: str
    papers: list[dict]
    preprints: list[dict]
    trials: list[dict]
    target_scores: list[dict] = []
    steps: list[dict] = []
    filepath: str = ""


class HealthStatus(BaseModel):
    status: str
    services: list[dict]


class RagStats(BaseModel):
    chunk_count: int
    paper_count: int


# ── Helpers ───────────────────────────────────────────────────────────────────

CHROMA_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db")


def _get_rag_stats() -> tuple[int, int]:
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        col = client.get_or_create_collection("pharma_papers")
        count = col.count()
        if count > 0:
            results = col.get(include=["metadatas"], limit=count)
            pmids = {m.get("pmid", "N/A") for m in results["metadatas"] if m.get("pmid", "N/A") != "N/A"}
            return count, len(pmids)
        return 0, 0
    except Exception:
        return 0, 0


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    """Run the full PharmaLit intelligence pipeline."""
    try:
        result = await run_pipeline(
            disease_query=req.query,
            days_back=req.days_back,
            max_papers=req.max_papers,
            fetch_fresh=req.fetch_fresh,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health", response_model=HealthStatus)
async def health():
    """Smoke-test all external APIs concurrently."""
    import httpx, time

    async def _test(name, coro):
        t0 = time.time()
        try:
            result = await coro
            return {"name": name, "status": "ok", "latency_ms": int((time.time()-t0)*1000), "detail": result}
        except Exception as e:
            return {"name": name, "status": "error", "latency_ms": int((time.time()-t0)*1000), "detail": str(e)}

    async def _ot():
        q = '{ search(queryString: "PCSK9", entityNames: ["target"]) { hits { id } } }'
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.post("https://api.platform.opentargets.org/api/v4/graphql", json={"query": q})
        hits = r.json().get("data", {}).get("search", {}).get("hits", [])
        return f"{len(hits)} hits for PCSK9"

    async def _uniprot():
        async with httpx.AsyncClient(timeout=8.0) as c:
            r = await c.get("https://rest.uniprot.org/uniprotkb/search?query=gene_exact:PCSK9+AND+organism_id:9606&format=json&size=1")
        results = r.json().get("results", [])
        return f"PCSK9 → {results[0]['primaryAccession']}" if results else "no results"

    async def _europepmc():
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                            params={"query": "NASH SRC:PPR", "resulttype": "lite", "format": "json", "pageSize": "1"})
        items = r.json().get("resultList", {}).get("result", [])
        return f"{len(items)} preprints"

    async def _clinicaltrials():
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get("https://clinicaltrials.gov/api/v2/studies",
                            params={"query.cond": "diabetes", "pageSize": 1, "format": "json"})
        total = r.json().get("totalCount", 0)
        return f"{total} trials for 'diabetes'"

    services = await asyncio.gather(
        _test("Open Targets (Drug DB)", _ot()),
        _test("UniProt (Protein DB)", _uniprot()),
        _test("Europe PMC (Preprints)", _europepmc()),
        _test("ClinicalTrials.gov", _clinicaltrials()),
        return_exceptions=True,
    )

    results = []
    for s in services:
        if isinstance(s, Exception):
            results.append({"name": "Unknown", "status": "error", "latency_ms": 0, "detail": str(s)})
        else:
            results.append(s)

    overall = "ok" if all(s.get("status") == "ok" for s in results) else "degraded"
    return {"status": overall, "services": results}


@app.get("/api/rag/stats", response_model=RagStats)
async def rag_stats():
    chunk_count, paper_count = _get_rag_stats()
    return {"chunk_count": chunk_count, "paper_count": paper_count}


@app.delete("/api/rag/clear")
async def rag_clear():
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        client.delete_collection("pharma_papers")
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Static file serving ───────────────────────────────────────────────────────

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


@app.get("/")
async def serve_index():
    index = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Frontend not found")


@app.get("/{full_path:path}")
async def serve_spa_fallback(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("frontend/"):
        raise HTTPException(status_code=404, detail="Not found")
    index = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Frontend not found")
