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

SYSTEM_PROMPT = """You are a senior technical program manager generating software project progress reports.

Critical rules:
- Only describe what is explicitly present in the provided commit data
- Never invent file names, features, or technical details not mentioned in the context
- Be specific and concrete — avoid phrases like \"making progress\" or \"various improvements\"
- Write as an experienced engineering manager communicating to business stakeholders
- If data is sparse or absent, acknowledge it honestly rather than padding the report
- Maximum density of information per sentence: every sentence must carry a specific fact"""


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
            model=settings.openai_model,
            max_tokens=settings.openai_max_tokens,
            temperature=settings.openai_temperature,
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
