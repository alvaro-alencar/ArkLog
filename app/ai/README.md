# app/ai — AI Engine

Responsible for transforming raw commit data into structured natural language reports.

## Files

### `context_builder.py`
Assembles the prompt sent to the AI model. Loads the appropriate Markdown template from `prompts/`, fills in observed values (commits, project metadata, tech stack), and returns the final prompt string. **Nothing is inferred here** — only data explicitly present in the payload is injected.

### `report_generator.py`
Calls the configured AI model via the OpenAI-compatible client. Selects the correct system prompt and token budget based on the report trigger:

| Trigger | System prompt | Max tokens |
|---|---|---|
| `webhook` / `daily_scheduled` | Concise (150 words) | `AI_MAX_TOKENS` |
| `weekly_scheduled` | Detailed weekly review (400 words) | `AI_MAX_TOKENS_BACKFILL` |
| `backfill` | Comprehensive historical analysis | `AI_MAX_TOKENS_BACKFILL` |

### `openai_client.py`
Singleton factory for the `AsyncOpenAI` client, pre-configured for OpenRouter with the required `HTTP-Referer` and `X-Title` headers. Drop-in compatible with any OpenAI API-format provider.

## Adding a new AI provider

1. Set `AI_BASE_URL` and `AI_API_KEY` in `.env`
2. Set `AI_MODEL` to any model ID supported by your provider
3. No code changes required — the client is provider-agnostic

## Prompt templates

Templates live in [`prompts/`](../../prompts/README.md). They are plain Markdown files with `{placeholder}` variables — edit them freely without touching Python code.
