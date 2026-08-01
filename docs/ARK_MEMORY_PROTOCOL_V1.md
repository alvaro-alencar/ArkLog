# Ark Memory Protocol v1

## Purpose

Ark Memory Protocol (AMP) is the integration contract between ArkLog, ArkOS, ArkClip and, experimentally, ArkCell.

The products remain independent. They exchange explicit, inspectable events instead of sharing hidden state or becoming one monolith.

## Roles

- **ArkClip** captures reusable human material and emits candidate memory events.
- **ArkLog** transforms operational activity into reports and collects human review.
- **ArkOS** stores versioned operational context inside a repository.
- **ArkCell** is an experimental learning runtime. It may consume approved examples, but it is not a production dependency of ArkLog v1.

## Core rule

No machine-generated preference becomes durable memory without human evidence.

A report review can produce one of three signals:

- `approved`: the result is acceptable as-is;
- `edited`: the user supplied a preferred version;
- `rejected`: the result should not be reused without correction.

## Event envelope

```json
{
  "protocol": "ark.memory.v1",
  "event_id": "uuid",
  "event_type": "report.reviewed",
  "occurred_at": "2026-08-01T00:00:00Z",
  "actor": {
    "kind": "user",
    "id": "ark-user-id"
  },
  "scope": {
    "organization_id": "org-id",
    "project_id": 123,
    "flow_id": null
  },
  "payload": {}
}
```

## `report.reviewed`

```json
{
  "report_id": 42,
  "verdict": "edited",
  "original_content": "machine draft",
  "approved_content": "human-approved version",
  "reason": "Use direct executive language and never infer delivery dates.",
  "labels": ["executive", "no-unverified-inference"]
}
```

## Memory scopes

Preferences are resolved from broadest to narrowest:

1. global user preferences;
2. organization preferences;
3. project or flow preferences;
4. destination or audience preferences;
5. current task instructions.

Narrower scopes override broader scopes. Conflicting rules must remain visible and traceable.

## ArkOS projection

Approved memory can be projected into an ArkOS repository under:

```text
.ai/
  PREFERENCES.md
  EXAMPLES.md
  REVIEW_LOG.md
```

The projection is derived state. The original review event remains the source of provenance.

## ArkClip projection

ArkClip may emit `memory.captured` events with content type, source, local timestamp and user-selected labels. Automatic clipboard capture alone is not permission to publish or train.

## ArkCell boundary

ArkCell may receive exported, approved datasets containing pairs such as:

```text
input context -> generated draft -> human-approved result -> explicit reason
```

This export must be opt-in, reproducible and provenance-preserving. ArkCell must not read production secrets or raw clipboard history by default.

## Safety invariants

1. Secrets are excluded from memory events.
2. Every learned rule has provenance.
3. Deleting a review invalidates derived projections.
4. Automatic delivery is a separate permission from report generation.
5. ArkCell is never silently substituted for the configured production model.
