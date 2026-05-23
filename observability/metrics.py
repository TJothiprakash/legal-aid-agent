import os
import time
import requests
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from dotenv import load_dotenv

load_dotenv()

registry = CollectorRegistry()

# ── Counters ────────────────────────────────────────────────
agent_runs_total = Counter(
    "legal_agent_runs_total",
    "Total agent pipeline runs",
    ["status", "document_type"],
    registry=registry,
)

agent_flags_total = Counter(
    "legal_agent_flags_total",
    "Total flags raised",
    ["flag_type", "severity"],
    registry=registry,
)

rag_results_total = Counter(
    "legal_rag_results_total",
    "RAG results by source",
    ["source"],
    registry=registry,
)

web_search_total = Counter(
    "legal_web_search_total",
    "Web search fallback triggers",
    registry=registry,
)

# ── Histograms ───────────────────────────────────────────────
node_duration = Histogram(
    "legal_agent_node_duration_seconds",
    "Time spent in each agent node",
    ["node"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60],
    registry=registry,
)

pipeline_duration = Histogram(
    "legal_agent_pipeline_duration_seconds",
    "Total pipeline duration",
    buckets=[1, 5, 10, 30, 60, 120],
    registry=registry,
)

api_request_duration = Histogram(
    "legal_api_request_duration_seconds",
    "API endpoint response times",
    ["endpoint", "method"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
    registry=registry,
)

# ── Gauges ───────────────────────────────────────────────────
rag_chunks_used = Gauge(
    "legal_rag_chunks_used",
    "Number of RAG chunks used in last run",
    registry=registry,
)


# ── Helpers ──────────────────────────────────────────────────
def record_run(status: str, document_type: str, duration: float) -> None:
    agent_runs_total.labels(
        status=status,
        document_type=document_type or "unknown",
    ).inc()
    pipeline_duration.observe(duration)


def record_node_timing(timings: dict) -> None:
    for node, duration in timings.items():
        node_duration.labels(node=node).observe(duration)


def record_flags(flagged_clauses: list) -> None:
    for flag in flagged_clauses:
        agent_flags_total.labels(
            flag_type=flag.get("flag_type", "unknown"),
            severity=flag.get("severity", "low"),
        ).inc()


def record_rag(rag_context: list, web_used: bool) -> None:
    for chunk in rag_context:
        source = chunk.get("source", "vector")
        rag_results_total.labels(source=source).inc()
    rag_chunks_used.set(len(rag_context))
    if web_used:
        web_search_total.inc()


def get_metrics_output() -> tuple[bytes, str]:
    return generate_latest(registry), CONTENT_TYPE_LATEST


def push_to_grafana(job: str = "legal-aid") -> None:
    url      = os.getenv("GRAFANA_PROMETHEUS_URL")
    username = os.getenv("GRAFANA_PROMETHEUS_USERNAME")
    password = os.getenv("GRAFANA_PROMETHEUS_PASSWORD")

    if not url:
        return

    try:
        data = generate_latest(registry)
        push_url = f"{url}/metrics/job/{job}"
        requests.post(
            push_url,
            data=data,
            headers={"Content-Type": CONTENT_TYPE_LATEST},
            auth=(username, password),
            timeout=5,
        )
    except Exception:
        pass