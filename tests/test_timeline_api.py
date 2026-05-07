"""Tests for the timeline and project listing endpoints."""

import pytest


@pytest.mark.asyncio
async def test_list_projects_empty(client):
    """Should return an empty list when no projects are configured."""
    response = await client.get("/api/v1/projects")
    assert response.status_code == 200
    data = response.json()
    assert "projects" in data
    assert "count" in data


@pytest.mark.asyncio
async def test_timeline_unknown_project(client):
    response = await client.get("/api/v1/projects/nonexistent-project-xyz/timeline")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reports_unknown_project(client):
    response = await client.get("/api/v1/projects/nonexistent-project-xyz/reports")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_analytics_summary_shape(client):
    response = await client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_projects" in data
    assert "total_commits" in data
    assert "total_reports" in data
    assert "projects" in data


@pytest.mark.asyncio
async def test_analytics_unknown_project(client):
    response = await client.get("/api/v1/analytics/projects/nonexistent-xyz/health")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_report_not_found(client):
    response = await client.get("/api/v1/reports/999999")
    assert response.status_code == 404
