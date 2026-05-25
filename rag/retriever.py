import os
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer
from rich.console import Console

console = Console()

CHROMA_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
client = PersistentClient(path=CHROMA_DB_DIR)

# Load embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def search_rag(query: str, n_results: int = 5) -> list[dict]:
    """
    Queries ChromaDB for the most relevant chunks.
    Returns a list of dicts containing text and metadata.
    """
    try:
        collection = client.get_collection(name="pharma_papers")
    except Exception as e:
        console.print(f"[yellow]ChromaDB collection not found or empty: {e}[/yellow]")
        return []

    query_embedding = embedding_model.encode([query]).tolist()

    try:
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )
    except Exception as e:
        console.print(f"[red]Error querying ChromaDB: {e}[/red]")
        return []

    output = []
    if not results or not results.get("documents") or not results["documents"][0]:
        return output

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for doc, meta, dist in zip(documents, metadatas, distances):
        # Convert distance to a similarity score roughly between 0 and 1
        score = 1.0 - dist if dist < 1.0 else 0.0
        
        output.append({
            "text": doc,
            "pmid": meta.get("pmid", "N/A"),
            "title": meta.get("title", "N/A"),
            "source": meta.get("source", "unknown"),
            "score": round(score, 3)
        })

    return output
