# ArkLog 0.4.0

Production rollout of the provider-agnostic reporting architecture.

- User-owned GitHub App installations with repository selection.
- Short-lived GitHub installation tokens restricted to the selected repository.
- User-owned Slack OAuth connections.
- Provider-neutral event normalization between source and LLM.
- Manual GitHub to Slack flows with quota, idempotency, and publication history.
- Secure fail-closed cloud startup and readiness diagnostics.

Platform secrets are configured outside the repository. No personal provider token belongs in source control or shared environment variables.
