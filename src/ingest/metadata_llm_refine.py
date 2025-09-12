from __future__ import annotations
import os, json
from typing import Callable, Optional

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from ..api.schemas_metadata import MetadataExtraction
from ..common.logging import get_logger

log = get_logger("metadata_llm_refine")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
PROMPT = """You are a compliance metadata arbiter. Choose the BEST values ONLY when the current confidence is low or there are conflicts.
Return STRICT JSON: {{"framework":"","jurisdiction":"","doc_type":"","authority_level":"","effective_date":"","version":"","explanations":{{"field":"quoted evidence sentence"}}}}

Controlled values:
framework: IFRS|US_GAAP|Other
jurisdiction: US|EU|UK|Global|Other
doc_type: standard|release|order|manual|guidelines|policy|filing|memo|qna|staff_alert
authority_level: authoritative|interpretive|internal_policy

Context:
Current draft: {draft}
Evidence snippets (per field): {evidence}
"""

async def llm_refine(draft: MetadataExtraction) -> MetadataExtraction:
    """Optional LLM refinement for low-confidence metadata fields"""
    if not HTTPX_AVAILABLE:
        log.warning("httpx not available for LLM refinement")
        return draft
    
    try:
        # Build compact evidence payload
        ev = {}
        for name in ["framework","jurisdiction","doc_type","authority_level","effective_date","version"]:
            f = getattr(draft, name)
            ev[name] = [e.text for e in (f.evidence or [])][:3]

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": PROMPT.format(draft=draft.model_dump(), evidence=json.dumps(ev)),
            "stream": False,
            "options": {"temperature": 0.0}
        }
        
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
            r.raise_for_status()
            resp = r.json().get("response","{}")
        
        try:
            # Extract JSON from response
            start = resp.find("{")
            end = resp.rfind("}") + 1
            if start >= 0 and end > start:
                j = json.loads(resp[start:end])
            else:
                log.warning("No JSON found in LLM response")
                return draft
        except json.JSONDecodeError as e:
            log.warning(f"Failed to parse LLM response as JSON: {e}")
            return draft

        # Only overwrite fields that were low confidence
        for k in ["framework","jurisdiction","doc_type","authority_level","effective_date","version"]:
            f = getattr(draft, k)
            if f.confidence < 0.80 and j.get(k):
                f.value = j[k]
                f.confidence = 0.85
                f.method = "llm"
                log.info(f"LLM refined {k}: {j[k]}")
        
        return draft
        
    except Exception as e:
        log.warning(f"LLM refinement failed: {e}")
        return draft
