import os
from fastapi import APIRouter
from fastapi.responses import Response
from api.schemas import HealthResponse
from observability.metrics import get_metrics_output

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        version="1.0.0",
        env=os.getenv("APP_ENV", "development"),
    )


@router.get("/metrics")
def metrics():
    data, content_type = get_metrics_output()
    return Response(content=data, media_type=content_type)