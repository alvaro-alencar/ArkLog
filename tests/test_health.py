"""Tests for health check endpoints."""

import pytest


@pytest.mark.asyncio
async def test_liveness(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "uptime_seconds" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "ArkLog"
    assert data["status"] == "operational"


@pytest.mark.asyncio
async def test_detailed_health(client):
    response = await client.get("/api/v1/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert "components" in data
    assert "database" in data["components"]
