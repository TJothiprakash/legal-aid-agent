import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from observability.metrics import api_request_duration


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        duration = time.time() - start

        endpoint = request.url.path
        method   = request.method
        api_request_duration.labels(
            endpoint=endpoint,
            method=method,
        ).observe(duration)

        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Response-Time"] = str(round(duration, 3))
        return response