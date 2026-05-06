# ArkLog - Prompt de Relatório Executivo

## Contexto do Projeto
- **Projeto:** {project_name}
- **Descrição:** {project_description}
- **Stack:** {tech_stack}
- **Contexto de negócio:** {business_context}

## Atividade Recente
- **Commits:** {commit_count}
- **Arquivos alterados:** {files_changed}
- **Áreas afetadas:** {directories}

## Dados dos Commits
{commit_summaries}

## Instrução

Gere um **relatório executivo de progresso** em pt-BR com a seguinte estrutura Markdown:

```
## Status

[Uma frase declarativa sobre o estado atual do projeto.]

### O que Evoluiu

[Bullet points curtos descrevendo as mudanças em linguagem de negócio, sem jargão técnico desnecessário.]

### Impacto

[O que essas mudanças significam para o produto ou stakeholders. Só inclua se houver algo relevante.]

### Próximos Passos *(opcional)*

[Apenas se houver continuidade clara e visível nos commits. Omita se não houver dados suficientes.]
```

**Regras:**
- Máximo 150 palavras no total
- Sem frases genéricas ou de preenchimento
- Se não houver commits: infira a fase atual (planejamento, debug, pesquisa) pelo contexto do projeto
- Retorne APENAS o relatório formatado, sem comentários adicionais
