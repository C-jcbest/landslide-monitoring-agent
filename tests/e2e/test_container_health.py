"""Containerized API smoke tests without live LLM calls."""

import os

import httpx
import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("RUN_E2E") != "1",
        reason="requires docker-compose.test.yml; run make test-e2e",
    ),
]


def test_container_exposes_liveness_and_readiness_endpoints() -> None:
    """The built API container starts against migrated PostgreSQL without live model access."""
    base_url = os.getenv("API_BASE_URL", "http://localhost:58000")

    root = httpx.get(f"{base_url}/", timeout=10)
    readiness = httpx.get(f"{base_url}/health", timeout=10)
    api_health = httpx.get(f"{base_url}/api/v1/health", timeout=10)

    assert root.status_code == 200
    assert root.json()["status"] == "healthy"
    assert readiness.status_code == 200
    assert readiness.json()["components"]["database"] == "healthy"
    assert api_health.status_code == 200
