"""Provider metadata and capability checks for the ArkLog flow engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.core.config import settings

ProviderRole = Literal["source", "destination"]


@dataclass(frozen=True)
class ProviderDefinition:
    id: str
    name: str
    description: str
    capabilities: tuple[ProviderRole, ...]
    source_resource_label: str = "Origem"
    destination_resource_label: str = "Destino"
    accent: str = "violet"

    def supports(self, role: ProviderRole) -> bool:
        return role in self.capabilities


PROVIDERS: dict[str, ProviderDefinition] = {
    "github": ProviderDefinition(
        id="github",
        name="GitHub",
        description="Commits, pull requests, issues, CI e releases dos repositórios escolhidos.",
        capabilities=("source",),
        source_resource_label="Repositório",
        accent="slate",
    ),
    "slack": ProviderDefinition(
        id="slack",
        name="Slack",
        description="Mensagens de canais como fonte e publicação de relatórios como destino.",
        capabilities=("source", "destination"),
        source_resource_label="Canal para leitura",
        destination_resource_label="Canal para publicação",
        accent="violet",
    ),
    "notion": ProviderDefinition(
        id="notion",
        name="Notion",
        description="Páginas e bases compartilhadas com a conexão do ArkLog.",
        capabilities=("source", "destination"),
        source_resource_label="Página ou base",
        destination_resource_label="Página ou base",
        accent="stone",
    ),
    "clickup": ProviderDefinition(
        id="clickup",
        name="ClickUp",
        description="Tarefas de uma lista como fonte e novos relatórios como tarefas.",
        capabilities=("source", "destination"),
        source_resource_label="Lista",
        destination_resource_label="Lista",
        accent="fuchsia",
    ),
    "trello": ProviderDefinition(
        id="trello",
        name="Trello",
        description="Cartões de quadros como fonte e criação de cartões em listas.",
        capabilities=("source", "destination"),
        source_resource_label="Quadro",
        destination_resource_label="Lista",
        accent="blue",
    ),
}


def provider_definition(provider: str) -> ProviderDefinition:
    try:
        return PROVIDERS[provider]
    except KeyError as exc:
        raise ValueError(f"Provider {provider} is not supported.") from exc


def provider_is_configured(provider: str) -> bool:
    configured = {
        "github": settings.github_app_configured,
        "slack": settings.slack_oauth_configured,
        "notion": settings.notion_oauth_configured,
        "clickup": settings.clickup_oauth_configured,
        "trello": settings.trello_oauth_configured,
    }
    return bool(configured.get(provider, False))


def public_provider_catalog() -> dict[str, dict]:
    return {
        provider_id: {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "capabilities": list(item.capabilities),
            "sourceResourceLabel": item.source_resource_label,
            "destinationResourceLabel": item.destination_resource_label,
            "accent": item.accent,
            "configured": provider_is_configured(provider_id),
        }
        for provider_id, item in PROVIDERS.items()
    }
