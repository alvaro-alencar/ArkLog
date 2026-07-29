"""Regression tests for the source-neutral LLM contract."""

from app.ai.context_builder import ContextBuilder
from app.integrations.runtime import _normalize_github_activity


def test_github_activity_is_normalized_before_the_llm() -> None:
    events = _normalize_github_activity(
        "ark/example",
        {
            "commits": [
                {
                    "subject": "Add secure flow",
                    "body": "Creates the connection vault.",
                    "author": "Álvaro",
                    "committed_at": "2026-07-29T12:00:00Z",
                    "short_sha": "abc1234",
                }
            ],
            "pull_requests": [
                {
                    "number": 7,
                    "title": "Connect providers",
                    "body": "GitHub to Slack",
                    "author": "Álvaro",
                    "state": "merged",
                    "merged_at": "2026-07-29T13:00:00Z",
                    "labels": ["feature"],
                }
            ],
            "issues": [],
            "workflow_runs": [
                {
                    "name": "CI",
                    "status": "completed",
                    "conclusion": "success",
                    "created_at": "2026-07-29T13:10:00Z",
                    "branch": "main",
                    "commit_subject": "Connect providers",
                }
            ],
            "releases": [],
        },
    )

    assert [event["type"] for event in events] == ["change", "review", "automation"]
    assert all(event["source"] == "github" for event in events)
    assert events[1]["reference"] == "PR #7"


def test_context_builder_accepts_non_github_normalized_events() -> None:
    context = ContextBuilder().build_context(
        {
            "project_name": "Decisões da equipe",
            "source_provider": "notion",
            "source_label": "Workspace Produto",
            "trigger": "manual_flow",
            "report_style": "executivo",
            "business_context": "Destaque decisões e pendências.",
            "normalized_events": [
                {
                    "type": "decision",
                    "source": "notion",
                    "container": "Workspace Produto",
                    "title": "Publicação aprovada",
                    "description": "A versão será enviada na sexta-feira.",
                    "actor": "Equipe",
                    "status": "approved",
                    "occurred_at": "2026-07-29T14:00:00Z",
                    "reference": "Página Roadmap",
                }
            ],
        }
    )

    assert "Fonte:** notion" in context
    assert "Publicação aprovada" in context
    assert "Pull Requests" not in context
    assert "Commits" not in context
