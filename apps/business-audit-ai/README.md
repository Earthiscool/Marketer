# Business Audit AI

Free client-acquisition tool for an AI consultancy.

Paste a prospect's website and the app creates:

- A digital audit using public/free signals
- Free lead discovery by industry and city
- Batch auditing from pasted CSV-style rows
- A lead score
- The best AI pilot offer for that prospect
- Cold email, LinkedIn, phone, and referral scripts
- A 2-minute walkthrough outline
- A 21-day follow-up plan
- A CRM dashboard and today's follow-up queue
- Outreach quality scoring
- A demo workflow and 1-page proposal draft
- A PDF report when report generation succeeds
- A CRM CSV export from saved audits

## Run Locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000`.

## Free Mode

The app works without paid APIs. If `GROQ_API_KEY` is missing, it uses rule-based audit insights and still generates scripts, a pilot offer, follow-up plan, and CRM row.

For richer AI-written reports, create a free Groq key and add it to `.env`:

```bash
GROQ_API_KEY=your_free_groq_key
```

Optional free-tier screenshot analysis:

```bash
SCREENSHOTONE_API_KEY=your_free_screenshotone_key
```

## Daily Workflow

1. Pick one niche for the week, such as dentists, roofers, law firms, realtors, or med spas.
2. Use **Find Free Leads** to search by industry and city, then save prospects into the CRM.
3. Audit the 5 weakest websites or paste a list into **Batch Audit**.
4. Sort by lead score and work the **Today Queue**.
5. Send the permission email from the Sales Pack tab.
6. Record a 2-minute walkthrough only for people who reply.
7. Offer a 7-day pilot, not a large retainer.
8. Export `/leads.csv` when you want to work the pipeline in a spreadsheet.

## What To Sell First

Start with the smallest measurable pilot:

- AI receptionist for website inquiries
- Missed-call or form follow-up sequence
- Review request automation
- FAQ/intake assistant
- Local SEO service page sprint

The first sale should be easy to say yes to. Use the audit to sell one urgent fix, then expand after results.

## New Web Routes

- `/find_leads` finds prospects from public search results
- `/batch_audit` audits up to 10 pasted prospects at a time
- `/crm.json` returns the pipeline
- `/queue.json` returns leads due for follow-up
- `/lead_update` updates status and next follow-up date
- `/leads.csv` exports the CRM

## Practical Operating Rule

Do not spend money on ads until this free funnel produces replies:

```text
Find 25 leads
Audit 5
Send 5 permission emails
Follow up after 3 days
Record walkthroughs only for replies
Sell one small pilot
```
