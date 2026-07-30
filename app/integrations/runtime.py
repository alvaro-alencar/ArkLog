"""Provider-agnostic runtime dispatcher for ArkLog flows."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Awaitable, Callable

from sqlalchemy import update

from app.integrations.catalog import provider_definition
from app.integrations.providers import clickup, github, notion, slack, trello
from app.integrations.providers.common import ProviderRuntimeError
from app.models.database import AsyncSessionLocal
from app.models.tables import IntegrationConnectionRecord
from app.security.credentials import decrypt_credentials, encrypt_credentials

IntegrationRuntimeError = ProviderRuntimeError

ResourceLister = Callable[[dict[str, Any], str], Awaitable[list[dict[str, Any]]]]
SourceCollector = Callable[..., Awaitable[dict[str, Any]]]
DestinationPublisher = Callable[..., Awaitable[dict[str, Any]]]

_RESOURCE_LISTERS: dict[str, ResourceLister] = {
    "github": github.list_resources,
    "slack": slack.list_resources,
    "notion": notion.list_resources,
    "clickup": clickup.list_resources,
    "trello": trello.list_resources,
}

_SOURCE_COLLECTORS: dict[str, SourceCollector] = {
    "github": github.collect,
    "slack": slack.collect,
    "notion": notion.collect,
    "clickup": clickup.collect,
    "trello": trello.collect,
}

_DESTINATION_PUBLISHERS: dict[str, DestinationPublisher] = {
    "slack": slack.publish,
    "notion": notion.publish,
    "clickup": clickup.publish,
    "trello": trello.publish,
}


def _normalize_github_activity(
    source_label: str, activity: dict[str, Any]
) -> list[dict[str, Any]]:
    """Compatibility shim for callers predating the provider adapter split."""
    return github._normalize(source_label, activity)


def _credentials(connection: IntegrationConnectionRecord) -> dict[str, Any]:
    values = decrypt_credentials(connection.encrypted_credentials)
    values["_scopes"] = list(connection.scopes or [])
    return values


async def _persist_if_changed(
    connection: IntegrationConnectionRecord, credentials: dict[str, Any]
) -> None:
    if not credentials.pop("_dirty", False):
        return
    clean = {
        key: value
        for key, value in credentials.items()
        if not key.startswith("_")
    }
    encrypted = encrypt_credentials(clean)
    async with AsyncSessionLocal() as session, session.begin():
        await session.execute(
            update(IntegrationConnectionRecord)
            .where(IntegrationConnectionRecord.id == connection.id)
            .values(encrypted_credentials=encrypted)
        )


async def list_connection_resources(
    connection: IntegrationConnectionRecord,
    role: str = "source",
) -> list[dict[str, Any]]:
    try:
        definition = provider_definition(connection.provider)
    except ValueError as exc:
        raise ProviderRuntimeError(str(exc)) from exc
    if role not in {"source", "destination"}:
        raise ProviderRuntimeError("A função da conexão é inválida.")
    if not definition.supports(role):
        return []
    lister = _RESOURCE_LISTERS.get(connection.provider)
    if lister is None:
        raise ProviderRuntimeError(
            f"{definition.name} ainda não possui seletor de recursos."
        )
    credentials = _credentials(connection)
    try:
        resources = await lister(credentials, role)
    finally:
        await _persist_if_changed(connection, credentials)
    return [item for item in resources if item.get("id")]


async def validate_connection_resource(
    connection: IntegrationConnectionRecord,
    role: str,
    resource_id: str,
) -> dict[str, Any]:
    normalized = resource_id.strip()
    if not normalized:
        raise ProviderRuntimeError("Escolha um recurso para esta conexão.")
    resources = await list_connection_resources(connection, role)
    selected = next(
        (
            item
            for item in resources
            if str(item.get("id") or "").casefold() == normalized.casefold()
        ),
        None,
    )
    if selected is None:
        raise ProviderRuntimeError(
            "O recurso escolhido não está mais disponível nesta conexão."
        )
    if not selected.get("available", True):
        reason = str(selected.get("availabilityReason") or "").strip()
        raise ProviderRuntimeError(
            reason or "O recurso escolhido ainda não está pronto para uso."
        )
    return selected


async def collect_source(
    connection: IntegrationConnectionRecord,
    config: dict[str, Any],
    *,
    since: datetime | None,
    trial_limits: bool,
) -> dict[str, Any]:
    try:
        definition = provider_definition(connection.provider)
    except ValueError as exc:
        raise ProviderRuntimeError(str(exc)) from exc
    if not definition.supports("source"):
        raise ProviderRuntimeError(
            f"{definition.name} não está disponível como fonte."
        )
    collector = _SOURCE_COLLECTORS.get(connection.provider)
    if collector is None:
        raise ProviderRuntimeError(
            f"A leitura de {definition.name} ainda não foi implementada."
        )
    credentials = _credentials(connection)
    try:
        result = await collector(
            credentials,
            config,
            since=since,
            trial_limits=trial_limits,
        )
    finally:
        await _persist_if_changed(connection, credentials)
    return result


async def publish_destination(
    connection: IntegrationConnectionRecord,
    config: dict[str, Any],
    content: str,
    *,
    title: str,
    idempotency_key: str,
) -> dict[str, Any]:
    try:
        definition = provider_definition(connection.provider)
    except ValueError as exc:
        raise ProviderRuntimeError(str(exc)) from exc
    if not definition.supports("destination"):
        raise ProviderRuntimeError(
            f"{definition.name} não está disponível como destino."
        )
    publisher = _DESTINATION_PUBLISHERS.get(connection.provider)
    if publisher is None:
        raise ProviderRuntimeError(
            f"A publicação em {definition.name} ainda não foi implementada."
        )
    credentials = _credentials(connection)
    try:
        result = await publisher(
            credentials,
            config,
            title=title,
            content=content,
            idempotency_key=idempotency_key,
        )
    finally:
        await _persist_if_changed(connection, credentials)
    return result
