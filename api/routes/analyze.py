import time
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from api.schemas import AnalyzeResponse
from agent.graph import run_pipeline
from db.repositories.documents import get_document
from observability.metrics import (
    record_run,
    record_node_timing,
    record_flags,
    record_rag,
    push_to_grafana,
)
from observability.langfuse_client import create_trace, log_span, flush

router = APIRouter()

ALLOWED_TYPES = {
    "application/pdf":  "pdf",
    "image/jpeg":       "jpg",
    "image/png":        "png",
    "text/plain":       "txt",
}


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file:                UploadFile = File(...),
    language_preference: str        = Form(default="en"),
    session_id:          str        = Form(default=""),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, JPEG, PNG, TXT",
        )

    if not session_id:
        session_id = str(uuid.uuid4())

    if language_preference not in ("en", "ta"):
        language_preference = "en"

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB.")

    file_type = ALLOWED_TYPES[file.content_type]
    start     = time.time()

    try:
        result = run_pipeline(
            file_bytes=file_bytes,
            file_name=file.filename or "document",
            file_type=file_type,
            session_id=session_id,
            language_preference=language_preference,
        )

        duration = time.time() - start

        record_run(
            status="success",
            document_type=result.get("document_type", "unknown"),
            duration=duration,
        )
        record_node_timing(result.get("node_timings", {}))
        record_flags(result.get("flagged_clauses", []))
        record_rag(result.get("rag_sources", []), result.get("web_search_used", False))
        push_to_grafana()

        trace = create_trace(
            document_id=result["analysis_id"],
            session_id=session_id,
            document_type=result.get("document_type", ""),
            language=result.get("detected_language", "en"),
        )
        log_span(
            trace,
            name="pipeline_complete",
            output_data={
                "risk_level":    result.get("risk_level"),
                "flags_count":   len(result.get("flagged_clauses", [])),
                "duration":      round(duration, 3),
            },
        )
        flush()

        return AnalyzeResponse(**result)

    except Exception as e:
        duration = time.time() - start
        record_run(status="error", document_type="unknown", duration=duration)
        push_to_grafana()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{analysis_id}", response_model=AnalyzeResponse)
def get_analysis(analysis_id: str):
    doc = get_document(analysis_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Analysis not found")

    import json

    def _parse(val):
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return val
        return val or []

    return AnalyzeResponse(
        analysis_id=doc["id"],
        document_type=doc.get("document_type"),
        document_subtype=doc.get("document_subtype"),
        risk_level=doc.get("risk_level"),
        confidence=None,
        explanation={
            "en": _parse(doc.get("explanation_en")),
            "ta": _parse(doc.get("explanation_ta")),
        },
        key_clauses=_parse(doc.get("analysis")),
        flagged_clauses=_parse(doc.get("flagged_clauses")),
        action_items=_parse(doc.get("action_items")),
        parties=[],
        important_dates=[],
        rag_sources=_parse(doc.get("rag_sources")),
        web_search_used=False,
        node_timings={},
        errors=[],
        detected_language=doc.get("language"),
    )