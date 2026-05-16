# Summit Gmail Growth Agent

Local CRM + Gmail strategy analyzer for Summit outreach.

## Setup

1. Create a Google Cloud OAuth client for a Desktop/Web app.
2. Add this redirect URI:

   `http://localhost:5180/oauth2callback`

3. Copy `.env.example` to `.env` and fill in:

   `GOOGLE_CLIENT_ID`

   `GOOGLE_CLIENT_SECRET`

4. Run:

   `npm start`

5. Open:

   `http://localhost:5180`

## What It Reads

The app uses Gmail readonly access. It syncs recent sent and inbox messages, then analyzes:

- sent subjects
- recipients
- replies by thread
- `Opened` label if your Gmail account has that label
- timing and follow-up patterns

It does not send emails automatically.
