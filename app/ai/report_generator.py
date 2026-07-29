"""AI report generation with server-side cost controls."""

from typing import Any

import structlog

from app.ai.context_builder import ContextBuilder
from app.ai.openai_client import get_openai_client
from app.core.config import settings

logger = structlog.get_logger(__name__)

_PROMPT_BASE = """Você é um gerente sênior transformando atividade operacional em um relatório de progresso.

Você receberá eventos coletados e normalizados pelo ArkLog. Eles podem vir de GitHub, Slack, Notion, ClickUp ou outros conectores.
Use apenas os dados fornecidos, independentemente da plataforma de origem.

Regras obrigatórias:
- Escreva sempre em português do Brasil
- Use Markdown com títulos e destaques moderados
- Nunca invente arquivos, funcionalidades, decisões, responsáveis ou resultados
- Cada afirmação deve ser verificável nos eventos recebidos
- Separe o que foi concluído, o que está em andamento e possíveis pendências somente quando houver evidência
"""

SYSTEM_PROMPT = _PROMPT_BASE + "\n- Seja conciso. Máximo 220 palavras."
WEEKLY_SYSTEM_PROMPT = _PROMPT_BASE + "\n- Seja detalhado. Máximo 400 palavras."
BACKFILL_SYSTEM_PROMPT = _PROMPT_BASE + "\n- Organize a evolução histórica. Máximo 800 palavras."
TRIAL_SYSTEM_PROMPT = _PROMPT_BASE + "\n- Este é um relatório demonstrativo. Máximo 180 palavras."

_PROMPTS = {
    "backfill": (BACKFILL_SYSTEM_PROMPT, "ai_max_tokens_backfill"),
    "weekly_scheduled": (WEEKLY_SYSTEM_PROMPT, "ai_max_tokens_backfill"),
}


class ReportGenerator:
    def __init__(self) -> None:
        self._context_builder = ContextBuilder()

    async def generate(self, payload: dict[str, Any]) -> tuple[str, str]:
        project_name = payload.get("project_name", "unknown")
        trigger = payload.get("trigger", "webhook")
        access_status = payload.get("access_status", "ACTIVE")
        is_trial = access_status == "TRIAL"

        if is_trial:
            system_prompt = TRIAL_SYSTEM_PROMPT
            max_tokens = settings.ai_trial_max_tokens
            model = settings.ai_trial_model
            prompt_limit = settings.ai_trial_max_prompt_chars
        else:
            system_prompt, tokens_attr = _PROMPTS.get(
                trigger, (SYSTEM_PROMPT, "ai_max_tokens")
            )
            max_tokens = getattr(settings, tokens_attr)
            model = settings.ai_model
            prompt_limit = settings.ai_max_prompt_chars

        prompt = self._context_builder.build_context(payload)
        if len(prompt) > prompt_limit:
            prompt = prompt[:prompt_limit] + "\n\n[Contexto truncado pelo limite de segurança do ArkLog.]"

        logger.info(
            "report_generation_start",
            project=project_name,
            trigger=trigger,
            access_status=access_status,
            model=model,
            max_tokens=max_tokens,
            prompt_chars=len(prompt),
        )

        client = get_openai_client()
        response = await client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=settings.ai_temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        summary = content.split("\n\n")[0] if content else ""
        logger.info(
            "report_generation_complete",
            project=project_name,
            trigger=trigger,
            tokens=response.usage.total_tokens if response.usage else 0,
            chars=len(content),
        )
        return content, summary
