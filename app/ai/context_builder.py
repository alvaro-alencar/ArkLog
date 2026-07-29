"""Build bounded LLM context from normalized source events or legacy GitHub payloads."""

from typing import Any

_PERIOD_LABELS = {
    "backfill": "histórico completo",
    "weekly_scheduled": "semana completa",
    "daily_scheduled": "período desde o último relatório diário",
    "manual_flow": "janela escolhida pelo usuário",
}


def _period_label(trigger: str) -> str:
    return _PERIOD_LABELS.get(trigger, "atividade recente")


class ContextBuilder:
    """Build structured context without coupling the LLM to one provider."""

    def build_context(self, payload: dict[str, Any]) -> str:
        if "normalized_events" in payload:
            return self._build_normalized(payload)
        style = payload.get("report_style", "misto")
        if style == "executivo":
            return self._build_executive(payload)
        if style == "tecnico":
            return self._build_technical(payload)
        return self._build_executive(payload) + "\n\n---\n\n" + self._build_technical(payload)

    def _build_normalized(self, payload: dict[str, Any]) -> str:
        style = str(payload.get("report_style") or "misto")
        events = payload.get("normalized_events") or []
        lines = [
            "## Configuração do fluxo",
            f"- **Fluxo:** {payload.get('project_name', '')}",
            f"- **Fonte:** {payload.get('source_provider', 'desconhecida')}",
            f"- **Origem selecionada:** {payload.get('source_label', '')}",
            f"- **Período:** {_period_label(payload.get('trigger', 'manual_flow'))}",
        ]
        instructions = str(payload.get("business_context") or "").strip()
        if instructions:
            lines.append(f"- **Instruções do usuário:** {instructions}")
        lines.extend(["", f"## Eventos normalizados ({len(events)})"])
        if not events:
            lines.append("Nenhum evento foi coletado na janela selecionada.")
        for event in events:
            reference = str(event.get("reference") or "").strip()
            actor = str(event.get("actor") or "").strip()
            labels = event.get("labels") or []
            metadata = [
                str(event.get("type") or "evento"),
                str(event.get("status") or ""),
                reference,
                f"por {actor}" if actor else "",
                f"labels: {', '.join(labels)}" if labels else "",
            ]
            suffix = " · ".join(item for item in metadata if item)
            lines.append(f"- **{event.get('title', '')}** ({suffix})")
            description = str(event.get("description") or "").strip()
            if description:
                lines.append(f"  > {description[:350]}")

        lines.extend(["", "## Instrução de saída", ""])
        if style == "executivo":
            lines.extend(
                [
                    "Produza um relatório executivo em Markdown com: Status, O que Evoluiu, Impacto e Próximos Passos quando houver evidência.",
                    "Máximo 220 palavras. Não cite quantidade de eventos salvo se as instruções pedirem.",
                ]
            )
        elif style == "tecnico":
            lines.extend(
                [
                    "Produza um relatório técnico em Markdown com: Alterações, Decisões, Qualidade/Automação e Riscos quando houver evidência.",
                    "Máximo 300 palavras. Seja preciso e não invente detalhes ausentes.",
                ]
            )
        else:
            lines.extend(
                [
                    "Produza um relatório misto em Markdown: resumo executivo curto seguido de evolução técnica, impacto, riscos e próximos passos quando sustentados pelos eventos.",
                    "Máximo 400 palavras. Não invente fatos, decisões ou arquivos.",
                ]
            )
        lines.append("Retorne apenas o relatório formatado.")
        return "\n".join(lines)

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
            "Gere um relatório executivo de progresso em pt-BR com Status, O que Evoluiu, Impacto e Próximos Passos quando houver evidência. Máximo 200 palavras. Retorne apenas o relatório.",
        ]
        return "\n".join(lines)

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
            "Gere um relatório técnico em pt-BR com Alterações, Decisões de Arquitetura, CI/CD e Riscos quando sustentados pelos dados. Máximo 250 palavras. Retorne apenas o relatório.",
        ]
        return "\n".join(lines)

    def _section_commits_summary(self, commits: list[dict]) -> str:
        if not commits:
            return "## Commits\nNenhum commit no período."
        lines = [f"## Commits ({len(commits)})"]
        for commit in commits:
            lines.append(
                f"- `{commit.get('short_sha', '')}` {commit.get('subject', '')} *(por {commit.get('author', '')})*"
            )
        return "\n".join(lines)

    def _section_commits_detail(self, commits: list[dict]) -> str:
        if not commits:
            return "## Commits\nNenhum commit no período."
        lines = [f"## Commits ({len(commits)})"]
        for commit in commits:
            entry = f"- `{commit.get('short_sha', '')}` **{commit.get('subject', '')}** — {commit.get('author', '')}"
            body = str(commit.get("body") or "").strip()
            if body:
                entry += f"\n  > {body[:150]}"
            lines.append(entry)
        return "\n".join(lines)

    def _section_prs(self, items: list[dict]) -> str:
        if not items:
            return ""
        lines = [f"## Pull Requests ({len(items)})"]
        for item in items:
            labels = f" [{', '.join(item['labels'])}]" if item.get("labels") else ""
            lines.append(
                f"- **#{item['number']}** {item.get('title', '')} — {item.get('state', '').upper()}{labels} *(por {item.get('author', '')})*"
            )
            body = str(item.get("body") or "").strip()
            if body:
                lines.append(f"  > {body[:150]}")
        return "\n".join(lines)

    def _section_issues(self, items: list[dict]) -> str:
        if not items:
            return ""
        lines = [f"## Issues ({len(items)})"]
        for item in items:
            labels = f" [{', '.join(item['labels'])}]" if item.get("labels") else ""
            lines.append(
                f"- **#{item['number']}** {item.get('title', '')} — {item.get('state', '').upper()}{labels} *(por {item.get('author', '')})*"
            )
        return "\n".join(lines)

    def _section_workflows(self, items: list[dict]) -> str:
        if not items:
            return ""
        lines = [f"## CI/CD ({len(items)})"]
        for item in items:
            subject = item.get("commit_subject", "")
            lines.append(
                f"- **{item.get('name', '')}** [{item.get('branch', '')}] → {item.get('conclusion', 'in_progress').upper()}"
                + (f" | {subject}" if subject else "")
            )
        return "\n".join(lines)

    def _section_releases(self, items: list[dict]) -> str:
        if not items:
            return ""
        lines = [f"## Releases ({len(items)})"]
        for item in items:
            pre = " *(pré-release)*" if item.get("prerelease") else ""
            lines.append(
                f"- **{item.get('tag', '')}** — {item.get('name', '')}{pre} por {item.get('author', '')}"
            )
            body = str(item.get("body") or "").strip()
            if body:
                lines.append(f"  > {body[:200]}")
        return "\n".join(lines)
