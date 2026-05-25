import httpx
from google.adk.tools import FunctionTool
from rich.console import Console

console = Console()

def score_target(target_gene: str, disease: str) -> dict:
    """
    Scores a candidate target gene by querying Open Targets for tractability/association and UniProt for protein function.
    Returns a score from 1-10 based on available evidence.
    """
    console.print(f"[cyan]Scoring target:[/cyan] {target_gene} for {disease}")
    
    result = {
        "gene": target_gene,
        "score": 0,
        "ot_score": "Score unavailable",
        "tractability": "Unknown",
        "protein_function": "Unknown",
        "uniprot_id": "Unknown"
    }
    
    score_components = []
    
    # 1. Open Targets API
    try:
        ot_url = "https://api.platform.opentargets.org/api/v4/graphql"
        query = """
        query targetSearch($queryString: String!) {
            search(queryString: $queryString, entityNames: ["target"]) {
                hits {
                    id
                    name
                    description
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
        response = httpx.post(ot_url, json={"query": query, "variables": {"queryString": target_gene}}, timeout=10.0)
        data = response.json()
        
        hits = data.get("data", {}).get("search", {}).get("hits", [])
        if hits:
            target_hit = hits[0]
            tractability = target_hit.get("tractability", {}) or {}
            sm = tractability.get("smallmolecule", {}) or {}
            ab = tractability.get("antibody", {}) or {}
            
            sm_buckets = sm.get("buckets", []) or []
            ab_buckets = ab.get("buckets", []) or []
            sm_hq = sm.get("highQualityMols", 0) or 0
            sm_top_bucket = sm.get("topBucket", 99) or 99
            
            if sm_buckets and any(sm_buckets):
                result["tractability"] = "Small Molecule Druggable"
                # Top bucket 1 or 2 = clinical drugs exist = max points
                if sm_top_bucket <= 2:
                    score_components.append(5)
                elif sm_top_bucket <= 4:
                    score_components.append(4)
                else:
                    score_components.append(2)
                # High quality molecules bonus
                if sm_hq > 0:
                    score_components.append(2)
            elif ab_buckets and any(ab_buckets):
                result["tractability"] = "Antibody Druggable"
                score_components.append(3)
            else:
                result["tractability"] = "Undruggable / Unknown"
                score_components.append(0)
                
            result["ot_score"] = f"{sm_top_bucket} (bucket, lower is better)"
    except Exception as e:
        console.print(f"[yellow]Open Targets API failed: {e}[/yellow]")
        
    # 2. UniProt REST API
    try:
        uniprot_url = f"https://rest.uniprot.org/uniprotkb/search?query=gene_exact:{target_gene}&format=json&size=1"
        response = httpx.get(uniprot_url, timeout=10.0)
        data = response.json()
        
        if "results" in data and len(data["results"]) > 0:
            protein = data["results"][0]
            result["uniprot_id"] = protein.get("primaryAccession", "Unknown")
            score_components.append(2)  # validated protein entry = evidence
            
            # Extract function from comments
            comments = protein.get("comments", [])
            for comment in comments:
                if comment.get("commentType") == "FUNCTION":
                    texts = comment.get("texts", [])
                    if texts:
                        result["protein_function"] = texts[0].get("value", "")[:200] + "..."
                        score_components.append(1)  # has functional annotation
                        break
    except Exception as e:
        console.print(f"[yellow]UniProt API failed: {e}[/yellow]")
        
    # Compute final 1-10 score
    raw = sum(score_components)
    result["score"] = min(10, max(1, raw))  # clamp 1-10
    console.print(f"[green]Score for {target_gene}:[/green] {result['score']}/10 (components: {score_components})")
        
    return result

score_target_tool = FunctionTool(func=score_target)
