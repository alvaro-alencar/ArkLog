"""Tests for the AI report generator and context builder. OpenAI is fully mocked."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.context_builder import ContextBuilder
from app.ai.report_generator import ReportGenerator


@pytest.fixture
def sample_payload() -> dict[str, Any]:
    return {
        "project_name": "SmartEAD",
        "description": "Plataforma de educação adaptativa com IA",
        "tech_stack": ["Python", "FastAPI", "React"],
        "business_context": "Sistema de ensino online para escolas.",
        "report_style": "executivo",
        "commit_count": 2,
        "commits": [
            {
                "short_sha": "abc1234",
                "subject": "feat: add authentication module",
                "author": "Alvaro Alencar",
                "files_changed": 4,
                "directories": ["app/auth"],
                "extensions": ["py"],
            }
        ],
    }


def test_context_contains_project_name(sample_payload):
    ctx = ContextBuilder().build_context(sample_payload)
    assert "SmartEAD" in ctx


def test_context_contains_commit_count(sample_payload):
    ctx = ContextBuilder().build_context(sample_payload)
    assert "2" in ctx


def test_executive_contains_business_context(sample_payload):
    ctx = ContextBuilder()._build_executive(sample_payload)
    assert "ensino online" in ctx


def test_technical_contains_stack(sample_payload):
    ctx = ContextBuilder()._build_technical(sample_payload)
    assert "FastAPI" in ctx


def test_misto_combines_sections(sample_payload):
    sample_payload["report_style"] = "misto"
    ctx = ContextBuilder().build_context(sample_payload)
    assert "---" in ctx


def test_empty_commits_handled_gracefully(sample_payload):
    sample_payload["commits"] = []
    ctx = ContextBuilder().build_context(sample_payload)
    assert "Nenhum commit no período" in ctx


def _make_mock_response(text: str) -> MagicMock:
    response = MagicMock()
    response.choices[0].message.content = text
    response.usage.total_tokens = len(text.split())
    return response


@pytest.mark.asyncio
async def test_generate_returns_content_and_summary(sample_payload):
    text = "Auth infrastructure was established.\n\nToken refresh logic was added."
    with patch("app.ai.report_generator.get_openai_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_make_mock_response(text))
        mock_get.return_value = mock_client
        content, summary = await ReportGenerator().generate(sample_payload)

    assert content == text
    assert summary == "Auth infrastructure was established."


@pytest.mark.asyncio
async def test_generate_single_paragraph(sample_payload):
    text = "Single paragraph, no breaks."
    with patch("app.ai.report_generator.get_openai_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_make_mock_response(text))
        mock_get.return_value = mock_client
        content, summary = await ReportGenerator().generate(sample_payload)

    assert summary == content


@pytest.mark.asyncio
async def test_generate_passes_correct_temperature(sample_payload):
    with patch("app.ai.report_generator.get_openai_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_mock_response("Report.")
        )
        mock_get.return_value = mock_client
        await ReportGenerator().generate(sample_payload)
        kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert kwargs["temperature"] == 0.3
