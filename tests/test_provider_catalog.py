"""Regression tests for the provider-agnostic flow catalog."""

from app.api.v1.routes.flows import _normalized_config
from app.integrations.catalog import provider_definition


def test_provider_capabilities_are_independent() -> None:
    assert provider_definition("github").capabilities == ("source",)
    for provider in ("slack", "notion", "clickup", "trello"):
        definition = provider_definition(provider)
        assert definition.supports("source")
        assert definition.supports("destination")


def test_legacy_github_slack_flow_configs_are_normalized() -> None:
    source = _normalized_config(
        {"repository": "ark/example"}, "github", "source"
    )
    destination = _normalized_config(
        {"channel": "C123", "channelLabel": "#relatorios"},
        "slack",
        "destination",
    )

    assert source == {
        "resourceId": "ark/example",
        "resourceLabel": "ark/example",
        "resourceType": "repository",
        "options": {},
    }
    assert destination["resourceId"] == "C123"
    assert destination["resourceLabel"] == "#relatorios"
    assert destination["resourceType"] == "channel"
