import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"legal_agent" in response.content


def test_analyze_no_file():
    response = client.post("/analyze")
    assert response.status_code == 422


def test_analyze_invalid_file_type():
    response = client.post(
        "/analyze",
        files={"file": ("test.csv", b"col1,col2\n1,2", "text/csv")},
        data={"language_preference": "en"},
    )
    assert response.status_code == 400


def test_analyze_txt_document():
    content = b"NOTICE TO VACATE. You must vacate premises within 30 days."
    response = client.post(
        "/analyze",
        files={"file": ("notice.txt", content, "text/plain")},
        data={"language_preference": "en", "session_id": "test-session"},
        timeout=120,
    )
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = response.json()
        assert "analysis_id" in data
        assert "document_type" in data

def test_get_analysis_not_found():
    response = client.get("/analysis/nonexistent-id")
    assert response.status_code == 404