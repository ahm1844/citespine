"""Metric computations for retrieval quality."""
from typing import List, Dict

def recall_at_k(results: List[List[str]], gold: List[List[str]], k: int = 10) -> float:
    """results: list of predicted chunk_id lists per query; gold: list of gold chunk_id lists per query."""
    assert len(results) == len(gold)
    hits = 0
    for preds, truth in zip(results, gold):
        preds_k = set(preds[:k])
        truth_set = set(truth)
        if truth_set and preds_k.intersection(truth_set):
            hits += 1
    return hits / max(1, len(results))
