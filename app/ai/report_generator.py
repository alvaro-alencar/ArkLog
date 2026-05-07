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
- Use formatação Markdown: ## para títulos, ### para subtítulos, **negrito** para destaques, *itálico* para ênfase
- Seja CONCISO — corte toda frase que não adiciona informação nova. Sem enrolação.
- Descreva apenas o que está explicitamente presente nos dados de commits
- Nunca invente arquivos, funcionalidades ou detalhes técnicos não mencionados
- Evite frases genéricas ("progresso sendo feito", "melhorias diversas", "avanços significativos")
- Se os dados forem escassos, reconheça honestamente — não infle o relatório
- Cada frase deve carregar um fato específico e verificável"""

BACKFILL_SYSTEM_PROMPT = """Você é um arquiteto de software sênior gerando um relatório histórico completo de um projeto.

Este é o PRIMEIRO relatório do projeto no ArkLog, cobrindo TODA a história de desenvolvimento até hoje.

Regras obrigatórias:
- Escreva SEMPRE em português do Brasil (pt-BR)
- Use formatação Markdown rica: ## títulos, ### subtítulos, **negrito**, *itálico*, listas com -
- Seja DETALHADO e ABRANGENTE — este relatório deve capturar toda a evolução do projeto
- Organize cronologicamente ou por fases/épocas de desenvolvimento quando identificável
- Identifique padrões: quais áreas receberam mais atenção, quais funcionalidades foram construídas, como a arquitetura evoluiu
- Destaque decisões técnicas relevantes visíveis nos commits
- Identifique o estado atual do projeto com base nos commits mais recentes
- Nunca invente detalhes não presentes nos commits
- Cada afirmação deve ser rastreável a commits reais listados
- Use seções claras para facilitar leitura por stakeholders técnicos e não-técnicos"""


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
        trigger = payload.get("trigger", "webhook")
        is_backfill = trigger == "backfill"

        prompt = self._context_builder.build_context(payload)
        system_prompt = BACKFILL_SYSTEM_PROMPT if is_backfill else SYSTEM_PROMPT
        max_tokens = settings.ai_max_tokens_backfill if is_backfill else settings.ai_max_tokens

        logger.info(
            "report_generation_start",
            project=project_name,
            style=style,
            trigger=trigger,
            max_tokens=max_tokens,
        )

        client = get_openai_client()
        response = await client.chat.completions.create(
            model=settings.ai_model,
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
