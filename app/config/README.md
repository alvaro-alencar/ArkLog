# app/config — Project Configuration Loader

Loads and validates `projects.yaml` into typed domain entities at startup.

## Files

### `projects.py`

Two-layer validation using Pydantic:

**Layer 1 — `ReportDestinationEntry`**: Validates a single report destination from YAML. Checks that `times` use `HH:MM` format, that `day` is a valid weekday, and that `report_style` is one of `misto | executivo | tecnico`. Converts to a `ReportDestination` domain entity via `to_entity()`, applying default `window_days` (0 for daily, 7 for weekly if not explicitly set).

**Layer 2 — `ProjectYamlEntry`**: Validates a full project block. Converts to a `Project` domain entity with all its destinations.

**`ProjectsConfig`**: Singleton loader. Reads `projects.yaml` once on first access and caches the result. Invalid entries are logged and skipped — a malformed project does not crash the application.

## projects.yaml

The YAML file is **gitignored** — it contains task IDs and configuration specific to your environment. Copy `projects.yaml.example` to get started:

```bash
cp projects.yaml.example projects.yaml
```

See the [main README](../../README.md#projectsyaml) for the full format reference.
