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
    category: str
    source_resource_label: str = "Origem"
    destination_resource_label: str = "Destino"
    accent: str = "violet"
    implemented: bool = True

    def supports(self, role: ProviderRole) -> bool:
        return role in self.capabilities


PROVIDERS: dict[str, ProviderDefinition] = {
    "github": ProviderDefinition(
        id="github",
        name="GitHub",
        description="Commits, pull requests, issues, CI e releases dos repositórios escolhidos.",
        capabilities=("source",),
        category="Código",
        source_resource_label="Repositório",
        accent="slate",
    ),
    "slack": ProviderDefinition(
        id="slack",
        name="Slack",
        description="Mensagens de canais como fonte e publicação de relatórios como destino.",
        capabilities=("source", "destination"),
        category="Comunicação",
        source_resource_label="Canal para leitura",
        destination_resource_label="Canal para publicação",
        accent="violet",
    ),
    "notion": ProviderDefinition(
        id="notion",
        name="Notion",
        description="Páginas e bases compartilhadas com a conexão do ArkLog.",
        capabilities=("source", "destination"),
        category="Conhecimento",
        source_resource_label="Página ou base",
        destination_resource_label="Página ou base",
        accent="stone",
    ),
    "clickup": ProviderDefinition(
        id="clickup",
        name="ClickUp",
        description="Tarefas de uma lista como fonte e novos relatórios como tarefas.",
        capabilities=("source", "destination"),
        category="Projetos",
        source_resource_label="Lista",
        destination_resource_label="Lista",
        accent="fuchsia",
    ),
    "trello": ProviderDefinition(
        id="trello",
        name="Trello",
        description="Cartões de quadros como fonte e criação de cartões em listas.",
        capabilities=("source", "destination"),
        category="Projetos",
        source_resource_label="Quadro",
        destination_resource_label="Lista",
        accent="blue",
    ),
    "gitlab": ProviderDefinition(
        id="gitlab",
        name="GitLab",
        description="Commits, merge requests, issues, pipelines e releases dos projetos.",
        capabilities=("source",),
        category="Código",
        source_resource_label="Projeto",
        accent="orange",
        implemented=False,
    ),
    "bitbucket": ProviderDefinition(
        id="bitbucket",
        name="Bitbucket",
        description="Commits, pull requests e pipelines dos repositórios selecionados.",
        capabilities=("source",),
        category="Código",
        source_resource_label="Repositório",
        accent="blue",
        implemented=False,
    ),
    "azure-devops": ProviderDefinition(
        id="azure-devops",
        name="Azure DevOps",
        description="Repos, pull requests, boards, builds e releases da organização.",
        capabilities=("source",),
        category="Código",
        source_resource_label="Projeto",
        accent="blue",
        implemented=False,
    ),
    "jira": ProviderDefinition(
        id="jira",
        name="Jira",
        description="Issues e sprints como fonte; relatórios publicados em tickets.",
        capabilities=("source", "destination"),
        category="Projetos",
        source_resource_label="Projeto",
        destination_resource_label="Projeto",
        accent="blue",
        implemented=False,
    ),
    "linear": ProviderDefinition(
        id="linear",
        name="Linear",
        description="Issues e cycles como fonte; relatórios em issues ou projetos.",
        capabilities=("source", "destination"),
        category="Projetos",
        source_resource_label="Equipe",
        destination_resource_label="Equipe",
        accent="violet",
        implemented=False,
    ),
    "asana": ProviderDefinition(
        id="asana",
        name="Asana",
        description="Tarefas e marcos como fonte; atualizações publicadas em projetos.",
        capabilities=("source", "destination"),
        category="Projetos",
        source_resource_label="Projeto",
        destination_resource_label="Projeto",
        accent="rose",
        implemented=False,
    ),
    "monday": ProviderDefinition(
        id="monday",
        name="Monday.com",
        description="Boards e itens como fonte; atualizações e relatórios como destino.",
        capabilities=("source", "destination"),
        category="Projetos",
        source_resource_label="Board",
        destination_resource_label="Board",
        accent="rose",
        implemented=False,
    ),
    "google-drive": ProviderDefinition(
        id="google-drive",
        name="Google Drive",
        description="Documentos como fonte e relatórios arquivados em pastas compartilhadas.",
        capabilities=("source", "destination"),
        category="Conhecimento",
        source_resource_label="Pasta",
        destination_resource_label="Pasta",
        accent="emerald",
        implemented=False,
    ),
    "google-calendar": ProviderDefinition(
        id="google-calendar",
        name="Google Calendar",
        description="Eventos, agendas e marcos de projeto usados como contexto temporal.",
        capabilities=("source",),
        category="Conhecimento",
        source_resource_label="Agenda",
        accent="blue",
        implemented=False,
    ),
    "confluence": ProviderDefinition(
        id="confluence",
        name="Confluence",
        description="Páginas e espaços como fonte; relatórios publicados na documentação.",
        capabilities=("source", "destination"),
        category="Conhecimento",
        source_resource_label="Espaço",
        destination_resource_label="Espaço",
        accent="blue",
        implemented=False,
    ),
    "airtable": ProviderDefinition(
        id="airtable",
        name="Airtable",
        description="Bases e registros como fonte; resultados gravados em tabelas.",
        capabilities=("source", "destination"),
        category="Conhecimento",
        source_resource_label="Base",
        destination_resource_label="Base",
        accent="cyan",
        implemented=False,
    ),
    "microsoft-teams": ProviderDefinition(
        id="microsoft-teams",
        name="Microsoft Teams",
        description="Mensagens de canais como fonte e publicação dos relatórios.",
        capabilities=("source", "destination"),
        category="Comunicação",
        source_resource_label="Canal",
        destination_resource_label="Canal",
        accent="indigo",
        implemented=False,
    ),
    "discord": ProviderDefinition(
        id="discord",
        name="Discord",
        description="Mensagens de canais como fonte e relatórios enviados por bot.",
        capabilities=("source", "destination"),
        category="Comunicação",
        source_resource_label="Canal",
        destination_resource_label="Canal",
        accent="indigo",
        implemented=False,
    ),
    "hubspot": ProviderDefinition(
        id="hubspot",
        name="HubSpot",
        description="Negócios, atividades e tickets transformados em contexto executivo.",
        capabilities=("source", "destination"),
        category="CRM e suporte",
        source_resource_label="Pipeline",
        destination_resource_label="Pipeline",
        accent="orange",
        implemented=False,
    ),
    "salesforce": ProviderDefinition(
        id="salesforce",
        name="Salesforce",
        description="Oportunidades e atividades como fonte; registros atualizados pelo fluxo.",
        capabilities=("source", "destination"),
        category="CRM e suporte",
        source_resource_label="Objeto",
        destination_resource_label="Objeto",
        accent="blue",
        implemented=False,
    ),
    "zendesk": ProviderDefinition(
        id="zendesk",
        name="Zendesk",
        description="Tickets e métricas de suporte como fonte; notas publicadas em tickets.",
        capabilities=("source", "destination"),
        category="CRM e suporte",
        source_resource_label="Fila",
        destination_resource_label="Fila",
        accent="emerald",
        implemented=False,
    ),
    "intercom": ProviderDefinition(
        id="intercom",
        name="Intercom",
        description="Conversas e eventos de clientes resumidos em relatórios acionáveis.",
        capabilities=("source", "destination"),
        category="CRM e suporte",
        source_resource_label="Workspace",
        destination_resource_label="Workspace",
        accent="blue",
        implemented=False,
    ),
    "sentry": ProviderDefinition(
        id="sentry",
        name="Sentry",
        description="Erros, regressões, releases e alertas de performance como fonte.",
        capabilities=("source",),
        category="Operações",
        source_resource_label="Projeto",
        accent="violet",
        implemented=False,
    ),
    "datadog": ProviderDefinition(
        id="datadog",
        name="Datadog",
        description="Monitores, incidentes e métricas de observabilidade como fonte.",
        capabilities=("source",),
        category="Operações",
        source_resource_label="Serviço",
        accent="violet",
        implemented=False,
    ),
    "vercel": ProviderDefinition(
        id="vercel",
        name="Vercel",
        description="Deploys, previews, falhas de build e releases dos projetos.",
        capabilities=("source",),
        category="Operações",
        source_resource_label="Projeto",
        accent="slate",
        implemented=False,
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
            "category": item.category,
            "sourceResourceLabel": item.source_resource_label,
            "destinationResourceLabel": item.destination_resource_label,
            "accent": item.accent,
            "implemented": item.implemented,
            "configured": provider_is_configured(provider_id),
        }
        for provider_id, item in PROVIDERS.items()
    }
