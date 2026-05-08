"""
ArkLog - AI Report Generator

Calls the configured AI model (OpenAI / OpenRouter) with the assembled
prompt context and returns the generated report content.

Triggers e comportamento:
  webhook          → relatório conciso dos commits do push
  daily_scheduled  → relatório diário; infere fase se sem commits
  weekly_scheduled → relatório semanal detalhado da semana
  backfill         → análise histórica abrangente de todo o projeto
"""

from typing import Any

import structlog

from app.ai.context_builder import ContextBuilder
from app.ai.openai_client import get_openai_client
from app.core.config import settings

logger = structlog.get_logger(__name__)

_PROMPT_BASE = """Você é um gerente técnico sênior gerando relatórios de progresso de projetos de software.

Você receberá dados completos de atividade do GitHub: commits, pull requests, issues, \
execuções de CI/CD e releases. Use TODOS os dados disponíveis — não apenas commits.

Regras obrigatórias:
- Escreva SEMPRE em português do Brasil (pt-BR)
- Use formatação Markdown: ## para títulos, ### para subtítulos, **negrito** para destaques, *itálico* para ênfase
- Descreva apenas o que está explicitamente presente nos dados fornecidos
- Nunca invente arquivos, funcionalidades ou detalhes técnicos não mencionados
- Evite frases genéricas ("progresso sendo feito", "melhorias diversas", "avanços significativos")
- Cada frase deve carregar um fato específico e verificável
- PRs mergeados, issues fechadas e releases publicadas são sinais tão importantes quanto commits

Quando não há atividade no período:
- Se o contexto ou descrição do projeto oferecem evidências claras do estado atual, \
descreva esse estado com confiança — é uma inferência justa e útil
- Se não há evidências suficientes, informe objetivamente: \
"O projeto encontra-se em fase de planejamento e definição de novas tarefas neste período\""""

SYSTEM_PROMPT = _PROMPT_BASE + """

- Seja CONCISO — corte toda frase que não adiciona informação nova. Máximo 150 palavras."""

WEEKLY_SYSTEM_PROMPT = _PROMPT_BASE + """

- Seja DETALHADO — este é o relatório semanal que será revisado antes de ir ao contratante
- Organize por área ou tema quando houver múltiplos commits em domínios diferentes
- Destaque o que foi concluído, o que está em andamento e o que pode estar pendente
- Máximo 400 palavras"""

BACKFILL_SYSTEM_PROMPT = """Você é um arquiteto de software sênior gerando um relatório histórico completo de um projeto.

Este é o PRIMEIRO relatório do projeto no ArkLog, cobrindo TODA a história de desenvolvimento até hoje.

Regras obrigatórias:
- Escreva SEMPRE em português do Brasil (pt-BR)
- Use formatação Markdown rica: ## títulos, ### subtítulos, **negrito**, *itálico*, listas com -
- Seja DETALHADO e ABRANGENTE — capture toda a evolução do projeto
- Organize cronologicamente ou por fases/épocas quando identificável
- Identifique padrões: áreas com mais atenção, funcionalidades construídas, evolução da arquitetura
- Destaque decisões técnicas relevantes visíveis nos commits
- Descreva o estado atual com base nos commits mais recentes
- Nunca invente detalhes não presentes nos commits
- Cada afirmação rastreável a commits reais"""

_PROMPTS = {
    "backfill": (BACKFILL_SYSTEM_PROMPT, "ai_max_tokens_backfill"),
    "weekly_scheduled": (WEEKLY_SYSTEM_PROMPT, "ai_max_tokens_backfill"),
}


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

        system_prompt, tokens_attr = _PROMPTS.get(trigger, (SYSTEM_PROMPT, "ai_max_tokens"))
        max_tokens = getattr(settings, tokens_attr)

        prompt = self._context_builder.build_context(payload)

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
