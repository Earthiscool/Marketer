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

## Shared Supabase Database

The browser marketing engine supports Supabase sync for a shared team workspace.

1. Create a free Supabase project.
2. Open the Supabase SQL Editor.
3. Run the SQL shown inside the app under **Exports -> Team database**.
4. Copy the project URL and anon key from Supabase project settings.
5. In the app, open **Exports -> Team database**, paste the URL/key, choose a workspace ID such as `summit-team`, then save settings.
6. Use **Save shared** to write the current CRM/demo state and **Load shared** on teammate browsers.

The anon key is safe to expose for browser apps, but the permissive demo policies in the app are intended for a private team workspace. Tighten RLS policies before storing sensitive client data.

## Deploy To Vercel

The root project is configured with `vercel.json` for a static team-facing deployment:

- `/` serves the browser marketing engine from `public/index.html`.
- `/growth-studio` serves the browser-only CRM/demo builder from `public/growth-studio`.

The Gmail Growth Agent is included in the repo, but it is not automatically hosted by the static Vercel launcher because Gmail OAuth tokens need durable storage. Use a hosted database before enabling it for a team deployment.
