# prompts/ — AI Prompt Templates

Plain Markdown files used as prompt templates by the AI engine. Edit freely — no Python changes required.

## Files

### `report_executive.md`
Template for `report_style: executivo`. Produces a business-oriented report with sections for Status, What Evolved, Impact, and Next Steps. Maximum 150 words. Audience: non-technical stakeholders and managers.

### `report_technical.md`
Template for `report_style: tecnico`. Produces a precise technical report with sections for Technical Changes, Architecture Decisions (optional), and Technical Debt/Risks (optional). Maximum 150 words. Audience: developers and architects.

For `report_style: misto`, both templates are concatenated and sent to the AI as a single prompt.

## Variables

Templates use Python `.format()` syntax. Available variables:

| Variable | Source |
|---|---|
| `{project_name}` | `projects.yaml` → `name` |
| `{project_description}` | `projects.yaml` → `description` |
| `{tech_stack}` | `projects.yaml` → `tech_stack` (comma-separated) |
| `{business_context}` | `projects.yaml` → `business_context` |
| `{period_start}` | Derived from trigger type |
| `{period_end}` | Always "hoje" |
| `{commit_count}` | Number of commits in this batch |
| `{files_changed}` | Total files changed across all commits |
| `{directories}` | Unique directories affected |
| `{commit_summaries}` | Formatted list: `[sha] subject (author) — areas` |
| `{commit_details}` | Detailed list with file counts and extensions |

## Customizing

Adjust tone, structure, or word limits directly in the Markdown files. The system prompts (which control the AI's overall behavior and language) live in `app/ai/report_generator.py`.
