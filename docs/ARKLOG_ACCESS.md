# ArkLog access policy

ArkLog authenticates with the shared Ark account and authorizes access separately.

- New users start as `PENDING`.
- A manually approved trial receives exactly one report.
- Trial usage is reserved atomically before the OpenRouter request.
- The OpenRouter key never leaves the backend.
- Administrative integrations and automated reports remain restricted to administrators.
- Production requires a persistent PostgreSQL database and keeps the scheduler disabled unless explicitly enabled.
