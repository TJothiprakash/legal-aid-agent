from typing import Optional
from pydantic import BaseModel


class AnalyzeResponse(BaseModel):
    analysis_id:       str
    document_type:     Optional[str]
    document_subtype:  Optional[str]
    risk_level:        Optional[str]
    confidence:        Optional[float]
    explanation:       dict
    key_clauses:       list
    flagged_clauses:   list
    action_items:      list
    parties:           list
    important_dates:   list
    rag_sources:       list
    web_search_used:   bool
    node_timings:      dict
    errors:            list
    detected_language: Optional[str]


class HealthResponse(BaseModel):
    status:  str
    version: str
    env:     str