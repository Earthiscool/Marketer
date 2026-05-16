const state = {
  connected: false,
  sync: null,
  strategy: null,
  leads: [],
  selectedLead: null,
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.message || "Request failed.");
  return data;
}

async function loadStatus() {
  const data = await api("/api/status");
  state.connected = data.connected;
  state.sync = data.sync;
  state.strategy = data.strategy;
  state.leads = data.leads || [];
  render();
}

async function connectGmail() {
  const data = await api("/api/auth/url");
  if (!data.configured) {
    $("connectionStatus").textContent = `Missing Google OAuth config. Create .env with GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET. Redirect URI: ${data.redirectUri}`;
    return;
  }
  window.location.href = data.url;
}

async function syncGmail() {
  $("connectionStatus").textContent = "Syncing Gmail. This can take a minute...";
  $("syncBtn").disabled = true;
  try {
    const data = await api("/api/sync", { method: "POST", body: "{}" });
    state.sync = data.sync;
    state.strategy = data.strategy;
    state.leads = data.leads || [];
    render();
  } catch (error) {
    $("connectionStatus").textContent = error.message;
  } finally {
    $("syncBtn").disabled = false;
  }
}

function render() {
  const overall = state.strategy?.overall || {};
  $("connectionStatus").textContent = state.connected
    ? `Connected. Last sync: ${state.sync?.at ? new Date(state.sync.at).toLocaleString() : "not synced yet"}.`
    : "Not connected yet.";
  $("sentCount").textContent = overall.count || 0;
  $("openRate").textContent = `${overall.openRate || 0}%`;
  $("replyRate").textContent = `${overall.replyRate || 0}%`;
  renderRecommendations();
  renderFeatureStats();
  renderLeads();
  renderWordStats();
}

function renderRecommendations() {
  const recs = state.strategy?.recommendations || ["Connect Gmail and sync to generate strategy changes from real replies."];
  $("recommendations").innerHTML = recs.map((rec) => `<li>${escapeHtml(rec)}</li>`).join("");
}

function renderFeatureStats() {
  const stats = state.strategy?.featureStats || [];
  $("featureStats").innerHTML = stats.length ? stats.map((s) => `
    <div class="feature-row">
      <div>
        <strong>${labelFeature(s.name)}</strong>
        <span>${s.count} emails matched</span>
      </div>
      <div>
        <span class="pill ${s.replyRate > s.without.replyRate ? "good" : "warn"}">${s.openRate}% opened</span>
        <span class="pill ${s.replyRate > s.without.replyRate ? "good" : "warn"}">${s.replyRate}% replied</span>
      </div>
    </div>
  `).join("") : `<div class="feature-row"><span>No synced strategy data yet.</span></div>`;
}

function renderLeads() {
  const query = $("searchInput").value.toLowerCase();
  const leads = state.leads.filter((lead) => `${lead.business} ${lead.email} ${lead.website} ${lead.status}`.toLowerCase().includes(query));
  $("leadList").innerHTML = leads.length ? leads.map((lead) => `
    <article class="lead-card">
      <header>
        <div>
          <h4>${escapeHtml(lead.business || lead.email)}</h4>
          <p>${escapeHtml(lead.email)} ${lead.website ? `· <a href="${escapeAttr(lead.website)}" target="_blank" rel="noreferrer">${escapeHtml(lead.website)}</a>` : ""}</p>
        </div>
        <span class="pill ${lead.replied ? "good" : lead.opened ? "warn" : ""}">${escapeHtml(lead.status)}</span>
      </header>
      <p>${lead.sent || 0} sent · ${lead.opened || 0} opened · ${lead.replied || 0} replied</p>
      <p>${escapeHtml((lead.subjects || []).slice(0, 3).join(" | "))}</p>
      <div class="lead-actions">
        <button data-id="${lead.id}" data-action="draft">Generate adaptive draft</button>
        <button data-id="${lead.id}" data-action="opened">Mark opened</button>
        <button data-id="${lead.id}" data-action="replied">Mark replied</button>
        <button data-id="${lead.id}" data-action="hide">Not fit</button>
      </div>
    </article>
  `).join("") : `<article class="lead-card"><p>No leads yet. Connect and sync Gmail.</p></article>`;
}

function renderWordStats() {
  const words = state.strategy?.subjectWords || [];
  $("wordStats").innerHTML = words.length ? words.map((w) => `
    <div class="word-row">
      <strong>${escapeHtml(w.word)}</strong>
      <span>${w.openRate}% opened · ${w.replyRate}% replied</span>
    </div>
  `).join("") : `<div class="word-row"><span>No word stats yet.</span></div>`;
}

async function generateDraft(lead) {
  const data = await api("/api/draft", { method: "POST", body: JSON.stringify({ lead }) });
  $("draftTitle").textContent = `Draft for ${lead.business || lead.email}`;
  $("draftOutput").textContent = `Subject: ${data.subject}\n\n${data.body}\n\nStrategy notes:\n- ${data.strategyNotes.join("\n- ")}`;
}

async function updateLead(id, action) {
  const lead = state.leads.find((item) => item.id === id);
  if (!lead) return;
  if (action === "opened") {
    lead.status = "Opened";
    lead.opened = Math.max(lead.opened || 0, 1);
  }
  if (action === "replied") {
    lead.status = "Replied";
    lead.replied = Math.max(lead.replied || 0, 1);
  }
  if (action === "hide") lead.status = "Not fit";
  await api("/api/leads", { method: "POST", body: JSON.stringify({ leads: state.leads }) });
  renderLeads();
}

function exportLeads() {
  const blob = new Blob([JSON.stringify({ leads: state.leads, strategy: state.strategy }, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "summit-gmail-growth-agent-export.json";
  link.click();
  URL.revokeObjectURL(url);
}

function labelFeature(name) {
  return {
    specificBusiness: "Business-specific subject",
    question: "Question framing",
    followUp: "Follow-up wording",
    shortSubject: "Short subject",
    longSubject: "Long subject",
    quickIdea: "Quick idea",
    free: "Free/no-cost wording",
    studentRadnor: "Student/Radnor wording",
    demoMeeting: "Demo or meeting wording",
  }[name] || name;
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#96;");
}

$("connectBtn").addEventListener("click", connectGmail);
$("syncBtn").addEventListener("click", syncGmail);
$("exportBtn").addEventListener("click", exportLeads);
$("searchInput").addEventListener("input", renderLeads);
$("copyDraftBtn").addEventListener("click", () => navigator.clipboard.writeText($("draftOutput").textContent));
$("leadList").addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  const lead = state.leads.find((item) => item.id === button.dataset.id);
  if (!lead) return;
  if (button.dataset.action === "draft") await generateDraft(lead);
  else await updateLead(button.dataset.id, button.dataset.action);
});

loadStatus().catch((error) => {
  $("connectionStatus").textContent = error.message;
});
