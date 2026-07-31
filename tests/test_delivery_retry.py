"""Regression tests for no-cost report delivery retries."""

from datetime import timedelta
from uuid import UUID

from app.api.v1.routes.deliveries import (
    _delivery_idempotency_key,
    _latest_publication,
    _pending_is_fresh,
)
from app.models.tables import ReportPublicationRecord
from app.utils.datetime_utils import naive_utcnow


def _publication(
    publication_id: int,
    status: str,
    *,
    age_minutes: int = 0,
) -> ReportPublicationRecord:
    return ReportPublicationRecord(
        id=publication_id,
        platform="slack",
        target_id="C123",
        status=status,
        report_id=8,
        published_at=naive_utcnow() - timedelta(minutes=age_minutes),
    )


def test_retry_idempotency_key_is_stable_provider_safe_uuid() -> None:
    first = _delivery_idempotency_key(8, "C123")
    second = _delivery_idempotency_key(8, "C123")
    other_target = _delivery_idempotency_key(8, "C999")

    assert first == second
    assert first != other_target
    assert str(UUID(first)) == first
    assert len(first) == 36


def test_latest_publication_preserves_audit_history() -> None:
    publications = [
        _publication(2, "failed"),
        _publication(9, "success"),
        _publication(5, "failed"),
    ]

    assert _latest_publication(publications).id == 9
    assert _latest_publication([]) is None


def test_only_recent_pending_attempt_blocks_another_retry() -> None:
    assert _pending_is_fresh(_publication(1, "pending", age_minutes=1)) is True
    assert _pending_is_fresh(_publication(2, "pending", age_minutes=10)) is False
    assert _pending_is_fresh(_publication(3, "failed", age_minutes=1)) is False
