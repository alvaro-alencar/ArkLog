"""Tests for Ark Memory Protocol v1 schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.memory import ReportReviewRequest


def test_edited_review_requires_approved_content() -> None:
    with pytest.raises(ValidationError):
        ReportReviewRequest(verdict="edited", reason="Ajustar o tom")


def test_approved_review_rejects_replacement_content() -> None:
    with pytest.raises(ValidationError):
        ReportReviewRequest(
            verdict="approved",
            approved_content="conteúdo indevido",
        )


def test_review_normal_payload() -> None:
    payload = ReportReviewRequest(
        verdict="edited",
        approved_content="Relatório revisado.",
        reason="Menos adjetivos e mais fatos.",
        labels=["tom-executivo", "sem-inferencias"],
    )

    assert payload.verdict == "edited"
    assert payload.approved_content == "Relatório revisado."
    assert payload.labels == ["tom-executivo", "sem-inferencias"]
