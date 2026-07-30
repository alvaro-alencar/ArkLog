# ArkLog production setup

This checklist intentionally contains only platform credentials. No personal GitHub,
Slack, Notion, ClickUp, or other user token belongs in Vercel environment variables.

## 1. Persistent database

The Neon project is `arklog-production` and its default database is `neondb`.
Copy the pooled connection string into `DATABASE_URL`. ArkLog normalizes the standard
Neon URL for the async driver and rejects SQLite in cloud deployments.

## 2. Platform secrets

Configure these for Production and Preview in the ArkLog Vercel project:

```text
APP_ENV=production
DATABASE_URL=<Neon pooled connection string>
AI_API_KEY=<OpenRouter key>
CONNECTIONS_ENCRYPTION_KEY=<independent random value, at least 32 characters>
OAUTH_STATE_SECRET=<another independent random value, at least 32 characters>
PUBLIC_APP_URL=https://www.arksystem.net/arklog
ARK_AUTH_ME_URL=https://www.arksystem.net/api/saas?action=me
ARKLOG_AUTO_TRIAL=false
SCHEDULER_ENABLED=false
CORS_ORIGINS=["https://www.arksystem.net"]
```

Do not configure `GITHUB_TOKEN`, `CLICKUP_API_TOKEN`, or any personal provider token.

## 3. GitHub App

Create a GitHub App named **ArkLog**.

General settings:

- Homepage URL: `https://www.arksystem.net/arklog`
- Callback URL: `https://www.arksystem.net/api/arklog/v1/connections/github/callback`
- Setup URL: `https://www.arksystem.net/arklog/connections`
- Request user authorization during installation: enabled
- Webhooks: disabled for the first release
- Installation scope: any account that is allowed to use ArkLog

Repository permissions, all read-only:

- Actions
- Contents
- Issues
- Pull requests
- Metadata, which GitHub includes automatically

No write permission is required.

Generate one private key and one client secret. Add these Vercel variables:

```text
GITHUB_APP_ID=<numeric App ID>
GITHUB_APP_SLUG=<slug shown in the GitHub App URL>
GITHUB_APP_PRIVATE_KEY=<complete PEM private key>
GITHUB_CLIENT_ID=<GitHub App client ID>
GITHUB_CLIENT_SECRET=<GitHub App client secret>
GITHUB_REDIRECT_URI=https://www.arksystem.net/api/arklog/v1/connections/github/callback
```

During connection, each user chooses **All repositories** or **Only select repositories**.
ArkLog stores only the installation ID. It generates an expiring installation token when
it needs to list selected repositories and narrows the report execution token to the one
repository used by that flow.

## 4. Slack App

Create a Slack App from `docs/slack-app-manifest.yaml`, or configure it manually.

Required bot scopes:

- `channels:read`
- `groups:read`
- `chat:write`

Redirect URL:

`https://www.arksystem.net/api/arklog/v1/connections/slack/callback`

Add these Vercel variables:

```text
SLACK_CLIENT_ID=<Slack App client ID>
SLACK_CLIENT_SECRET=<Slack App client secret>
SLACK_REDIRECT_URI=https://www.arksystem.net/api/arklog/v1/connections/slack/callback
```

Each ArkLog user installs the Slack App in their own workspace. The returned bot token is
encrypted in the database and is never sent back to the browser.

## 5. Release verification

Before exposing the institutional route:

1. Check `/api/arklog/v1/health/detailed`.
2. Sign in with an Ark account.
3. Confirm a new account starts as `PENDING`.
4. Grant `TRIAL` and confirm the limit is one report.
5. Install the GitHub App on one test repository.
6. Connect one Slack workspace and select one test channel.
7. Create and execute a manual flow.
8. Confirm failure returns the reserved quota and success consumes it once.
9. Confirm refreshing or retrying the same request does not duplicate the Slack message.
10. Only then merge the ArkSystem menu and route integration.
