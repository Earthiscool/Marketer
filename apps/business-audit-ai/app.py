"""
Flask Web UI — paste a URL in your browser, get a full audit + cold email.
Run: python app.py
Visit: http://localhost:5000
"""
import os
import json
import tempfile
import csv
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template_string, request, jsonify, send_file
from dotenv import load_dotenv
from engine.sales_pack import heuristic_email, heuristic_email_sequence, heuristic_insights, sales_pack

load_dotenv()
app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Business Audit AI</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1115; color: #e7e9ee; min-height: 100vh; }
  .container { max-width: 1120px; margin: 0 auto; padding: 36px 20px; }
  .hero { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.65fr); gap: 28px; align-items: start; margin-bottom: 28px; }
  h1 { font-size: clamp(2rem, 5vw, 4.4rem); line-height: 0.95; font-weight: 800; color: #fff; margin-bottom: 14px; letter-spacing: 0; max-width: 760px; }
  .subtitle { color: #a8afbd; margin-bottom: 18px; font-size: 1rem; line-height: 1.55; max-width: 680px; }
  .hero-proof { display:flex; gap:10px; flex-wrap:wrap; margin-top: 16px; }
  .proof-chip { background:#161c26; border:1px solid #283142; color:#c8d0df; padding:8px 10px; border-radius:8px; font-size:0.82rem; }
  .side-panel { background: #151922; border: 1px solid #273043; border-radius: 8px; padding: 18px; }
  .side-panel h2 { font-size: .86rem; text-transform: uppercase; letter-spacing: .05em; color: #7fb3ff; margin-bottom: 12px; }
  .side-panel ol { margin-left: 18px; color:#c8d0df; font-size:.9rem; line-height:1.65; }
  .form-card { background: #151922; border: 1px solid #273043; border-radius: 8px; padding: 24px; margin-bottom: 28px; }
  .form-grid { display:grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .form-grid .wide { grid-column: 1 / -1; }
  label { display: block; font-size: 0.85rem; color: #aaa; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em; }
  input { width: 100%; padding: 12px 16px; background: #0d1016; border: 1px solid #30394a; border-radius: 8px; color: #fff; font-size: 1rem; margin-bottom: 0; outline: none; transition: border-color 0.2s; }
  textarea, select { width: 100%; padding: 12px 16px; background: #0d1016; border: 1px solid #30394a; border-radius: 8px; color: #fff; font-size: 0.95rem; outline: none; font-family: inherit; }
  textarea { min-height: 120px; resize: vertical; line-height: 1.45; }
  input:focus { border-color: #4f8ef7; }
  button { width: 100%; padding: 14px; background: #2f80ed; color: #fff; border: none; border-radius: 8px; font-size: 1rem; font-weight: 700; cursor: pointer; transition: background 0.2s; }
  button:hover { background: #3a7de0; }
  button:disabled { background: #333; color: #666; cursor: not-allowed; }
  .spinner { display: none; text-align: center; padding: 40px; }
  .spinner.active { display: block; }
  .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #4f8ef7; animation: bounce 1.2s infinite ease-in-out; margin: 0 4px; }
  .dot:nth-child(2) { animation-delay: 0.2s; }
  .dot:nth-child(3) { animation-delay: 0.4s; }
  @keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }
  .status-text { color: #888; margin-top: 12px; font-size: 0.9rem; }
  .results { display: none; }
  .results.active { display: block; }
  .score-bar { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
  .score-circle { width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; font-weight: 700; flex-shrink: 0; }
  .score-good { background: #1a3a1a; border: 3px solid #4caf50; color: #4caf50; }
  .score-mid { background: #3a2a1a; border: 3px solid #ff9800; color: #ff9800; }
  .score-bad { background: #3a1a1a; border: 3px solid #f44336; color: #f44336; }
  .biz-summary { color: #ccc; font-size: 0.95rem; line-height: 1.6; }
  .section { background: #151922; border: 1px solid #273043; border-radius: 8px; padding: 24px; margin-bottom: 20px; }
  .section h2 { font-size: 1rem; font-weight: 600; color: #fff; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.05em; }
  .insight { border-left: 3px solid #4f8ef7; padding: 16px; margin-bottom: 12px; background: #111; border-radius: 0 8px 8px 0; }
  .insight.critical { border-left-color: #f44336; }
  .insight.high { border-left-color: #ff9800; }
  .insight.medium { border-left-color: #4f8ef7; }
  .insight-title { font-weight: 600; color: #fff; margin-bottom: 6px; font-size: 0.95rem; }
  .insight-finding { color: #ccc; font-size: 0.88rem; margin-bottom: 4px; }
  .insight-impact { color: #f44336; font-size: 0.85rem; font-weight: 500; }
  .insight-benchmark { color: #888; font-size: 0.82rem; margin-top: 4px; font-style: italic; }
  .email-box { background: #111; border: 1px solid #2a2a2a; border-radius: 8px; padding: 20px; font-family: monospace; font-size: 0.88rem; line-height: 1.7; color: #ccc; white-space: pre-wrap; }
  .subject { background: #1a2a3a; border: 1px solid #2a4a6a; border-radius: 6px; padding: 10px 16px; margin-bottom: 16px; color: #4f8ef7; font-size: 0.9rem; font-weight: 500; }
  .quick-wins li { color: #ccc; font-size: 0.9rem; padding: 8px 0; border-bottom: 1px solid #2a2a2a; line-height: 1.5; }
  .quick-wins li:last-child { border-bottom: none; }
  .quick-wins li::before { content: "→ "; color: #4caf50; font-weight: 700; }
  .opportunity { background: #1a2a1a; border: 1px solid #2a4a2a; border-radius: 8px; padding: 16px; color: #4caf50; font-size: 0.95rem; line-height: 1.6; }
  .copy-btn { margin-top: 12px; padding: 8px 16px; background: #2a2a2a; color: #aaa; border: 1px solid #333; border-radius: 6px; font-size: 0.8rem; cursor: pointer; float: right; }
  .copy-btn:hover { background: #333; }
  .error-box { background: #2a1a1a; border: 1px solid #5a2a2a; border-radius: 8px; padding: 20px; color: #f44336; }
  .funnel-row { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid #2a2a2a; }
  .funnel-row:last-child { border-bottom: none; }
  .funnel-label { flex: 1; font-size: 0.88rem; color: #ccc; }
  .funnel-bar-bg { flex: 2; height: 8px; background: #2a2a2a; border-radius: 4px; overflow: hidden; }
  .funnel-bar { height: 100%; border-radius: 4px; transition: width 0.8s ease; }
  .funnel-score { width: 40px; text-align: right; font-size: 0.82rem; color: #888; }
  .tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-left: 8px; }
  .tag-critical { background: #3a1a1a; color: #f44336; }
  .tag-high { background: #3a2a1a; color: #ff9800; }
  .tag-medium { background: #1a2a3a; color: #4f8ef7; }
  .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 16px; }
  .stat-card { background: #111; border: 1px solid #2a2a2a; border-radius: 8px; padding: 14px; text-align: center; }
  .stat-value { font-size: 1.4rem; font-weight: 700; color: #fff; }
  .stat-label { font-size: 0.75rem; color: #888; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.04em; }
  .pill { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.78rem; font-weight: 500; margin: 3px; }
  .pill-red { background: #3a1a1a; color: #f44336; }
  .pill-green { background: #1a3a1a; color: #4caf50; }
  .pill-blue { background: #1a2a3a; color: #4f8ef7; }
  .pill-gray { background: #2a2a2a; color: #888; }
  .email-seq-item { border: 1px solid #2a2a2a; border-radius: 8px; margin-bottom: 10px; overflow: hidden; }
  .email-seq-header { padding: 12px 16px; background: #111; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
  .email-seq-header:hover { background: #1a1a1a; }
  .email-seq-body { display: none; padding: 16px; border-top: 1px solid #2a2a2a; }
  .email-seq-body.open { display: block; }
  .traffic-bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
  .traffic-bar-label { width: 90px; font-size: 0.82rem; color: #aaa; }
  .traffic-bar-bg { flex: 1; height: 6px; background: #2a2a2a; border-radius: 3px; overflow: hidden; }
  .traffic-bar-fill { height: 100%; border-radius: 3px; background: #4f8ef7; }
  .traffic-bar-pct { width: 36px; text-align: right; font-size: 0.8rem; color: #888; }
  .tabs { display: flex; gap: 2px; margin-bottom: 20px; border-bottom: 1px solid #2a2a2a; }
  .tab-btn { padding: 10px 20px; background: none; border: none; color: #888; font-size: 0.9rem; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; width: auto; }
  .tab-btn.active { color: #4f8ef7; border-bottom-color: #4f8ef7; }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }
  .sales-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
  .sales-card { background:#0d1016; border:1px solid #273043; border-radius:8px; padding:16px; }
  .sales-card h3 { color:#fff; font-size:.9rem; margin-bottom:8px; }
  .sales-card p, .sales-card li { color:#c8d0df; font-size:.88rem; line-height:1.55; }
  .script-box { background:#0d1016; border:1px solid #273043; border-radius:8px; padding:14px; color:#c8d0df; white-space:pre-wrap; font-size:.88rem; line-height:1.55; margin-bottom:10px; }
  .action-link { display:inline-block; padding:9px 12px; background:#20324a; color:#9dccff; border:1px solid #31547c; border-radius:7px; text-decoration:none; font-size:.84rem; font-weight:700; margin:4px 8px 4px 0; }
  .mode-note { background:#2b2512; border:1px solid #665318; color:#ffd36a; padding:12px 14px; border-radius:8px; font-size:.86rem; line-height:1.45; margin-bottom:16px; }
  .workspace { display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:16px; margin-bottom:28px; }
  .tool-panel { background:#151922; border:1px solid #273043; border-radius:8px; padding:18px; min-width:0; }
  .tool-panel h2 { font-size:.9rem; color:#fff; margin-bottom:12px; text-transform:uppercase; letter-spacing:.05em; }
  .tool-panel p { color:#a8afbd; font-size:.86rem; line-height:1.5; margin-bottom:12px; }
  .mini-btn { padding:10px 12px; font-size:.88rem; margin-top:10px; }
  .lead-table { width:100%; border-collapse:collapse; font-size:.84rem; }
  .lead-table th, .lead-table td { border-bottom:1px solid #273043; padding:9px 8px; text-align:left; vertical-align:top; }
  .lead-table th { color:#7fb3ff; font-size:.75rem; text-transform:uppercase; letter-spacing:.05em; }
  .lead-table td { color:#c8d0df; }
  .small-muted { color:#7f8796; font-size:.8rem; line-height:1.4; }
  .queue-item { border:1px solid #273043; border-radius:8px; padding:12px; margin-bottom:10px; background:#0d1016; }
  .queue-item strong { color:#fff; }
  .inline-actions { display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }
  .inline-actions button, .inline-actions a { width:auto; padding:7px 10px; font-size:.78rem; border-radius:6px; }
  @media (max-width: 820px) {
    .hero { grid-template-columns: 1fr; }
    .form-grid { grid-template-columns: 1fr; }
    .workspace { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<div class="container">
  <div class="hero">
    <div>
      <h1>Find clients with free AI audits.</h1>
      <p class="subtitle">Paste a prospect's website. Get a business audit, outreach scripts, a 7-day pilot offer, follow-up plan, CRM row, and report assets you can use to win customers without paid ads or paid data tools.</p>
      <div class="hero-proof">
        <span class="proof-chip">No paid ad spend</span>
        <span class="proof-chip">Free/public audit signals</span>
        <span class="proof-chip">Built for cold outreach</span>
        <span class="proof-chip">Works with Groq free tier</span>
      </div>
    </div>
    <div class="side-panel">
      <h2>Daily Free Workflow</h2>
      <ol>
        <li>Find 20 local businesses from Google Maps or directories.</li>
        <li>Run audits for the 5 weakest websites.</li>
        <li>Send the permission email, not a huge pitch.</li>
        <li>Record a 2-minute walkthrough for replies.</li>
        <li>Sell a small pilot before any retainer.</li>
      </ol>
    </div>
  </div>

  <div class="form-card">
    <div class="form-grid">
      <div>
        <label for="url">Prospect Website URL</label>
        <input type="text" id="url" placeholder="https://somebusiness.com" />
      </div>
      <div>
        <label for="name">Business Name</label>
        <input type="text" id="name" placeholder="Joe's Plumbing" />
      </div>
      <div class="wide">
        <button id="submit-btn" onclick="runAudit()">Create Audit + Sales Pack</button>
      </div>
    </div>
  </div>

  <div class="workspace">
    <div class="tool-panel">
      <h2>Find Free Leads</h2>
      <p>Search public results, save prospects, then audit the best ones.</p>
      <label for="find-industry">Industry</label>
      <input id="find-industry" placeholder="dentist, roofer, med spa" />
      <label for="find-location" style="margin-top:10px">Location</label>
      <input id="find-location" placeholder="Austin TX" />
      <button class="mini-btn" onclick="findLeads()">Find Leads</button>
    </div>
    <div class="tool-panel">
      <h2>Batch Audit</h2>
      <p>Paste one prospect per line. Format: URL, Business Name.</p>
      <textarea id="batch-input" placeholder="https://example.com, Example Business&#10;acmeplumbing.com, Acme Plumbing"></textarea>
      <button class="mini-btn" onclick="runBatchAudit()">Audit Batch</button>
    </div>
    <div class="tool-panel">
      <h2>Today Queue</h2>
      <p>Work leads due for action. This keeps follow-up from slipping.</p>
      <button class="mini-btn" onclick="loadQueue()">Load Follow-Ups</button>
      <button class="mini-btn" onclick="loadCRM()" style="background:#26364d">View CRM</button>
      <a class="action-link" href="/leads.csv" target="_blank">Export CRM</a>
    </div>
  </div>

  <div class="section" id="ops-panel" style="display:none"></div>

  <div class="spinner" id="spinner">
    <div><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>
    <p class="status-text" id="status-text">Scraping website...</p>
  </div>

  <div class="results" id="results"></div>
</div>

<script>
function showOps(html) {
  const panel = document.getElementById('ops-panel');
  panel.innerHTML = html;
  panel.style.display = 'block';
  panel.scrollIntoView({behavior:'smooth', block:'start'});
}

async function findLeads() {
  const industry = document.getElementById('find-industry').value.trim();
  const location = document.getElementById('find-location').value.trim();
  if (!industry || !location) { alert('Enter an industry and location'); return; }
  showOps('<h2>Finding leads...</h2><p class="small-muted">Searching public results and filtering directories.</p>');
  const res = await fetch('/find_leads', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({industry, location, limit: 25})
  });
  const data = await res.json();
  if (data.error) { showOps(`<div class="error-box">${data.error}</div>`); return; }
  let html = `<h2>Found ${data.leads.length} Leads</h2>`;
  html += `<table class="lead-table"><thead><tr><th>Business</th><th>Website</th><th>Score</th><th>Next</th></tr></thead><tbody>`;
  data.leads.forEach((lead, idx) => {
    html += `<tr>
      <td><strong>${lead.business_name || ''}</strong><div class="small-muted">${lead.snippet || ''}</div></td>
      <td><a href="${lead.url}" target="_blank" style="color:#9dccff">${lead.url}</a></td>
      <td>${lead.lead_score || 0}</td>
      <td><button class="mini-btn" onclick="prefillAudit('${lead.url.replace(/'/g, "\\'")}', '${(lead.business_name || '').replace(/'/g, "\\'")}')">Audit</button></td>
    </tr>`;
  });
  html += `</tbody></table>`;
  showOps(html);
}

function prefillAudit(url, name) {
  document.getElementById('url').value = url;
  document.getElementById('name').value = name;
  window.scrollTo({top: 0, behavior: 'smooth'});
}

async function runBatchAudit() {
  const raw = document.getElementById('batch-input').value.trim();
  if (!raw) { alert('Paste at least one URL'); return; }
  const rows = raw.split('\\n').map(line => {
    const [url, ...nameParts] = line.split(',');
    return {url: (url || '').trim(), name: nameParts.join(',').trim()};
  }).filter(row => row.url);
  showOps(`<h2>Batch running...</h2><p class="small-muted">Auditing ${rows.length} prospects. Keep this tab open.</p>`);
  const res = await fetch('/batch_audit', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({rows})
  });
  const data = await res.json();
  if (data.error) { showOps(`<div class="error-box">${data.error}</div>`); return; }
  let html = `<h2>Batch Results</h2><table class="lead-table"><thead><tr><th>Business</th><th>Score</th><th>Lead Score</th><th>Hook</th></tr></thead><tbody>`;
  data.results.forEach(item => {
    const pack = item.sales_pack || {};
    const crm = pack.crm_row || {};
    html += `<tr><td><strong>${crm.business_name || item.name || item.url}</strong><div class="small-muted">${item.url}</div></td><td>${(item.insights || {}).overall_health_score || '?'}</td><td>${pack.lead_score || '?'}</td><td>${pack.audit_hook || item.error || ''}</td></tr>`;
  });
  html += `</tbody></table>`;
  showOps(html);
}

async function loadQueue() {
  const res = await fetch('/queue.json');
  const data = await res.json();
  let html = `<h2>Today Follow-Up Queue</h2>`;
  if (!data.leads.length) {
    html += `<p class="small-muted">No due leads. Find or audit more prospects.</p>`;
    showOps(html);
    return;
  }
  data.leads.forEach(lead => {
    const mailto = `mailto:${encodeURIComponent(lead.email || '')}?subject=${encodeURIComponent(lead.email_subject || 'Quick idea')}&body=${encodeURIComponent(lead.email_body || lead.hook || '')}`;
    html += `<div class="queue-item">
      <strong>${lead.business_name || lead.url}</strong>
      <div class="small-muted">${lead.status || 'new'} · score ${lead.lead_score || lead.health_score || '?'} · next: ${lead.next_step || 'Follow up'}</div>
      <p style="color:#c8d0df;margin-top:8px">${lead.hook || lead.top_finding || ''}</p>
      <div class="inline-actions">
        <a class="action-link" href="${mailto}">Email</a>
        <button onclick="updateLead('${lead.url.replace(/'/g, "\\'")}', 'contacted')">Mark Contacted</button>
        <button onclick="updateLead('${lead.url.replace(/'/g, "\\'")}', 'replied')">Replied</button>
        <button onclick="updateLead('${lead.url.replace(/'/g, "\\'")}', 'call_booked')">Call Booked</button>
      </div>
    </div>`;
  });
  showOps(html);
}

async function loadCRM() {
  const res = await fetch('/crm.json');
  const data = await res.json();
  let html = `<h2>CRM Pipeline</h2>`;
  const statuses = {};
  data.leads.forEach(lead => {
    const key = lead.status || 'new';
    statuses[key] = (statuses[key] || 0) + 1;
  });
  html += `<div class="stat-grid">`;
  Object.entries(statuses).forEach(([status, count]) => {
    html += `<div class="stat-card"><div class="stat-value">${count}</div><div class="stat-label">${status}</div></div>`;
  });
  html += `</div><table class="lead-table"><thead><tr><th>Lead</th><th>Status</th><th>Score</th><th>Next</th><th>Contact</th></tr></thead><tbody>`;
  data.leads.forEach(lead => {
    html += `<tr>
      <td><strong>${lead.business_name || lead.url}</strong><div class="small-muted">${lead.hook || lead.top_finding || ''}</div></td>
      <td>${lead.status || 'new'}</td>
      <td>${lead.lead_score || lead.health_score || '?'}</td>
      <td>${lead.next_follow_up || ''}<div class="small-muted">${lead.next_step || ''}</div></td>
      <td>${lead.email || ''}<div class="small-muted">${lead.phone || ''}</div></td>
    </tr>`;
  });
  html += `</tbody></table>`;
  showOps(html);
}

async function updateLead(url, status) {
  await fetch('/lead_update', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({url, status})
  });
  loadQueue();
}

async function runAudit() {
  const url = document.getElementById('url').value.trim();
  const name = document.getElementById('name').value.trim();
  if (!url) { alert('Please enter a URL'); return; }

  document.getElementById('submit-btn').disabled = true;
  document.getElementById('results').classList.remove('active');
  document.getElementById('results').innerHTML = '';
  document.getElementById('spinner').classList.add('active');

  const statuses = [
    'Scraping website & all pages...',
    'Running performance analysis...',
    'Analyzing SEO signals...',
    'Checking social media...',
    'Scraping Google reviews & sentiment...',
    'Finding competitors...',
    'Checking ad intelligence...',
    'Estimating traffic...',
    'Scoring by industry...',
    'Checking site history...',
    'Running AI deep analysis...',
    'Writing cold email sequence...',
  ];
  let si = 0;
  const statusEl = document.getElementById('status-text');
  const statusTimer = setInterval(() => {
    statusEl.textContent = statuses[si % statuses.length];
    si++;
  }, 5000);

  try {
    const res = await fetch('/audit', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url, name})
    });
    const data = await res.json();
    clearInterval(statusTimer);
    document.getElementById('spinner').classList.remove('active');
    document.getElementById('submit-btn').disabled = false;

    if (data.error) {
      document.getElementById('results').innerHTML = `<div class="error-box"><strong>Error:</strong> ${data.error}</div>`;
    } else {
      renderResults(data);
    }
    document.getElementById('results').classList.add('active');
  } catch(e) {
    clearInterval(statusTimer);
    document.getElementById('spinner').classList.remove('active');
    document.getElementById('submit-btn').disabled = false;
    document.getElementById('results').innerHTML = `<div class="error-box">Request failed: ${e.message}</div>`;
    document.getElementById('results').classList.add('active');
  }
}

function renderResults(data) {
  const insights = data.insights || {};
  const email = data.email || {};
  const auditData = data.audit_data || {};
  const emailSeq = data.email_sequence || {};
  const score = insights.overall_health_score || 0;
  const scoreClass = score >= 70 ? 'score-good' : score >= 50 ? 'score-mid' : 'score-bad';

  let html = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <div class="tabs" style="margin-bottom:0">
        <button class="tab-btn active" onclick="switchTab('overview', this)">Overview</button>
        <button class="tab-btn" onclick="switchTab('sales', this)">Sales Pack</button>
        <button class="tab-btn" onclick="switchTab('emails', this)">Email Sequence</button>
        <button class="tab-btn" onclick="switchTab('details', this)">Full Details</button>
      </div>
      ${data.pdf_url ? `<a href="${data.pdf_url}" target="_blank" style="padding:9px 18px;background:#4caf50;color:#fff;border-radius:8px;font-size:0.85rem;font-weight:600;text-decoration:none;white-space:nowrap">⬇ Download PDF Report</a>` : ''}
    </div>

    <div id="tab-overview" class="tab-panel active">`;

  if (data.free_mode) {
    html += `<div class="mode-note">Free mode active: no Groq key was found, so the app used rule-based analysis and public website signals. Add a free GROQ_API_KEY when you want richer AI-written reports.</div>`;
  }

  // Score + summary
  html += `
    <div class="section">
      <div class="score-bar">
        <div class="score-circle ${scoreClass}">${score}</div>
        <p class="biz-summary">${insights.business_summary || ''}</p>
      </div>
    </div>`;

  // Total AI Opportunity banner
  if (insights.total_ai_opportunity) {
    html += `<div class="section" style="border-color:#4caf50;background:#0d1f0d">
      <h2 style="color:#4caf50">Total AI Opportunity</h2>
      <p style="color:#ccc;font-size:0.95rem;line-height:1.6">${insights.total_ai_opportunity}</p>
    </div>`;
  }

  // Traffic + Industry stats row
  const traffic = auditData.traffic || {};
  const industry = auditData.industry || {};
  const industryScore = industry.industry_score || {};
  const revModel = industry.revenue_model || {};
  if (traffic.estimated_monthly_visitors || industryScore.score) {
    html += `<div class="section"><h2>Traffic & Industry Overview</h2><div class="stat-grid">`;
    if (traffic.estimated_monthly_visitors) {
      html += `<div class="stat-card"><div class="stat-value">~${traffic.estimated_monthly_visitors.toLocaleString()}</div><div class="stat-label">Monthly Visitors</div></div>`;
    }
    if (traffic.revenue_context && traffic.revenue_context.estimated_monthly_leads) {
      html += `<div class="stat-card"><div class="stat-value">${traffic.revenue_context.estimated_monthly_leads}</div><div class="stat-label">Est. Monthly Leads</div></div>`;
    }
    if (industryScore.score !== undefined) {
      const ig = industryScore.grade || '';
      const igColor = ig === 'Strong' ? '#4caf50' : ig === 'Moderate' ? '#ff9800' : '#f44336';
      html += `<div class="stat-card"><div class="stat-value" style="color:${igColor}">${industryScore.score}</div><div class="stat-label">Industry Score</div></div>`;
    }
    if (revModel.annual_revenue_opportunity) {
      html += `<div class="stat-card"><div class="stat-value" style="color:#4caf50">$${revModel.annual_revenue_opportunity.toLocaleString()}</div><div class="stat-label">Annual Opportunity</div></div>`;
    }
    html += `</div>`;

    // Traffic source bars
    const sources = traffic.traffic_sources || {};
    if (Object.keys(sources).length) {
      html += `<div style="margin-top:8px">`;
      const srcColors = {organic_search:'#4f8ef7',direct:'#4caf50',social:'#ff9800',paid:'#f44336',referral:'#9c27b0'};
      for (const [src, val] of Object.entries(sources)) {
        const pct = val.pct || 0;
        html += `<div class="traffic-bar-row">
          <div class="traffic-bar-label">${src.replace('_',' ')}</div>
          <div class="traffic-bar-bg"><div class="traffic-bar-fill" style="width:${pct}%;background:${srcColors[src]||'#4f8ef7'}"></div></div>
          <div class="traffic-bar-pct">${pct}%</div>
        </div>`;
      }
      html += `</div>`;
    }

    // Industry must-haves missing
    const missing = industry.must_have_missing || [];
    if (missing.length) {
      html += `<div style="margin-top:12px"><span style="color:#f44336;font-size:0.85rem;font-weight:600">Missing must-haves:</span> `;
      missing.forEach(m => { html += `<span class="pill pill-red">${m}</span>`; });
      html += `</div>`;
    }
    html += `</div>`;
  }

  // Top Insights with AI Solutions
  const topInsights = insights.top_insights || [];
  if (topInsights.length) {
    html += '<div class="section"><h2>Top Findings + AI Solutions</h2>';
    topInsights.forEach(ins => {
      const urg = ins.urgency || 'medium';
      const sol = ins.ai_solution || {};
      const conf = ins.confidence || {};
      const sim = ins.fix_simulation || {};
      const confLevel = conf.level || '';
      const confColors = {HIGH:'#4caf50',MEDIUM:'#ff9800',LOW:'#888',ESTIMATED:'#555'};
      const confColor = confColors[confLevel] || '#555';
      html += `
        <div class="insight ${urg}">
          <div class="insight-title" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
            <span>${ins.rank}. ${ins.title}</span>
            <span class="tag tag-${urg}">${urg.toUpperCase()}</span>
            ${confLevel ? `<span style="font-size:0.72rem;padding:2px 7px;border-radius:4px;background:#1a1a1a;border:1px solid ${confColor};color:${confColor};font-weight:600">${confLevel} CONFIDENCE</span>` : ''}
          </div>
          <div class="insight-finding">${ins.finding}</div>
          <div class="insight-impact">Cost: ${ins.estimated_impact}</div>
          <div class="insight-benchmark">${ins.benchmark || ''}</div>
          ${ins.citation ? `<div style="color:#555;font-size:0.78rem;margin-top:3px;font-style:italic">Source: ${ins.citation}</div>` : ''}
          ${conf.confidence_note ? `<div style="color:#555;font-size:0.78rem;margin-top:2px">Data: ${conf.confidence_note}</div>` : ''}
          ${sim.conservative_estimate ? `
          <div style="margin-top:8px;background:#111822;border:1px solid #1a2a3a;border-radius:6px;padding:10px;font-size:0.82rem">
            <div style="color:#4f8ef7;font-weight:600;margin-bottom:4px">Fix Simulation ${sim.citation ? `<span style="color:#444;font-weight:400;font-style:italic">— ${sim.citation}</span>` : ''}</div>
            <div style="color:#888">Conservative: <span style="color:#ff9800">${sim.conservative_estimate}</span></div>
            <div style="color:#888">Realistic: <span style="color:#4caf50">${sim.realistic_estimate}</span></div>
          </div>` : ''}
          ${sol.name ? `
          <div style="margin-top:12px;background:#0d1a2a;border:1px solid #1a3a5a;border-radius:6px;padding:12px">
            <div style="color:#4f8ef7;font-weight:600;font-size:0.88rem;margin-bottom:6px">⚡ ${sol.name}</div>
            <div style="color:#ccc;font-size:0.84rem;line-height:1.5;margin-bottom:4px">${sol.what_it_does || ''}</div>
            <div style="color:#888;font-size:0.82rem">${sol.how_it_works || ''}</div>
            <div style="display:flex;gap:16px;margin-top:8px;flex-wrap:wrap">
              ${sol.timeline ? `<span style="color:#4caf50;font-size:0.8rem">⏱ ${sol.timeline}</span>` : ''}
              ${sol.specific_outcome ? `<span style="color:#ff9800;font-size:0.8rem">📈 ${sol.specific_outcome}</span>` : ''}
              ${sol.monthly_roi ? `<span style="color:#4caf50;font-size:0.8rem">💰 ${sol.monthly_roi}</span>` : ''}
            </div>
          </div>` : ''}
        </div>`;
    });
    html += '</div>';
  }

  // AI Growth Plan
  const growthPlan = insights.ai_growth_plan || [];
  if (growthPlan.length) {
    html += '<div class="section"><h2>AI Growth Plan</h2>';
    const phaseColors = ['#4f8ef7','#ff9800','#4caf50'];
    growthPlan.forEach((phase, i) => {
      html += `
        <div style="border-left:3px solid ${phaseColors[i]};padding:16px;margin-bottom:12px;background:#111;border-radius:0 8px 8px 0">
          <div style="color:${phaseColors[i]};font-weight:600;font-size:0.9rem;margin-bottom:6px">${phase.name}</div>
          <div style="color:#ccc;font-size:0.85rem;margin-bottom:6px">${phase.combined_impact || ''}</div>
          <div style="color:#888;font-size:0.82rem">Solutions: ${(phase.solutions || []).join(' · ')}</div>
          ${phase.estimated_monthly_value ? `<div style="color:#4caf50;font-size:0.85rem;margin-top:6px;font-weight:500">${phase.estimated_monthly_value}</div>` : ''}
        </div>`;
    });
    html += '</div>';
  }

  // Funnel
  const funnel = auditData.funnel || {};
  const journey = funnel.journey_map || [];
  if (journey.length) {
    html += '<div class="section"><h2>Customer Journey Funnel</h2>';
    journey.forEach(step => {
      const color = step.score >= 70 ? '#4caf50' : step.score >= 50 ? '#ff9800' : '#f44336';
      html += `
        <div class="funnel-row">
          <div class="funnel-label">${step.step}</div>
          <div class="funnel-bar-bg"><div class="funnel-bar" style="width:${step.visitors_remaining}%;background:${color}"></div></div>
          <div class="funnel-score">${step.visitors_remaining}%</div>
        </div>`;
    });
    const leak = funnel.revenue_leak || {};
    if (leak.estimated_monthly_revenue_leak) {
      html += `<p style="color:#f44336;font-size:0.88rem;margin-top:12px">Estimated revenue leak: <strong>$${leak.estimated_monthly_revenue_leak.toLocaleString()}/month</strong></p>`;
    }
    html += '</div>';
  }

  // Biggest Opportunity
  if (insights.biggest_opportunity) {
    html += `<div class="section"><h2>Biggest Opportunity</h2><div class="opportunity">${insights.biggest_opportunity}</div></div>`;
  }

  // Quick Wins
  const wins = insights.quick_wins || [];
  if (wins.length) {
    html += '<div class="section"><h2>Quick Wins</h2><ul class="quick-wins">';
    wins.forEach(w => { html += `<li>${w}</li>`; });
    html += '</ul></div>';
  }

  // Cold Email (single)
  if (email.email) {
    html += `
      <div class="section">
        <h2>Cold Email #1 <button class="copy-btn" onclick="copyEmail()">Copy</button></h2>
        ${email.subject_line ? `<div class="subject">Subject: ${email.subject_line}</div>` : ''}
        ${email.alternative_subject ? `<div class="subject" style="opacity:0.6">Alt: ${email.alternative_subject}</div>` : ''}
        <div class="email-box" id="email-body">${email.email}</div>
      </div>`;
  }

  html += `</div>`;  // end tab-overview

  // ── SALES PACK TAB ─────────────────────────────────────────────────────────
  const pack = data.sales_pack || {};
  html += `<div id="tab-sales" class="tab-panel">`;
  if (Object.keys(pack).length) {
    const mailto = pack.mailto || {};
    const mailtoHref = `mailto:${encodeURIComponent(mailto.to || '')}?subject=${encodeURIComponent(mailto.subject || '')}&body=${encodeURIComponent(mailto.body || '')}`;
    html += `<div class="section">
      <h2>Prospect Conversion Plan</h2>
      <div class="stat-grid">
        <div class="stat-card"><div class="stat-value" style="color:${pack.lead_score >= 75 ? '#4caf50' : pack.lead_score >= 60 ? '#ff9800' : '#888'}">${pack.lead_score || '?'}</div><div class="stat-label">Lead Score</div></div>
        <div class="stat-card"><div class="stat-value">${(pack.crm_row || {}).offer || 'AI Pilot'}</div><div class="stat-label">Best Offer</div></div>
        <div class="stat-card"><div class="stat-value">${(pack.crm_row || {}).status || 'new'}</div><div class="stat-label">CRM Status</div></div>
      </div>
      <div class="sales-grid">
        <div class="sales-card"><h3>One-Liner</h3><p>${pack.one_liner || ''}</p></div>
        <div class="sales-card"><h3>Audit Hook</h3><p>${pack.audit_hook || ''}</p></div>
        <div class="sales-card"><h3>Pilot Offer</h3><p>${pack.pilot_offer || ''}</p></div>
        <div class="sales-card"><h3>Buyer</h3><p>${pack.best_buyer || ''}</p></div>
      </div>
      <div class="sales-grid" style="margin-top:12px">
        <div class="sales-card"><h3>Conversion Quality</h3><p>${(pack.quality_check || {}).score || '?'} / 100</p><p class="small-muted">${(pack.quality_check || {}).highest_priority_fix || ''}</p></div>
        <div class="sales-card"><h3>Outreach Quality</h3><p>${(pack.outreach_score || {}).score || '?'} / 100</p><p class="small-muted">${((pack.outreach_score || {}).suggestions || []).join(' ') || 'Email passes the main cold outreach checks.'}</p></div>
      </div>
      <div style="margin-top:14px">
        <a class="action-link" href="${mailtoHref}">Open Email Draft</a>
        <a class="action-link" href="/leads.csv" target="_blank">Export CRM CSV</a>
      </div>
    </div>`;

    const scripts = pack.scripts || {};
    html += `<div class="section"><h2>Scripts</h2>`;
    Object.entries(scripts).forEach(([key, value]) => {
      const id = `script-${key}`;
      html += `<div class="script-box" id="${id}">${value || ''}</div><button class="copy-btn" style="float:none;margin:0 0 14px 0" onclick="copyById('${id}', this)">Copy ${key.replace('_', ' ')}</button>`;
    });
    html += `</div>`;

    if ((pack.walkthrough_outline || []).length) {
      html += `<div class="section"><h2>2-Minute Walkthrough Outline</h2><ul class="quick-wins">`;
      pack.walkthrough_outline.forEach(item => { html += `<li>${item}</li>`; });
      html += `</ul></div>`;
    }

    if ((pack.demo_workflow || []).length) {
      html += `<div class="section"><h2>Demo Workflow</h2><ul class="quick-wins">`;
      pack.demo_workflow.forEach(item => { html += `<li>${item}</li>`; });
      html += `</ul></div>`;
    }

    if ((pack.follow_up_plan || []).length) {
      html += `<div class="section"><h2>Follow-Up Plan</h2>`;
      pack.follow_up_plan.forEach(step => {
        html += `<div class="funnel-row"><div class="funnel-label">Day ${step.day} · ${step.date}</div><div style="flex:2;color:#c8d0df;font-size:.88rem">${step.task}</div></div>`;
      });
      html += `</div>`;
    }

    if ((pack.free_stack || []).length) {
      html += `<div class="section"><h2>Free Tool Stack</h2><ul class="quick-wins">`;
      pack.free_stack.forEach(item => { html += `<li>${item}</li>`; });
      html += `</ul></div>`;
    }

    if ((pack.proposal_outline || []).length) {
      html += `<div class="section"><h2>Proposal Outline</h2><ul class="quick-wins">`;
      pack.proposal_outline.forEach(item => { html += `<li>${item}</li>`; });
      html += `</ul></div>`;
    }

    if (pack.proposal) {
      const p = pack.proposal;
      html += `<div class="section"><h2>1-Page Proposal</h2>
        <div class="script-box" id="proposal-text">${p.title || ''}\n\nProblem\n${p.problem || ''}\n\nScope\n- ${(p.scope || []).join('\n- ')}\n\nTimeline\n${p.timeline || ''}\n\nSuccess Metric\n${p.success_metric || ''}\n\nPrice Options\n${(p.price_options || []).map(opt => `${opt.name}: ${opt.price} - ${opt.includes}`).join('\n')}</div>
        <button class="copy-btn" style="float:none" onclick="copyById('proposal-text', this)">Copy Proposal</button>
      </div>`;
    }
  } else {
    html += `<div class="section"><p style="color:#888">Sales pack not available for this audit.</p></div>`;
  }
  html += `</div>`;

  // ── EMAIL SEQUENCE TAB ──────────────────────────────────────────────────────
  html += `<div id="tab-emails" class="tab-panel">`;
  const seq = (emailSeq.sequence) || [];
  if (seq.length) {
    html += `<div class="section"><h2>5-Email Outreach Sequence</h2>`;
    if (emailSeq.sequence_summary) {
      html += `<p style="color:#888;font-size:0.88rem;margin-bottom:16px;font-style:italic">${emailSeq.sequence_summary}</p>`;
    }
    seq.forEach((em, idx) => {
      const dayLabel = em.send_day === 0 ? 'Send Today' : `Send Day ${em.send_day}`;
      html += `
        <div class="email-seq-item">
          <div class="email-seq-header" onclick="toggleSeq(${idx})">
            <div>
              <span style="color:#4f8ef7;font-weight:600;margin-right:10px">Email ${em.email_number}</span>
              <span style="color:#888;font-size:0.82rem">${dayLabel}</span>
              <span style="color:#aaa;font-size:0.85rem;margin-left:10px">· ${em.subject || ''}</span>
            </div>
            <span style="color:#888" id="seq-arrow-${idx}">▼</span>
          </div>
          <div class="email-seq-body" id="seq-body-${idx}">
            <div style="color:#888;font-size:0.8rem;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.04em">Angle: ${em.angle || ''}</div>
            <div class="subject">Subject: ${em.subject || ''}</div>
            <div class="email-box" id="seq-text-${idx}">${em.body || ''}</div>
            <button class="copy-btn" style="float:none;margin-top:8px" onclick="copyById('seq-text-${idx}', this)">Copy</button>
          </div>
        </div>`;
    });
    html += `</div>`;
  } else {
    html += `<div class="section"><p style="color:#888">Email sequence not available for this audit.</p></div>`;
  }
  html += `</div>`;  // end tab-emails

  // ── FULL DETAILS TAB ────────────────────────────────────────────────────────
  html += `<div id="tab-details" class="tab-panel">`;

  // Visual Analysis
  const visual = auditData.visual || {};
  const vAnalysis = visual.analysis || {};
  if (visual.screenshot_taken && !vAnalysis.error) {
    const vScore = visual.overall_score || 0;
    const vColor = vScore >= 70 ? '#4caf50' : vScore >= 50 ? '#ff9800' : '#f44336';
    html += `<div class="section" style="border-color:${vColor}">
      <h2>AI Visual Analysis <span style="color:${vColor};font-size:0.85rem;margin-left:8px">Grade: ${visual.overall_grade || '?'} · ${vScore}/100</span></h2>
      <div class="stat-grid" style="margin-bottom:12px">
        <div class="stat-card"><div class="stat-value" style="color:${vColor}">${visual.overall_grade || '?'}</div><div class="stat-label">Visual Grade</div></div>
        <div class="stat-card"><div class="stat-value">${visual.design_era || '?'}</div><div class="stat-label">Design Era</div></div>
        <div class="stat-card"><div class="stat-value" style="color:${visual.cta_above_fold ? '#4caf50' : '#f44336'}">${visual.cta_above_fold ? 'Yes' : 'No'}</div><div class="stat-label">CTA Above Fold</div></div>
        <div class="stat-card"><div class="stat-value">${vAnalysis.visual_clutter || '?'}</div><div class="stat-label">Clutter</div></div>
      </div>
      ${vAnalysis.headline_text ? `<p style="color:#888;font-size:0.85rem;margin-bottom:8px">Headline seen: <em>"${vAnalysis.headline_text}"</em></p>` : ''}
      ${(visual.top_issues || []).map(i => `<div style="border-left:3px solid #f44336;padding:8px 12px;margin-bottom:6px;background:#1a1010;border-radius:0 6px 6px 0;color:#ccc;font-size:0.87rem">${i}</div>`).join('')}
      ${vAnalysis.most_urgent_fix ? `<div style="background:#1a2a1a;border:1px solid #2a4a2a;border-radius:8px;padding:12px;margin-top:8px;color:#4caf50;font-size:0.88rem"><b>Most urgent fix:</b> ${vAnalysis.most_urgent_fix}</div>` : ''}
      ${visual.cold_email_angle ? `<p style="color:#4f8ef7;font-size:0.85rem;margin-top:10px;font-style:italic">Cold email angle: "${visual.cold_email_angle}"</p>` : ''}
    </div>`;
  }

  // Review Sentiment
  const sentiment = auditData.review_sentiment || {};
  const sentBreak = sentiment.sentiment_breakdown || {};
  if (sentBreak.overall) {
    const sColor = sentBreak.overall === 'Positive' ? '#4caf50' : sentBreak.overall === 'Negative' ? '#f44336' : '#ff9800';
    html += `<div class="section"><h2>Review Sentiment Analysis</h2>
      <div class="stat-grid">
        <div class="stat-card"><div class="stat-value" style="color:${sColor}">${sentBreak.overall}</div><div class="stat-label">Overall</div></div>
        <div class="stat-card"><div class="stat-value">${sentBreak.sentiment_score || '?'}%</div><div class="stat-label">Positive Score</div></div>
        <div class="stat-card"><div class="stat-value">${sentBreak.positive_mentions || 0}</div><div class="stat-label">+ Mentions</div></div>
        <div class="stat-card"><div class="stat-value">${sentBreak.negative_mentions || 0}</div><div class="stat-label">− Mentions</div></div>
      </div>`;
    const themes = (sentiment.top_themes || {}).top_themes || [];
    if (themes.length) {
      html += `<div style="margin-top:12px"><span style="color:#aaa;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.04em">Top Themes:</span> `;
      themes.forEach(t => { html += `<span class="pill pill-blue">${t.theme} (${t.mentions})</span>`; });
      html += `</div>`;
    }
    const negPhrases = sentBreak.top_negative_phrases || [];
    if (negPhrases.length) {
      html += `<div style="margin-top:10px"><span style="color:#f44336;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.04em">Recurring complaints:</span> `;
      negPhrases.forEach(p => { html += `<span class="pill pill-red">"${p}"</span>`; });
      html += `</div>`;
    }
    html += `</div>`;
  }

  // Site History (Wayback)
  const wayback = auditData.wayback || {};
  const changes = wayback.change_analysis || {};
  const traj = wayback.trajectory || {};
  if (changes.data_available) {
    const trendColor = changes.update_frequency_trend === 'increasing' ? '#4caf50' : changes.update_frequency_trend === 'decreasing' ? '#f44336' : '#ff9800';
    html += `<div class="section"><h2>Site History (Wayback Machine)</h2>
      <div class="stat-grid">
        <div class="stat-card"><div class="stat-value">${changes.site_age_years || '?'}</div><div class="stat-label">Years Online</div></div>
        <div class="stat-card"><div class="stat-value">${changes.established_since || '?'}</div><div class="stat-label">Est. Since</div></div>
        <div class="stat-card"><div class="stat-value" style="color:${trendColor}">${(changes.update_frequency_trend||'').charAt(0).toUpperCase()+(changes.update_frequency_trend||'').slice(1)}</div><div class="stat-label">Update Trend</div></div>
        ${changes.estimated_last_redesign ? `<div class="stat-card"><div class="stat-value">${changes.estimated_last_redesign}</div><div class="stat-label">Last Redesign</div></div>` : ''}
      </div>
      ${(traj.signals||[]).map(s => `<p style="color:#888;font-size:0.85rem;margin-top:6px">· ${s}</p>`).join('')}
    </div>`;
  }

  // Industry AI Opportunities
  const aiOpps = industry.top_ai_opportunities || [];
  if (aiOpps.length) {
    html += `<div class="section"><h2>Industry-Specific AI Opportunities</h2>`;
    aiOpps.forEach(opp => {
      html += `<div style="border-left:3px solid #4f8ef7;padding:10px 14px;margin-bottom:8px;background:#111;border-radius:0 6px 6px 0;color:#ccc;font-size:0.88rem">${opp}</div>`;
    });
    html += `</div>`;
  }

  html += `</div>`;  // end tab-details

  document.getElementById('results').innerHTML = html;
}

function switchTab(name, btn) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  btn.classList.add('active');
}

function toggleSeq(idx) {
  const body = document.getElementById('seq-body-' + idx);
  const arrow = document.getElementById('seq-arrow-' + idx);
  body.classList.toggle('open');
  arrow.textContent = body.classList.contains('open') ? '▲' : '▼';
}

function copyEmail() {
  const text = document.getElementById('email-body').innerText;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.querySelector('.copy-btn');
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy', 2000);
  });
}

function copyById(elemId, btn) {
  const text = document.getElementById(elemId).innerText;
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy', 2000);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('url').addEventListener('keypress', e => { if (e.key === 'Enter') runAudit(); });
});
</script>
</body>
</html>
"""


def run_audit_task(url: str, business_name: str, api_key: str) -> dict:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from auditors.website import WebsiteAuditor
    from auditors.performance import PerformanceAuditor
    from auditors.seo import SEOAuditor
    from auditors.social import SocialAuditor
    from auditors.reviews import ReviewAuditor
    from auditors.competitors import CompetitorAuditor
    from auditors.ads import AdsAuditor
    from auditors.trends import TrendsAuditor
    from auditors.content_deep import ContentDeepAuditor
    from auditors.funnel import FunnelAuditor
    from auditors.jobs import JobsAuditor
    from auditors.wayback import WaybackAuditor
    from auditors.review_sentiment import ReviewSentimentAuditor
    from auditors.traffic import TrafficAuditor
    from auditors.industry import IndustryAnalyzer
    from auditors.dns_intel import DNSIntelAuditor
    from auditors.tech_stack import TechStackAuditor
    from auditors.visual import VisualAuditor
    from auditors.email_deliverability import EmailDeliverabilityAuditor
    from auditors.gbp import GBPAuditor
    from auditors.social_frequency import SocialFrequencyAuditor
    from auditors.citations import CitationsAuditor
    from engine.analyzer import InsightAnalyzer
    from engine.email_writer import EmailWriter
    from engine.email_sequence import EmailSequenceWriter

    audit_data = {}

    def safe(fn):
        try:
            return fn()
        except Exception as e:
            return {"error": str(e)}

    # Group 1: fully independent
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(safe, lambda: WebsiteAuditor(url).audit()): "website",
            ex.submit(safe, lambda: PerformanceAuditor(url).audit()): "performance",
            ex.submit(safe, lambda: WaybackAuditor(url).audit()): "wayback",
            ex.submit(safe, lambda: ReviewSentimentAuditor(business_name, url).audit()): "review_sentiment",
            ex.submit(safe, lambda: DNSIntelAuditor(url).audit()): "dns_intel",
            ex.submit(safe, lambda: TechStackAuditor(url).audit()): "tech_stack",
            ex.submit(safe, lambda: VisualAuditor(url, api_key).audit()): "visual",
            ex.submit(safe, lambda: EmailDeliverabilityAuditor(url).audit()): "email_deliverability",
        }
        for future in as_completed(futures):
            audit_data[futures[future]] = future.result()

    # Group 2: needs website
    website_data = audit_data.get("website", {})
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(safe, lambda: SEOAuditor(url, website_data).audit()): "seo",
            ex.submit(safe, lambda: SocialAuditor(url, website_data).audit()): "social",
            ex.submit(safe, lambda: ReviewAuditor(url, business_name, website_data).audit()): "reviews",
            ex.submit(safe, lambda: CompetitorAuditor(url, business_name, website_data).audit()): "competitors",
            ex.submit(safe, lambda: AdsAuditor(url, business_name, website_data).audit()): "ads",
            ex.submit(safe, lambda: ContentDeepAuditor(website_data).audit()): "content_deep",
            ex.submit(safe, lambda: GBPAuditor(business_name, url, website_data).audit()): "gbp",
            ex.submit(safe, lambda: SocialFrequencyAuditor(url, website_data).audit()): "social_frequency",
        }
        for future in as_completed(futures):
            audit_data[futures[future]] = future.result()

    # Group 3: needs competitors
    biz_type = audit_data.get("competitors", {}).get("inferred_business_type", business_name or "business")
    location = audit_data.get("competitors", {}).get("inferred_location")
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {
            ex.submit(safe, lambda: TrendsAuditor(biz_type, location).audit()): "trends",
            ex.submit(safe, lambda: JobsAuditor(business_name, location).audit()): "jobs",
            ex.submit(safe, lambda: CitationsAuditor(business_name, url, location).audit()): "citations",
        }
        for future in as_completed(futures):
            audit_data[futures[future]] = future.result()

    # Group 4: needs multiple
    audit_data["funnel"] = safe(lambda: FunnelAuditor(
        url, audit_data.get("website", {}), audit_data.get("performance", {}), audit_data.get("seo", {})
    ).audit())
    audit_data["traffic"] = safe(lambda: TrafficAuditor(url, business_name, biz_type, audit_data).audit())
    audit_data["industry"] = safe(lambda: IndustryAnalyzer(biz_type, audit_data).analyze())

    # AI, with a useful no-cost fallback if no Groq key is configured.
    free_mode = not bool(api_key)
    if free_mode:
        insights = heuristic_insights(url, business_name, audit_data)
        email = heuristic_email(url, business_name, insights)
        email_sequence = heuristic_email_sequence(url, business_name, insights, audit_data)
    else:
        insights = safe(lambda: InsightAnalyzer(api_key).analyze(url, business_name, audit_data))
        if not isinstance(insights, dict) or insights.get("parse_error") or insights.get("error"):
            insights = heuristic_insights(url, business_name, audit_data)
            free_mode = True
        email = safe(lambda: EmailWriter(api_key).write(url, business_name, insights))
        if not isinstance(email, dict) or email.get("parse_error") or email.get("error"):
            email = heuristic_email(url, business_name, insights)
        email_sequence = safe(lambda: EmailSequenceWriter(api_key).write(url, business_name, insights, audit_data))
        if not isinstance(email_sequence, dict) or email_sequence.get("parse_error") or email_sequence.get("error"):
            email_sequence = heuristic_email_sequence(url, business_name, insights, audit_data)

    pack = sales_pack(url, business_name, audit_data, insights, email, email_sequence)

    try:
        from engine.database import AuditDatabase
        db = AuditDatabase()
        db.save_audit(url, business_name, audit_data, insights, email)
        db.save_sales_pack(pack)
    except Exception:
        pass

    # Generate PDF — use /tmp but fall back to local dir if /tmp is unreliable
    pdf_path = None
    try:
        from engine.pdf_report import generate_pdf
        safe_name = url.replace("https://", "").replace("http://", "").replace("/", "_").replace(".", "_")
        pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"report_{safe_name}.pdf")
        generate_pdf(pdf_path, url, business_name, audit_data, insights, email, email_sequence)
    except Exception:
        pdf_path = None

    return {
        "audit_data": audit_data,
        "insights": insights,
        "email": email,
        "email_sequence": email_sequence,
        "sales_pack": pack,
        "free_mode": free_mode,
        "pdf_available": bool(pdf_path),
        "pdf_url": f"/download_report?url={url}" if pdf_path else None,
    }


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/download_report")
def download_report():
    url = request.args.get("url", "")
    safe_name = url.replace("https://", "").replace("http://", "").replace("/", "_").replace(".", "_")
    pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"report_{safe_name}.pdf")
    if os.path.exists(pdf_path):
        biz_name = safe_name.split("_")[0] if safe_name else "report"
        return send_file(pdf_path, as_attachment=True,
                         download_name=f"audit_report_{biz_name}.pdf",
                         mimetype="application/pdf")
    return "Report not found", 404


@app.route("/leads.csv")
def leads_csv():
    try:
        from engine.database import AuditDatabase
        leads = AuditDatabase().get_all_leads()
    except Exception:
        leads = []

    fields = [
        "business_name", "url", "email", "phone", "industry", "location",
        "status", "lead_score", "health_score",
        "top_finding", "email_subject", "email_body", "last_contact",
        "hook", "offer", "next_step", "next_follow_up", "notes", "created_at",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for lead in leads:
        writer.writerow({field: lead.get(field, "") for field in fields})

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="")
    tmp.write(output.getvalue())
    tmp.close()
    return send_file(
        tmp.name,
        as_attachment=True,
        download_name="business_audit_leads.csv",
        mimetype="text/csv",
    )


@app.route("/find_leads", methods=["POST"])
def find_leads():
    data = request.json or {}
    industry = data.get("industry", "").strip()
    location = data.get("location", "").strip()
    limit = min(int(data.get("limit", 25) or 25), 50)
    if not industry or not location:
        return jsonify({"error": "industry and location are required"})

    from engine.lead_finder import LeadFinder
    from engine.database import AuditDatabase

    leads = LeadFinder().search(industry, location, limit=limit)
    db = AuditDatabase()
    for lead in leads:
        db.add_prospect(lead)
    return jsonify({"leads": leads})


@app.route("/crm.json")
def crm_json():
    from engine.database import AuditDatabase
    return jsonify({"leads": AuditDatabase().get_all_leads()})


@app.route("/queue.json")
def queue_json():
    from engine.database import AuditDatabase
    return jsonify({"leads": AuditDatabase().get_due_leads()[:50]})


@app.route("/lead_update", methods=["POST"])
def lead_update():
    data = request.json or {}
    url = data.get("url", "").strip()
    status = data.get("status", "").strip()
    if not url or not status:
        return jsonify({"error": "url and status are required"}), 400

    follow_up_days = {
        "found": 0,
        "new": 0,
        "contacted": 3,
        "replied": 1,
        "call_booked": 7,
        "proposal_sent": 4,
        "won": 30,
        "lost": 60,
    }
    next_steps = {
        "contacted": "Follow up with speed-to-lead angle",
        "replied": "Send 2-minute walkthrough or book call",
        "call_booked": "Prepare proposal",
        "proposal_sent": "Follow up on proposal",
        "won": "Deliver pilot and ask for testimonial",
        "lost": "Nurture later",
    }
    from datetime import datetime, timedelta
    from engine.database import AuditDatabase

    next_date = (datetime.utcnow() + timedelta(days=follow_up_days.get(status, 3))).date().isoformat()
    AuditDatabase().update_lead_status(
        url,
        status,
        notes=data.get("notes"),
        next_follow_up=next_date,
        next_step=next_steps.get(status, "Follow up"),
    )
    return jsonify({"ok": True, "next_follow_up": next_date})


@app.route("/batch_audit", methods=["POST"])
def batch_audit():
    data = request.json or {}
    rows = data.get("rows", [])
    if not rows:
        return jsonify({"error": "rows are required"}), 400
    rows = rows[:10]
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    results = []
    for row in rows:
        url = (row.get("url") or "").strip()
        name = (row.get("name") or row.get("business_name") or "").strip()
        if not url:
            continue
        if not url.startswith("http"):
            url = "https://" + url
        try:
            result = run_audit_task(url, name, api_key)
            result["url"] = url
            result["name"] = name
            results.append(result)
        except Exception as e:
            results.append({"url": url, "name": name, "error": str(e)})
    return jsonify({"results": results})


@app.route("/audit", methods=["POST"])
def audit():
    try:
        data = request.json
        url = data.get("url", "").strip()
        name = data.get("name", "").strip()

        if not url.startswith("http"):
            url = "https://" + url

        api_key = os.getenv("GROQ_API_KEY", "").strip()

        result = run_audit_task(url, name, api_key)
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({"error": f"Server error: {str(e)}", "traceback": traceback.format_exc()})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\nBusiness Audit AI — Web UI")
    print(f"Open: http://localhost:{port}\n")
    app.run(debug=False, host="0.0.0.0", port=port)
