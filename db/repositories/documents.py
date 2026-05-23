import json
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from db.client import get_supabase


def create_document(session_id: str, file_name: str, file_type: str) -> str:
    doc_id = str(uuid4())
    get_supabase().table("documents").insert({
        "id": doc_id,
        "session_id": session_id,
        "file_name": file_name,
        "file_type": file_type,
        "status": "pending",
    }).execute()
    return doc_id


def update_document(doc_id: str, data: dict) -> None:
    get_supabase().table("documents").update(data).eq("id", doc_id).execute()


def complete_document(doc_id: str, state: dict) -> None:
    get_supabase().table("documents").update({
        "document_type":    state.get("document_type"),
        "document_subtype": state.get("document_subtype"),
        "risk_level":       state.get("risk_level"),
        "raw_text":         state.get("raw_text", "")[:5000],
        "language":         state.get("detected_language", "en"),
        "explanation_en":   state.get("explanation_en"),
        "explanation_ta":   state.get("explanation_ta"),
        "analysis":         json.dumps(state.get("key_clauses", [])),
        "flagged_clauses":  json.dumps(state.get("flagged_clauses", [])),
        "action_items":     json.dumps(state.get("action_items", [])),
        "rag_sources":      json.dumps(state.get("rag_context", [])),
        "status":           "completed",
        "completed_at":     datetime.now(timezone.utc).isoformat(),
    }).eq("id", doc_id).execute()


def fail_document(doc_id: str, error: str) -> None:
    get_supabase().table("documents").update({
        "status": "failed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", doc_id).execute()


def get_document(doc_id: str) -> Optional[dict]:
    import re
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(uuid_pattern, doc_id, re.IGNORECASE):
        return None
    result = get_supabase().table("documents").select("*").eq("id", doc_id).execute()
    return result.data[0] if result.data else None