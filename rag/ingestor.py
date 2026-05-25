import os
import glob
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import httpx
from pypdf import PdfReader
from rich.console import Console

console = Console()

# Initialize ChromaDB locally
CHROMA_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
os.makedirs(CHROMA_DB_DIR, exist_ok=True)
client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

# Get or create collection
collection = client.get_or_create_collection(
    name="pharma_papers",
    metadata={"hnsw:space": "cosine"}
)

# Load embedding model
console.print("[dim]Loading sentence-transformer model (all-MiniLM-L6-v2)...[/dim]")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def chunk_text(text: str, chunk_size: int = 200, overlap: int = 20) -> list[str]:
    """Basic chunking splitting by words to approximate tokens."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts text from a local PDF file."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        console.print(f"[red]Error reading PDF {pdf_path}: {e}[/red]")
        return ""

async def fetch_pmc_oa_text(pmid: str) -> str:
    """Attempts to fetch full text from PMC Open Access API if available."""
    # Simplified approach: for POC we will rely on abstracts provided by BioMCP.
    # A full PMC fetcher would query E-utilities, map PMID to PMCID, then fetch full text.
    # This is a stub that could be expanded. For now, we return empty so it relies on the abstract.
    return ""

def ingest_papers(papers: list[dict]):
    """
    Ingests a list of paper dicts into ChromaDB.
    Expected paper dict keys: pmid, title, authors, journal, date, abstract, doi
    """
    if not papers:
        console.print("[yellow]No papers to ingest.[/yellow]")
        return

    try:
        existing_data = collection.get(include=[])
        existing_ids = set(existing_data["ids"])
    except Exception:
        existing_ids = set()

    documents = []
    metadatas = []
    ids = []

    for paper in papers:
        pmid = paper.get("pmid", "unknown")
        if pmid != "unknown" and f"pubmed_{pmid}_0" in existing_ids:
            console.print(f"[dim]Skipping PMID {pmid} (already in database)[/dim]")
            continue
            
        text_to_chunk = paper.get("abstract", "")
        # Fallback to title if abstract is missing
        if not text_to_chunk:
            text_to_chunk = paper.get("title", "")
            
        chunks = chunk_text(text_to_chunk)
        
        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({
                "pmid": paper.get("pmid", "unknown"),
                "title": paper.get("title", "unknown"),
                "journal": paper.get("journal", "unknown"),
                "date": paper.get("date", "unknown"),
                "doi": paper.get("doi", "unknown"),
                "source": "pubmed"
            })
            ids.append(f"pubmed_{paper.get('pmid', 'unknown')}_{i}")

    if documents:
        embeddings = embedding_model.encode(documents).tolist()
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        console.print(f"[green]Successfully ingested {len(documents)} chunks from {len(papers)} PubMed papers into ChromaDB.[/green]")

def ingest_internal_docs(docs_dir: str):
    """Ingests internal PDFs from a local directory."""
    if not os.path.exists(docs_dir):
        return
        
    pdf_files = glob.glob(os.path.join(docs_dir, "*.pdf"))
    if not pdf_files:
        return
        
    documents = []
    metadatas = []
    ids = []

    for pdf_file in pdf_files:
        text = extract_text_from_pdf(pdf_file)
        if not text:
            continue
            
        filename = os.path.basename(pdf_file)
        chunks = chunk_text(text)
        
        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({
                "pmid": "N/A",
                "title": filename,
                "journal": "Internal",
                "date": "N/A",
                "doi": "N/A",
                "source": "internal"
            })
            ids.append(f"internal_{filename}_{i}")
            
    if documents:
        embeddings = embedding_model.encode(documents).tolist()
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        console.print(f"[green]Successfully ingested {len(documents)} chunks from {len(pdf_files)} internal docs.[/green]")
