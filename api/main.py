import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.middleware import TimingMiddleware
from api.routes.health import router as health_router
from api.routes.analyze import router as analyze_router
from db.client import get_supabase

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_supabase()
    print(f"[startup] Legal Aid API ready — env={os.getenv('APP_ENV')}")
    yield
    print("[shutdown] Legal Aid API shutting down")


app = FastAPI(
    title="Legal Aid Agent",
    version="1.0.0",
    description="Understand legal documents in plain language",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TimingMiddleware)

app.include_router(health_router, tags=["health"])
app.include_router(analyze_router, tags=["analyze"])