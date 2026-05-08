"""
ArkLog - Context Builder

Assembles prompt context from project metadata and GitHub activity data
(commits, PRs, issues, CI runs, releases). Only data explicitly present
in the payload is injected — nothing is inferred or invented.
"""

from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_PERIOD_LABELS = {
    "backfill": "histórico completo do projeto (todos os commits)",
    "weekly_scheduled": "semana completa (desde o último relatório semanal)",
    "daily_scheduled": "período desde o último relatório diário",
}


def _period_label(trigger: str) -> str:
    return _PERIOD_LABELS.get(trigger, "atividade recente")


class ContextBuilder:
    """Builds structured prompt context for the AI report engine."""

    def build_context(self, payload: dict[str, Any]) -> str:
        style = payload.get("report_style", "misto")
        if style == "executivo":
            return self._build_executive(payload)
        elif style == "tecnico":
            return self._build_technical(payload)
        return self._build_executive(payload) + "\n\n---\n\n" + self._build_technical(payload)

    # ------------------------------------------------------------------
    # Executive view
    # ------------------------------------------------------------------

    def _build_executive(self, payload: dict[str, Any]) -> str:
        period = _period_label(payload.get("trigger", "webhook"))
        lines = [
            "## Contexto do Projeto",
            f"- **Projeto:** {payload.get('project_name', '')}",
            f"- **Descrição:** {payload.get('description', 'Não especificada')}",
            f"- **Stack:** {', '.join(payload.get('tech_stack', [])) or 'Não especificada'}",
            f"- **Contexto de negócio:** {payload.get('business_context', 'Não especificado')}",
            f"- **Período:** {period}",
            "",
            self._section_commits_summary(payload.get("commits", [])),
            self._section_prs(payload.get("pull_requests", [])),
            self._section_issues(payload.get("issues", [])),
            self._section_workflows(payload.get("workflow_runs", [])),
            self._section_releases(payload.get("releases", [])),
            "",
            "## Instrução",
            "",
            "Gere um **relatório executivo de progresso** em pt-BR com a seguinte estrutura Markdown:",
            "",
            "```",
            "## Status",
            "",
            "[Uma frase declarativa sobre o estado atual do projeto.]",
            "",
            "### O que Evoluiu",
            "",
            "[Bullet points curtos descrevendo as mudanças em linguagem de negócio.]",
            "",
            "### Impacto",
            "",
            "[O que essas mudanças significam para o produto ou stakeholders. Omita se não houver dados.]",
            "",
            "### Próximos Passos *(opcional)*",
            "",
            "[Apenas se houver continuidade clara nos dados. Omita se não houver.]",
            "```",
            "",
            "**Regras:** máximo 200 palavras. Sem frases genéricas. Se não houver atividade, infira a fase "
            "atual pelo contexto do projeto. Retorne APENAS o relatório formatado.",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Technical view
    # ------------------------------------------------------------------

    def _build_technical(self, payload: dict[str, Any]) -> str:
        lines = [
            "## Contexto do Projeto",
            f"- **Projeto:** {payload.get('project_name', '')}",
            f"- **Stack:** {', '.join(payload.get('tech_stack', [])) or 'Não especificada'}",
            "",
            self._section_commits_detail(payload.get("commits", [])),
            self._section_prs(payload.get("pull_requests", [])),
            self._section_issues(payload.get("issues", [])),
            self._section_workflows(payload.get("workflow_runs", [])),
            self._section_releases(payload.get("releases", [])),
            "",
            "## Instrução",
            "",
            "Gere um **relatório técnico de progresso** em pt-BR com a seguinte estrutura Markdown:",
            "",
            "```",
            "## Alterações Técnicas",
            "",
            "[Bullet points objetivos: o que foi construído, modificado ou mergeado.]",
            "",
            "### Decisões de Arquitetura *(opcional)*",
            "",
            "[Padrões introduzidos, refatorações, mudanças de design. Omita se não houver.]",
            "",
            "### CI/CD & Qualidade *(opcional)*",
            "",
            "[Status dos pipelines, testes, deploys. Omita se não houver dados.]",
            "",
            "### Débito Técnico / Riscos *(opcional)*",
            "",
            "[Apenas se claramente visível nos dados. Omita se não houver evidência.]",
            "```",
            "",
            "**Regras:** máximo 200 palavras. Linguagem precisa para desenvolvedores. "
            "Retorne APENAS o relatório formatado.",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Section formatters
    # ------------------------------------------------------------------

    def _section_commits_summary(self, commits: list[dict]) -> str:
        if not commits:
            return "## Commits\nNenhum commit no período."
        lines = [f"## Commits ({len(commits)})"]
        for c in commits:
            lines.append(
                f"- `{c.get('short_sha', '')}` {c.get('subject', '')} *(by {c.get('author', '')})*"
            )
        return "\n".join(lines)

    def _section_commits_detail(self, commits: list[dict]) -> str:
        if not commits:
            return "## Commits\nNenhum commit no período."
        lines = [f"## Commits ({len(commits)})"]
        for c in commits:
            entry = f"- `{c.get('short_sha', '')}` **{c.get('subject', '')}** — by {c.get('author', '')}"
            body = c.get("body", "").strip()
            if body:
                entry += f"\n  > {body[:150]}"
            lines.append(entry)
        return "\n".join(lines)

    def _section_prs(self, prs: list[dict]) -> str:
        if not prs:
            return ""
        lines = [f"## Pull Requests ({len(prs)})"]
        for pr in prs:
            state = pr.get("state", "open").upper()
            labels = f" [{', '.join(pr['labels'])}]" if pr.get("labels") else ""
            lines.append(
                f"- **#{pr['number']}** {pr.get('title', '')} — {state}{labels} *(by {pr.get('author', '')})*"
            )
            body = pr.get("body", "").strip()
            if body:
                lines.append(f"  > {body[:150]}")
        return "\n".join(lines)

    def _section_issues(self, issues: list[dict]) -> str:
        if not issues:
            return ""
        lines = [f"## Issues ({len(issues)})"]
        for issue in issues:
            state = issue.get("state", "open").upper()
            labels = f" [{', '.join(issue['labels'])}]" if issue.get("labels") else ""
            lines.append(
                f"- **#{issue['number']}** {issue.get('title', '')} — {state}{labels} *(by {issue.get('author', '')})*"
            )
        return "\n".join(lines)

    def _section_workflows(self, runs: list[dict]) -> str:
        if not runs:
            return ""
        lines = [f"## CI/CD — Workflow Runs ({len(runs)})"]
        for run in runs:
            conclusion = run.get("conclusion", "in_progress").upper()
            branch = run.get("branch", "")
            subject = run.get("commit_subject", "")
            lines.append(
                f"- **{run.get('name', '')}** [{branch}] → {conclusion}"
                + (f" | commit: {subject}" if subject else "")
            )
        return "\n".join(lines)

    def _section_releases(self, releases: list[dict]) -> str:
        if not releases:
            return ""
        lines = [f"## Releases ({len(releases)})"]
        for rel in releases:
            pre = " *(pre-release)*" if rel.get("prerelease") else ""
            lines.append(f"- **{rel.get('tag', '')}** — {rel.get('name', '')}{pre} by {rel.get('author', '')}")
            body = rel.get("body", "").strip()
            if body:
                lines.append(f"  > {body[:200]}")
        return "\n".join(lines)
