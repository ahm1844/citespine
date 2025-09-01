"""Re-ranking with cross-encoder for improved recall."""
from sentence_transformers import CrossEncoder
from typing import List, Dict, Any

_model = None

def get_model(name: str):
    """Get cached cross-encoder model."""
    global _model
    if _model is None:
        _model = CrossEncoder(name)
    return _model

def rerank(query: str, hits: List[Dict[str, Any]], model_name: str, top_k: int) -> List[Dict[str, Any]]:
    """Re-rank hits using cross-encoder and return top-k."""
    if not hits:
        return hits
    
    model = get_model(model_name)
    pairs = [(query, h["text"]) for h in hits]
    scores = model.predict(pairs, convert_to_numpy=True).tolist()
    
    # Add cross-encoder scores
    for h, s in zip(hits, scores):
        h["_ce"] = float(s)
    
    # Sort by cross-encoder score and return top-k
    hits.sort(key=lambda x: x.get("_ce", 0.0), reverse=True)
    return hits[:top_k]
