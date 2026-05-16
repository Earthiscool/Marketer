# Summit Marketing Agent

Standalone semi-autonomous marketing agent for Summit Intelligent Systems.

## What it does

- Generates campaign strategy
- Scores pasted prospects
- Reads public website text when a URL is provided
- Writes cold email, DM, and follow-up copy
- Tracks lead status in browser storage
- Exports prospects to CSV

## Setup

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Environment

Set `GROQ_API_KEY` in `.env.local` for model-generated strategy and outreach. Without it, the app uses fallback logic.
