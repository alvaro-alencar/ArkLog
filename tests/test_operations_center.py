"""Regression tests for the ArkLog operations center."""

from app.api.v1.routes.operations import _connection_check, _resource_check
from app.api.v1.routes.reports import _to_summary
from app.models.tables import ReportRecord
from app.utils.datetime_utils import naive_utcnow


def test_report_summary_uses_provider_neutral_item_count() -> None:
    record = ReportRecord(
        id=7,
        trigger="manual_flow",
        status="published",
        content="conteúdo",
        summary="resumo",
        commit_count=13,
        flow_id=4,
        project_id=None,
        generated_at=naive_utcnow(),
    )

    summary = _to_summary(
        record,
        {
            "name": "Fluxo operacional",
            "kind": "flow",
            "source": "notion",
            "destination": "slack",
        },
    )

    assert summary.item_count == 13
    assert summary.commit_count == 13
    assert summary.owner_kind == "flow"
    assert summary.source_provider == "notion"
    assert summary.destination_provider == "slack"


def test_connection_check_counts_ready_and_unavailable_resources() -> None:
    check = _connection_check(
        "destination",
        [
            {"id": "A", "available": True},
            {"id": "B", "available": False},
            {"id": "C"},
        ],
    )

    assert check["ready"] is True
    assert check["resourceCount"] == 3
    assert check["availableCount"] == 2
    assert check["unavailableCount"] == 1


def test_resource_check_never_exposes_credentials() -> None:
    check = _resource_check(
        "source",
        "github",
        {"id": "ark/repo", "label": "ark/repo", "token": "secret"},
    )

    assert check == {
        "role": "source",
        "provider": "github",
        "ready": True,
        "resourceId": "ark/repo",
        "resourceLabel": "ark/repo",
        "message": "Recurso acessível e pronto para uso.",
    }
