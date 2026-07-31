"""Regression tests for flow editing and cloning helpers."""

from app.api.v1.routes.operations import _clone_name, _resource_config


def test_resource_config_uses_provider_truth_instead_of_browser_labels() -> None:
    config = _resource_config(
        {
            "id": "C123",
            "name": "canal-real",
            "label": "#canal-real",
            "type": "channel",
        },
        "browser-value",
    )

    assert config == {
        "resourceId": "C123",
        "resourceLabel": "#canal-real",
        "resourceType": "channel",
    }


def test_resource_config_has_safe_fallbacks() -> None:
    config = _resource_config(
        {"id": "page-1", "name": "Página operacional"},
        "page",
    )

    assert config["resourceLabel"] == "Página operacional"
    assert config["resourceType"] == "page"


def test_clone_name_is_predictable_and_collision_free() -> None:
    existing = {
        "Relatório semanal",
        "Relatório semanal · cópia",
        "Relatório semanal · cópia 2",
    }

    assert _clone_name("Relatório diário", existing) == "Relatório diário · cópia"
    assert _clone_name("Relatório semanal", existing) == "Relatório semanal · cópia 3"
