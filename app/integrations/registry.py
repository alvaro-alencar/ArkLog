"""
ArkLog - Integration Registry

Static catalog of every integration ArkLog supports (or plans to support).
Each entry defines auth type, config fields, setup instructions, and direction.
Publishers/sources read this at runtime to know what credentials to expect.
"""

from dataclasses import dataclass, field


@dataclass
class ConfigField:
    key: str            # key in the credentials JSON
    label: str          # UI label
    type: str           # "password" | "url" | "text" | "email"
    instructions: str   # step-by-step shown in modal
    help_url: str = ""  # deep link to the API key page


@dataclass
class IntegrationDef:
    slug: str
    name: str
    description: str
    direction: str              # "source" | "destination" | "both"
    auth_type: str              # "api_key" | "oauth" | "webhook_url" | "bot_token" | "smtp"
    config_fields: list[ConfigField] = field(default_factory=list)
    implemented: bool = False   # False → shown as "coming soon" in UI
    category: str = ""
    color: str = "#6366f1"      # card accent color
    oauth_path: str = ""        # e.g. "/api/v1/auth/login/github"
    emoji: str = "🔌"           # fallback icon


INTEGRATIONS: dict[str, IntegrationDef] = {

    # ── Version Control ─────────────────────────────────────────────────────
    "github": IntegrationDef(
        slug="github", name="GitHub", category="Código",
        direction="source", auth_type="oauth",
        oauth_path="/api/v1/auth/login/github",
        description="Commits, PRs, Issues, CI runs e Releases em tempo real.",
        config_fields=[], implemented=True,
        color="#24292e", emoji="🐙",
    ),
    "gitlab": IntegrationDef(
        slug="gitlab", name="GitLab", category="Código",
        direction="source", auth_type="api_key",
        description="Commits, Merge Requests, Issues e Pipelines.",
        config_fields=[ConfigField(
            "api_token", "API Token", "password",
            "User Settings → Access Tokens → Create token com escopo read_api",
            "https://gitlab.com/-/profile/personal_access_tokens",
        )],
        implemented=False, color="#fc6d26", emoji="🦊",
    ),
    "bitbucket": IntegrationDef(
        slug="bitbucket", name="Bitbucket", category="Código",
        direction="source", auth_type="api_key",
        description="Commits, Pull Requests e Pipelines.",
        config_fields=[
            ConfigField("username", "Username", "text", "Seu username do Bitbucket"),
            ConfigField(
                "app_password", "App Password", "password",
                "Account Settings → App passwords → Create → marque Repositories:Read",
                "https://bitbucket.org/account/settings/app-passwords/",
            ),
        ],
        implemented=False, color="#0052cc", emoji="🪣",
    ),
    "azure_repos": IntegrationDef(
        slug="azure_repos", name="Azure Repos", category="Código",
        direction="source", auth_type="api_key",
        description="Commits, PRs e Builds do Azure DevOps.",
        config_fields=[
            ConfigField("organization", "Organização", "text", "Nome da sua org no Azure DevOps"),
            ConfigField(
                "pat", "Personal Access Token", "password",
                "Azure DevOps → User settings → Personal access tokens → New Token (Code:Read)",
                "https://dev.azure.com",
            ),
        ],
        implemented=False, color="#0078d4", emoji="☁️",
    ),

    # ── Project Management ───────────────────────────────────────────────────
    "clickup": IntegrationDef(
        slug="clickup", name="ClickUp", category="Tarefas",
        direction="both", auth_type="api_key",
        description="Tarefas concluídas como fonte; relatórios como comentário em tarefa.",
        config_fields=[ConfigField(
            "api_token", "API Token", "password",
            "Settings → Apps → Generate Token → copie o valor",
            "https://app.clickup.com/settings/apps",
        )],
        implemented=True, color="#7b68ee", emoji="✅",
    ),
    "jira": IntegrationDef(
        slug="jira", name="Jira", category="Tarefas",
        direction="both", auth_type="api_key",
        description="Tickets, sprints e velocity como fonte; comentário em ticket como destino.",
        config_fields=[
            ConfigField("domain", "Domínio Jira", "text", "Ex: minhaempresa.atlassian.net"),
            ConfigField("email", "E-mail da conta", "email", "Seu e-mail de login no Jira"),
            ConfigField(
                "api_token", "API Token", "password",
                "id.atlassian.com → Security → API tokens → Create",
                "https://id.atlassian.com/manage-profile/security/api-tokens",
            ),
        ],
        implemented=False, color="#0052cc", emoji="🎯",
    ),
    "linear": IntegrationDef(
        slug="linear", name="Linear", category="Tarefas",
        direction="both", auth_type="api_key",
        description="Issues e cycles como fonte; comentário em issue como destino.",
        config_fields=[ConfigField(
            "api_key", "API Key", "password",
            "Settings → API → Personal API Keys → Create key",
            "https://linear.app/settings/api",
        )],
        implemented=False, color="#5e6ad2", emoji="⚡",
    ),
    "notion": IntegrationDef(
        slug="notion", name="Notion", category="Tarefas",
        direction="both", auth_type="api_key",
        description="Páginas e databases como fonte; cria/atualiza página como destino.",
        config_fields=[
            ConfigField(
                "api_token", "Integration Token", "password",
                "notion.so/my-integrations → New integration → copie o token",
                "https://www.notion.so/my-integrations",
            ),
            ConfigField(
                "database_id", "ID do Database (destino)", "text",
                "Abra o database no Notion → copie o ID da URL (32 chars)",
            ),
        ],
        implemented=False, color="#000000", emoji="📝",
    ),
    "asana": IntegrationDef(
        slug="asana", name="Asana", category="Tarefas",
        direction="both", auth_type="api_key",
        description="Tarefas e milestones como fonte; comentário como destino.",
        config_fields=[ConfigField(
            "personal_access_token", "Personal Access Token", "password",
            "app.asana.com → Minha conta → Apps → Manage developer apps → New access token",
            "https://app.asana.com/0/my-apps",
        )],
        implemented=False, color="#f06a6a", emoji="🌿",
    ),
    "trello": IntegrationDef(
        slug="trello", name="Trello", category="Tarefas",
        direction="both", auth_type="api_key",
        description="Cards e boards como fonte; comentário em card como destino.",
        config_fields=[
            ConfigField("api_key", "API Key", "text", "Copie em trello.com/app-key", "https://trello.com/app-key"),
            ConfigField("api_token", "Token", "password", "Na mesma página, clique em Token", "https://trello.com/app-key"),
        ],
        implemented=False, color="#0079bf", emoji="📋",
    ),
    "monday": IntegrationDef(
        slug="monday", name="Monday.com", category="Tarefas",
        direction="both", auth_type="api_key",
        description="Boards e items como fonte; atualização de item como destino.",
        config_fields=[ConfigField(
            "api_token", "API Token", "password",
            "monday.com → Perfil → Administração → Conexões → API → Copiar token pessoal",
            "https://monday.com/apps/manage/tokens",
        )],
        implemented=False, color="#ff3d57", emoji="📅",
    ),

    # ── CI/CD & Deploy ──────────────────────────────────────────────────────
    "vercel": IntegrationDef(
        slug="vercel", name="Vercel", category="Deploy",
        direction="source", auth_type="api_key",
        description="Deploys, previews e build status.",
        config_fields=[ConfigField(
            "api_token", "API Token", "password",
            "vercel.com/account/tokens → Create",
            "https://vercel.com/account/tokens",
        )],
        implemented=False, color="#000000", emoji="▲",
    ),
    "netlify": IntegrationDef(
        slug="netlify", name="Netlify", category="Deploy",
        direction="source", auth_type="api_key",
        description="Deploys e funções serverless.",
        config_fields=[ConfigField(
            "api_token", "Personal Access Token", "password",
            "app.netlify.com → User settings → Applications → New access token",
            "https://app.netlify.com/user/applications",
        )],
        implemented=False, color="#00c7b7", emoji="🌐",
    ),
    "railway": IntegrationDef(
        slug="railway", name="Railway", category="Deploy",
        direction="source", auth_type="api_key",
        description="Deployments e logs de serviços.",
        config_fields=[ConfigField(
            "api_token", "API Token", "password",
            "railway.app → Account Settings → Tokens → Create",
            "https://railway.app/account/tokens",
        )],
        implemented=False, color="#0b0d0e", emoji="🚂",
    ),

    # ── Monitoring ──────────────────────────────────────────────────────────
    "sentry": IntegrationDef(
        slug="sentry", name="Sentry", category="Monitoramento",
        direction="source", auth_type="api_key",
        description="Novos erros, regressões, alertas de performance e releases.",
        config_fields=[
            ConfigField(
                "auth_token", "Auth Token", "password",
                "sentry.io → Settings → Auth Tokens → Create token",
                "https://sentry.io/settings/account/api/auth-tokens/",
            ),
            ConfigField("organization", "Slug da organização", "text", "Ex: minha-empresa (visível na URL)"),
        ],
        implemented=False, color="#362d59", emoji="🛡️",
    ),
    "datadog": IntegrationDef(
        slug="datadog", name="Datadog", category="Monitoramento",
        direction="source", auth_type="api_key",
        description="Alertas, monitors disparados e métricas de APM.",
        config_fields=[
            ConfigField("api_key", "API Key", "password", "app.datadoghq.com → Organization settings → API Keys", "https://app.datadoghq.com/organization-settings/api-keys"),
            ConfigField("app_key", "Application Key", "password", "Mesma página → Application Keys"),
        ],
        implemented=False, color="#632ca6", emoji="🐶",
    ),
    "pagerduty": IntegrationDef(
        slug="pagerduty", name="PagerDuty", category="Monitoramento",
        direction="source", auth_type="api_key",
        description="Incidentes abertos e resolvidos.",
        config_fields=[ConfigField(
            "api_token", "API Token", "password",
            "app.pagerduty.com → Integrations → API Access Keys → Create",
            "https://app.pagerduty.com/api_keys",
        )],
        implemented=False, color="#06ac38", emoji="🚨",
    ),

    # ── Messaging (destinations) ─────────────────────────────────────────────
    "slack": IntegrationDef(
        slug="slack", name="Slack", category="Mensagens",
        direction="destination", auth_type="webhook_url",
        description="Relatório enviado como mensagem em qualquer canal.",
        config_fields=[ConfigField(
            "webhook_url", "Incoming Webhook URL", "url",
            "api.slack.com/apps → Seu app → Incoming Webhooks → Add New Webhook → copie a URL",
            "https://api.slack.com/apps",
        )],
        implemented=True, color="#4a154b", emoji="💬",
    ),
    "discord": IntegrationDef(
        slug="discord", name="Discord", category="Mensagens",
        direction="destination", auth_type="webhook_url",
        description="Relatório enviado num canal de servidor via webhook.",
        config_fields=[ConfigField(
            "webhook_url", "Webhook URL", "url",
            "Servidor → Configurações do canal → Integrações → Webhooks → Criar webhook → Copiar URL",
            "https://support.discord.com/hc/en-us/articles/228383668",
        )],
        implemented=True, color="#5865f2", emoji="🎮",
    ),
    "telegram": IntegrationDef(
        slug="telegram", name="Telegram", category="Mensagens",
        direction="destination", auth_type="bot_token",
        description="Relatório enviado por bot em chat privado ou grupo.",
        config_fields=[
            ConfigField("bot_token", "Bot Token", "password", "Abra @BotFather → /newbot → copie o token"),
            ConfigField(
                "chat_id", "Chat ID", "text",
                "Envie /start ao bot, então acesse: api.telegram.org/bot{SEU_TOKEN}/getUpdates → copie o id",
            ),
        ],
        implemented=True, color="#229ed9", emoji="✈️",
    ),
    "email": IntegrationDef(
        slug="email", name="E-mail", category="Mensagens",
        direction="destination", auth_type="smtp",
        description="Relatório enviado para qualquer endereço via SMTP.",
        config_fields=[
            ConfigField("to", "Destinatário", "email", "Endereço de e-mail que receberá os relatórios"),
            ConfigField("smtp_host", "Servidor SMTP", "text", "Ex: smtp.gmail.com"),
            ConfigField("smtp_port", "Porta", "text", "587 (TLS recomendado) ou 465 (SSL)"),
            ConfigField("smtp_user", "Usuário", "email", "Seu e-mail de envio"),
            ConfigField(
                "smtp_password", "Senha / App Password", "password",
                "Para Gmail: myaccount.google.com → Segurança → Senhas de app → Gerar",
                "https://myaccount.google.com/apppasswords",
            ),
        ],
        implemented=True, color="#ea4335", emoji="📧",
    ),
    "teams": IntegrationDef(
        slug="teams", name="Microsoft Teams", category="Mensagens",
        direction="destination", auth_type="webhook_url",
        description="Relatório enviado num canal do Teams via conector.",
        config_fields=[ConfigField(
            "webhook_url", "Incoming Webhook URL", "url",
            "Canal → ⋯ → Conectores → Incoming Webhook → Configurar → copie a URL",
        )],
        implemented=False, color="#6264a7", emoji="🟦",
    ),
    "whatsapp": IntegrationDef(
        slug="whatsapp", name="WhatsApp Business", category="Mensagens",
        direction="destination", auth_type="api_key",
        description="Relatório enviado via Meta Business API.",
        config_fields=[
            ConfigField("access_token", "Access Token", "password", "developers.facebook.com → App → WhatsApp → API Setup"),
            ConfigField("phone_number_id", "Phone Number ID", "text", "ID do número no painel Meta"),
            ConfigField("to", "Número destinatário", "text", "Formato: 5511999999999 (sem + ou espaços)"),
        ],
        implemented=False, color="#25d366", emoji="📱",
    ),

    # ── Automation / Generic ─────────────────────────────────────────────────
    "webhook": IntegrationDef(
        slug="webhook", name="Webhook Genérico", category="Automação",
        direction="destination", auth_type="webhook_url",
        description="HTTP POST para qualquer URL — n8n, Zapier, Make ou sistema próprio.",
        config_fields=[
            ConfigField("url", "URL do Webhook", "url", "https://…"),
            ConfigField(
                "secret", "Secret (opcional)", "password",
                "Incluído no header X-ArkLog-Secret para validação na outra ponta",
            ),
        ],
        implemented=True, color="#f59e0b", emoji="🔗",
    ),

    # ── Documentation ────────────────────────────────────────────────────────
    "confluence": IntegrationDef(
        slug="confluence", name="Confluence", category="Documentação",
        direction="destination", auth_type="api_key",
        description="Cria ou atualiza página com o relatório.",
        config_fields=[
            ConfigField("domain", "Domínio", "text", "Ex: minhaempresa.atlassian.net"),
            ConfigField("email", "E-mail", "email", "Seu e-mail de login"),
            ConfigField("api_token", "API Token", "password", "id.atlassian.com → Security → API tokens", "https://id.atlassian.com/manage-profile/security/api-tokens"),
            ConfigField("space_key", "Space Key", "text", "Chave do espaço Confluence (ex: DEV)"),
            ConfigField("parent_page_id", "ID da página pai", "text", "ID da página onde criar os relatórios"),
        ],
        implemented=False, color="#0052cc", emoji="📚",
    ),

    # ── Design ───────────────────────────────────────────────────────────────
    "figma": IntegrationDef(
        slug="figma", name="Figma", category="Design",
        direction="source", auth_type="api_key",
        description="Versões de arquivo, comentários e handoffs.",
        config_fields=[ConfigField(
            "access_token", "Personal Access Token", "password",
            "figma.com → Account Settings → Personal access tokens → Create",
            "https://www.figma.com/settings",
        )],
        implemented=False, color="#f24e1e", emoji="🎨",
    ),
    "canny": IntegrationDef(
        slug="canny", name="Canny", category="Design",
        direction="source", auth_type="api_key",
        description="Feature requests, votos e status do roadmap.",
        config_fields=[ConfigField(
            "api_key", "API Key", "password",
            "canny.io → Settings → API → Copiar API Key",
            "https://canny.io/api",
        )],
        implemented=False, color="#4f9cf9", emoji="💡",
    ),
}


def get(slug: str) -> IntegrationDef | None:
    """Return an integration definition by slug."""
    return INTEGRATIONS.get(slug)


def list_all() -> list[IntegrationDef]:
    return list(INTEGRATIONS.values())


def list_by_direction(direction: str) -> list[IntegrationDef]:
    """Filter by 'source', 'destination', or 'both'."""
    return [
        i for i in INTEGRATIONS.values()
        if i.direction == direction or i.direction == "both"
    ]


def list_by_category() -> dict[str, list[IntegrationDef]]:
    result: dict[str, list[IntegrationDef]] = {}
    for intg in INTEGRATIONS.values():
        result.setdefault(intg.category, []).append(intg)
    return result
