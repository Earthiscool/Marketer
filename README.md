# Marketer

Unified growth toolkit for Summit outreach, local-business demos, Gmail-based strategy learning, and website audits.

## Apps

- **Launcher**: team dashboard for the full portfolio.
- **Summit Growth Studio**: CRM, custom demo deck builder, generated outreach copy, and demo video recorder.
- **Summit Gmail Growth Agent**: Gmail OAuth sync, reply/open pattern analysis, adaptive draft generation, and Gmail-informed CRM.
- **Summit Marketing Agent**: Next.js AI marketing planner and prospecting workspace.
- **Business Audit AI**: Python website/business audit engine with SEO, performance, reviews, social, competitors, funnel, and sales-pack modules.

## Run

```bash
npm start
```

Open:

```text
http://localhost:5190
```

## Gmail Setup

Copy:

```text
apps/summit-gmail-growth-agent/.env.example
```

to:

```text
apps/summit-gmail-growth-agent/.env
```

Then fill in your Google OAuth client ID and secret. The redirect URI for local use is:

```text
http://localhost:5180/oauth2callback
```

## Security

Secrets, Gmail tokens, local databases, generated PDFs, build output, and `node_modules` are intentionally ignored.

## Deploy To Vercel

The root project is configured with `vercel.json` for a static team-facing deployment:

- `/` serves the Marketer launcher.
- `/growth-studio` serves the browser-only CRM/demo builder.

The Gmail Growth Agent is included in the repo, but it is not automatically hosted by the static Vercel launcher because Gmail OAuth tokens need durable storage. Use a hosted database before enabling it for a team deployment.
