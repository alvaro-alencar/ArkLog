"""
ArkLog - Context Builder

Assembles prompt context from project configuration and commit data.
Loads prompt templates from prompts/ and fills in observed values.

Hallucination prevention starts here: only data explicitly present in
the commit payload is injected into the prompt. Nothing is inferred.
"""

from pathlib import Path
from typing import Any

import structlog

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

_PERIOD_LABELS = {
    "backfill": "histórico completo do projeto (todos os commits)",
    "weekly_scheduled": "semana completa (desde o último relatório semanal)",
    "daily_scheduled": "período desde o último relatório diário",
}

def _period_label(trigger: str) -> str:
    return _PERIOD_LABELS.get(trigger, "atividade recente")

logger = structlog.get_logger(__name__)

_FALLBACK_TEMPLATES: dict[str, str] = {
    "report_executive.md": (
        "Project: {project_name}\n"
        "Description: {project_description}\n"
        "Stack: {tech_stack}\n"
        "Context: {business_context}\n"
        "Period: {period_start} to {period_end}\n"
        "Commits: {commit_count} | Files changed: {files_changed}\n"
        "Areas: {directories}\n\n"
        "Activity:\n{commit_summaries}"
    ),
    "report_technical.md": (
        "Project: {project_name}\n"
        "Stack: {tech_stack}\n"
        "Period: {period_start} to {period_end}\n"
        "Commits: {commit_count}\n\n"
        "Details:\n{commit_details}"
    ),
}


class ContextBuilder:
    """Builds structured prompt context for the AI report engine."""

    def build_context(self, payload: dict[str, Any]) -> str:
        """Route to the appropriate template based on report_style."""
        style = payload.get("report_style", "misto")
        if style == "executivo":
            return self._build_executive(payload)
        elif style == "tecnico":
            return self._build_technical(payload)
        return self._build_executive(payload) + "\n\n---\n\n" + self._build_technical(payload)

    def _build_executive(self, payload: dict[str, Any]) -> str:
        template = self._load_template("report_executive.md")
        commits = payload.get("commits", [])
        period = _period_label(payload.get("trigger", "webhook"))
        return template.format(
            project_name=payload.get("project_name", ""),
            project_description=payload.get("description", "Not specified"),
            tech_stack=", ".join(payload.get("tech_stack", [])) or "Not specified",
            business_context=payload.get("business_context", "Not specified"),
            period_start=period,
            period_end="hoje",
            commit_count=payload.get("commit_count", 0),
            files_changed=sum(c.get("files_changed", 0) for c in commits),
            directories=", ".join(sorted(self._unique_directories(commits))) or "root",
            commit_summaries=self._format_summaries(commits),
        )

    def _build_technical(self, payload: dict[str, Any]) -> str:
        template = self._load_template("report_technical.md")
        commits = payload.get("commits", [])
        period = _period_label(payload.get("trigger", "webhook"))
        return template.format(
            project_name=payload.get("project_name", ""),
            tech_stack=", ".join(payload.get("tech_stack", [])) or "Not specified",
            period_start=period,
            period_end="hoje",
            commit_count=payload.get("commit_count", 0),
            commit_details=self._format_details(commits),
        )

    def _format_summaries(self, commits: list[dict]) -> str:
        if not commits:
            return "No commits in this period."
        return "\n".join(
            f"- [{c.get('short_sha', '')}] {c.get('subject', '')} "
            f"(by {c.get('author', '')}) — areas: {', '.join(c.get('directories', [])) or 'root'}"
            for c in commits
        )

    def _format_details(self, commits: list[dict]) -> str:
        if not commits:
            return "No commits in this period."
        return "\n\n".join(
            f"**[{c.get('short_sha', '')}]** {c.get('subject', '')}\n"
            f"  Author: {c.get('author', '')} | "
            f"Files: {c.get('files_changed', 0)} | "
            f"Types: {', '.join(c.get('extensions', [])) or 'unknown'} | "
            f"Areas: {', '.join(c.get('directories', [])) or 'root'}"
            for c in commits
        )

    def _unique_directories(self, commits: list[dict]) -> set[str]:
        dirs: set[str] = set()
        for c in commits:
            dirs.update(c.get("directories", []))
        return dirs

    def _load_template(self, filename: str) -> str:
        path = PROMPTS_DIR / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        logger.warning("template_not_found", filename=filename, fallback="using built-in")
        return _FALLBACK_TEMPLATES[filename]
