"""
ArkLog - AI Report Generator

Calls the configured AI model (OpenAI / OpenRouter) with the assembled
prompt context and returns the generated report content.

Anti-hallucination measures:
- Temperature 0.3: factual, grounded, low creativity
- System prompt explicitly forbids inventing details
- Context builder only injects observed data (never inferred)
"""

from typing import Any

import structlog

from app.ai.context_builder import ContextBuilder
from app.ai.openai_client import get_openai_client
from app.core.config import settings

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """Você é um gerente técnico sênior gerando relatórios de progresso de projetos de software.

Regras obrigatórias:
- Escreva SEMPRE em português do Brasil (pt-BR)
- Descreva apenas o que está explicitamente presente nos dados de commits fornecidos
- Nunca invente nomes de arquivos, funcionalidades ou detalhes técnicos não mencionados no contexto
- Seja específico e concreto — evite frases como "progresso sendo feito" ou "várias melhorias"
- Escreva como um gerente de engenharia experiente comunicando para stakeholders de negócio
- Se os dados forem escassos ou ausentes, reconheça isso honestamente em vez de inflar o relatório
- Densidade máxima de informação por frase: cada frase deve carregar um fato específico"""


class ReportGenerator:
    """Generates AI-powered progress reports from commit context."""

    def __init__(self) -> None:
        self._context_builder = ContextBuilder()

    async def generate(self, payload: dict[str, Any]) -> tuple[str, str]:
        """
        Generate a report from a commit batch payload.
        Returns (full_content, summary) where summary is the first paragraph.
        """
        project_name = payload.get("project_name", "unknown")
        style = payload.get("report_style", "misto")
        prompt = self._context_builder.build_context(payload)

        logger.info("report_generation_start", project=project_name, style=style)

        client = get_openai_client()
        response = await client.chat.completions.create(
            model=settings.ai_model,
            max_tokens=settings.ai_max_tokens,
            temperature=settings.ai_temperature,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        content = response.choices[0].message.content or ""
        summary = content.split("\n\n")[0] if content else ""

        logger.info(
            "report_generation_complete",
            project=project_name,
            tokens=response.usage.total_tokens if response.usage else 0,
            chars=len(content),
        )

        return content, summary
