"""Build SQL WHERE predicates for retrieval filters (including as-of)."""
from datetime import date
from typing import Dict, Tuple

def build_filters(filters: Dict) -> Tuple[str, Dict]:
    sql = ""
    params: Dict = {}
    if v := filters.get("framework"):
        sql += " AND framework = :framework"
        params["framework"] = v
    if v := filters.get("jurisdiction"):
        sql += " AND jurisdiction = :jurisdiction"
        params["jurisdiction"] = v
    if v := filters.get("doc_type"):
        sql += " AND doc_type = :doc_type"
        params["doc_type"] = v
    if v := filters.get("authority_level"):
        sql += " AND authority_level = :authority_level"
        params["authority_level"] = v
    if v := filters.get("as_of"):
        sql += " AND effective_date <= :as_of"
        params["as_of"] = v
    return sql, params
