import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

# Patch external deps before import
import sys
import types

# Stub redis module
redis_mod = types.ModuleType("redis")
redis_mod.asyncio = types.ModuleType("redis.asyncio")
sys.modules.setdefault("redis", redis_mod)
sys.modules.setdefault("redis.asyncio", redis_mod.asyncio)

import importlib
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_jobs.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("API_KEY", "test-key")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "api-gateway"))


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health_endpoint():
    """GET /health returns 200 and status ok"""
    with patch("redis.asyncio.from_url", new_callable=AsyncMock):
        from main import app, database, engine, metadata

        metadata.create_all(engine)
        await database.connect()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/health")

        await database.disconnect()
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


@pytest.mark.anyio
async def test_create_job_requires_auth():
    """POST /jobs without API key returns 422 (missing header)"""
    with patch("redis.asyncio.from_url", new_callable=AsyncMock):
        from main import app, database, engine, metadata

        metadata.create_all(engine)
        await database.connect()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(
                "/jobs",
                json={"subject": "Test", "body": "Hello", "recipients": ["a@example.com"]},
            )

        await database.disconnect()
        assert r.status_code == 422


@pytest.mark.anyio
async def test_create_job_wrong_key():
    """POST /jobs with wrong API key returns 401"""
    with patch("redis.asyncio.from_url", new_callable=AsyncMock):
        from main import app, database, engine, metadata

        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock(return_value="1-1")
        app.state.redis = mock_redis

        metadata.create_all(engine)
        await database.connect()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(
                "/jobs",
                json={"subject": "Test", "body": "Hello", "recipients": ["a@example.com"]},
                headers={"x-api-key": "wrong-key"},
            )

        await database.disconnect()
        assert r.status_code == 401


@pytest.mark.anyio
async def test_create_job_success():
    """POST /jobs with correct key creates a job"""
    with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_from_url:
        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock(return_value="1-1")
        mock_from_url.return_value = mock_redis

        from main import app, database, engine, metadata
        import main
        main.redis_client = mock_redis

        metadata.create_all(engine)
        await database.connect()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(
                "/jobs",
                json={
                    "subject": "Newsletter",
                    "body": "Hello subscribers!",
                    "recipients": ["user1@example.com", "user2@example.com"],
                },
                headers={"x-api-key": "test-key"},
            )

        await database.disconnect()
        assert r.status_code == 201
        data = r.json()
        assert data["subject"] == "Newsletter"
        assert data["status"] == "pending"
        assert data["recipients_count"] == 2


@pytest.mark.anyio
async def test_get_nonexistent_job():
    """GET /jobs/{id} for unknown id returns 404"""
    with patch("redis.asyncio.from_url", new_callable=AsyncMock):
        from main import app, database, engine, metadata

        metadata.create_all(engine)
        await database.connect()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get(
                "/jobs/nonexistent-id-000",
                headers={"x-api-key": "test-key"},
            )

        await database.disconnect()
        assert r.status_code == 404


@pytest.mark.anyio
async def test_empty_recipients_rejected():
    """POST /jobs with empty recipients list returns 422"""
    with patch("redis.asyncio.from_url", new_callable=AsyncMock):
        from main import app, database, engine, metadata

        metadata.create_all(engine)
        await database.connect()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(
                "/jobs",
                json={"subject": "Test", "body": "Hello", "recipients": []},
                headers={"x-api-key": "test-key"},
            )

        await database.disconnect()
        assert r.status_code == 422


@pytest.mark.anyio
async def test_metrics_endpoint():
    """GET /metrics returns Prometheus text format"""
    with patch("redis.asyncio.from_url", new_callable=AsyncMock):
        from main import app, database, engine, metadata

        metadata.create_all(engine)
        await database.connect()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/metrics")

        await database.disconnect()
        assert r.status_code == 200
        assert b"jobs_created_total" in r.content
