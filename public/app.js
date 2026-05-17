const STORAGE_KEY = "marketer_crm_state_v2";
const DB_CONFIG_KEY = "marketer_supabase_config_v2";
const DEFAULT_DB_CONFIG = {
  url: "https://wfnkfuxyfblocbinsbaj.supabase.co",
  anonKey: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmbmtmdXh5ZmJsb2NiaW5zYmFqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg5ODMxNjcsImV4cCI6MjA5NDU1OTE2N30.56o_zJbkLfTziOgUUSGaL1oqleIC_mHctmn_fuK1DBk",
  workspaceId: "summit-team",
};

const defaultDemo = {
  businessName: "",
  website: "",
  industry: "local business",
  goal: "More booked appointments",
  observation: "The current customer path could be clearer and faster.",
  build: "AI assistant, stronger service pages, cleaner calls to action, and a simple owner dashboard.",
};

const state = { leads: [], selectedId: null, activeSlide: 0, demo: { ...defaultDemo } };
let isHydrating = false;
let autosaveTimer = null;
let lastSavedHash = "";

const $ = (id) => document.getElementById(id);
const statuses = ["New", "Researched", "Contacted", "Opened", "Replied", "Meeting", "Won", "Not fit"];

function uid() { return crypto.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random()); }
function todayIso() { return new Date().toISOString(); }
function normalizeUrl(value) { if (!value) return ""; return /^https?:\/\//i.test(value) ? value : `https://${value}`; }
function esc(value) { return String(value || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

function getDbConfig() {
  try {
    const config = JSON.parse(localStorage.getItem(DB_CONFIG_KEY) || "{}");
    return {
      url: String(config.url || DEFAULT_DB_CONFIG.url).replace(/\/+$/, ""),
      anonKey: String(config.anonKey || DEFAULT_DB_CONFIG.anonKey),
      workspaceId: String(config.workspaceId || DEFAULT_DB_CONFIG.workspaceId).trim() || DEFAULT_DB_CONFIG.workspaceId,
    };
  } catch { return DEFAULT_DB_CONFIG; }
}

function setSync(message, tone = "") {
  const el = $("syncStatus");
  if (!el) return;
  el.textContent = message;
  el.dataset.tone = tone;
}

async function supabaseRequest(path, options = {}) {
  const config = getDbConfig();
  if (!config.url || !config.anonKey) throw new Error("Missing Supabase config.");
  const res = await fetch(`${config.url}/rest/v1/${path}`, {
    ...options,
    headers: { apikey: config.anonKey, authorization: `Bearer ${config.anonKey}`, "content-type": "application/json", ...(options.headers || {}) },
  });
  const text = await res.text();
  if (!res.ok) throw new Error(text || `${res.status} ${res.statusText}`);
  return text ? JSON.parse(text) : null;
}

function persistLocal() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ leads: state.leads, selectedId: state.selectedId, demo: state.demo }));
  scheduleAutosave();
}

function loadLocal() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    state.leads = Array.isArray(saved.leads) ? saved.leads : [];
    state.selectedId = saved.selectedId || state.leads[0]?.id || null;
    state.demo = { ...defaultDemo, ...(saved.demo || {}) };
  } catch { state.leads = []; }
}

function sharedPayload() { return { leads: state.leads, selectedId: state.selectedId, demo: state.demo }; }
function payloadHash() { return JSON.stringify(sharedPayload()); }

function scheduleAutosave() {
  if (isHydrating) return;
  clearTimeout(autosaveTimer);
  autosaveTimer = setTimeout(() => saveShared(true), 800);
}

async function loadShared() {
  const config = getDbConfig();
  setSync(`Loading ${config.workspaceId}...`);
  try {
    const rows = await supabaseRequest(`marketing_engine_states?id=eq.${encodeURIComponent(config.workspaceId)}&select=data,updated_at`);
    if (!rows.length) { await saveShared(true, true); return; }
    isHydrating = true;
    const data = rows[0].data || {};
    state.leads = Array.isArray(data.leads) ? data.leads : [];
    state.selectedId = data.selectedId || state.leads[0]?.id || null;
    state.demo = { ...defaultDemo, ...(data.demo || {}) };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sharedPayload()));
    isHydrating = false;
    lastSavedHash = payloadHash();
    renderAll();
    setSync(`Synced ${config.workspaceId} at ${new Date(rows[0].updated_at).toLocaleTimeString()}`, "ok");
  } catch (error) { isHydrating = false; setSync(`Sync failed: ${error.message}`, "bad"); }
}

async function saveShared(silent = false, force = false) {
  const config = getDbConfig();
  const hash = payloadHash();
  if (!force && hash === lastSavedHash) return;
  if (!silent) setSync("Syncing changes...");
  try {
    await supabaseRequest("marketing_engine_states?on_conflict=id", {
      method: "POST",
      headers: { prefer: "resolution=merge-duplicates,return=minimal" },
      body: JSON.stringify({ id: config.workspaceId, data: sharedPayload(), updated_at: todayIso() }),
    });
    lastSavedHash = hash;
    setSync(`Autosaved ${config.workspaceId} at ${new Date().toLocaleTimeString()}`, "ok");
  } catch (error) { setSync(`Autosave failed: ${error.message}`, "bad"); }
}

function scoreLead(lead) {
  const t = `${lead.name} ${lead.industry} ${lead.opportunity} ${lead.notes}`.toLowerCase();
  let score = 35;
  if (lead.website) score += 8;
  if (/booking|appointment|quote|call|lead|seo|website|slow|outdated|chatbot|ai|customer/.test(t)) score += 25;
  if (["Opened", "Replied", "Meeting", "Won"].includes(lead.status)) score += 20;
  if (lead.followup) score += 5;
  return Math.min(score, 100);
}

function selectedLead() { return state.leads.find((lead) => lead.id === state.selectedId) || null; }

function blankLead() {
  const lead = { id: uid(), name: "Untitled business", website: "", email: "", industry: "", status: "New", followup: "", opportunity: "", notes: "", updatedAt: todayIso() };
  state.leads.unshift(lead); state.selectedId = lead.id; hydrateFromLead(lead); persistLocal(); renderAll();
}

function hydrateFromLead(lead) {
  if (!lead) return;
  state.demo = { ...state.demo, businessName: lead.name, website: lead.website, industry: lead.industry || "local business", observation: lead.opportunity || state.demo.observation, build: lead.notes?.replace(/^Recommended build:\s*/i, "") || state.demo.build };
}

function saveLead(event) {
  event.preventDefault();
  const id = state.selectedId || uid();
  const lead = { id, name: $("leadName").value.trim() || "Untitled business", website: normalizeUrl($("leadWebsite").value.trim()), email: $("leadEmail").value.trim(), industry: $("leadIndustry").value.trim(), status: $("leadStatus").value, followup: $("leadFollowup").value, opportunity: $("leadOpportunity").value.trim(), notes: $("leadNotes").value.trim(), updatedAt: todayIso() };
  const i = state.leads.findIndex((item) => item.id === id);
  if (i >= 0) state.leads[i] = lead; else state.leads.unshift(lead);
  state.selectedId = id; hydrateFromLead(lead); persistLocal(); renderAll();
}

function deleteLead() {
  if (!state.selectedId) return;
  state.leads = state.leads.filter((lead) => lead.id !== state.selectedId);
  state.selectedId = state.leads[0]?.id || null;
  persistLocal(); renderAll();
}

function filteredLeads() {
  const q = $("searchInput")?.value.toLowerCase() || "";
  const status = $("statusFilter")?.value || "All";
  return state.leads.filter((lead) => status === "All" || lead.status === status).filter((lead) => `${lead.name} ${lead.email} ${lead.industry} ${lead.status} ${lead.opportunity}`.toLowerCase().includes(q)).sort((a,b) => scoreLead(b) - scoreLead(a));
}

function renderMetrics() {
  const open = state.leads.filter((l) => !["Won", "Not fit"].includes(l.status)).length;
  $("metricTotal").textContent = state.leads.length;
  $("metricOpen").textContent = open;
  $("metricMeetings").textContent = state.leads.filter((l) => l.status === "Meeting").length;
  $("metricWon").textContent = state.leads.filter((l) => l.status === "Won").length;
}

function renderRows() {
  const rows = filteredLeads();
  $("leadCount").textContent = `${rows.length} shown`;
  $("leadRows").innerHTML = rows.length ? rows.map((lead) => {
    const active = lead.id === state.selectedId ? "active" : "";
    const score = scoreLead(lead);
    return `<tr class="${active}" data-id="${lead.id}"><td><strong>${esc(lead.name)}</strong><span>${esc(lead.industry || lead.email || lead.website || "No details")}</span></td><td><span class="status">${esc(lead.status)}</span></td><td><span class="priority ${score >= 75 ? "hot" : score < 50 ? "low" : ""}">${score}</span></td><td>${esc(lead.followup || "--")}</td></tr>`;
  }).join("") : `<tr><td colspan="4" class="empty">No leads yet. Click New lead.</td></tr>`;
}

function renderDetail() {
  const lead = selectedLead();
  $("deleteLeadBtn").disabled = !lead;
  $("detailTitle").textContent = lead ? lead.name : "New lead";
  $("detailScore").textContent = lead ? `${scoreLead(lead)} priority` : "--";
  $("leadName").value = lead?.name || ""; $("leadWebsite").value = lead?.website || ""; $("leadEmail").value = lead?.email || ""; $("leadIndustry").value = lead?.industry || ""; $("leadStatus").value = lead?.status || "New"; $("leadFollowup").value = lead?.followup || ""; $("leadOpportunity").value = lead?.opportunity || ""; $("leadNotes").value = lead?.notes || "";
}

function renderOutreach() {
  const lead = selectedLead();
  const business = lead?.name || state.demo.businessName || "the business";
  const observation = lead?.opportunity || state.demo.observation;
  $("outreachLead").textContent = lead ? business : "No lead";
  $("demoLead").textContent = lead ? business : "No lead";
  $("emailOutput").textContent = `Subject: Question about ${business}'s website\n\nHi,\n\nI was looking at ${business}${lead?.website ? ` (${lead.website})` : ""} and noticed this:\n\n${observation}\n\nI build AI websites and customer intake tools for local businesses, and I mocked up a short concept for how ${business} could turn more visitors into customers.\n\nWould you be open to seeing the 60-second version?`;
  $("followupOutput").textContent = `Subject: Re: Question about ${business}'s website\n\nQuick follow-up in case this got buried.\n\nThe main idea is simple: ${state.demo.build}\n\nShould I send over the demo concept I mocked up for ${business}?`;
}

function fillDemoForm() { const d = state.demo; $("demoName").value = d.businessName; $("demoWebsite").value = d.website; $("demoIndustry").value = d.industry; $("demoGoal").value = d.goal; $("demoObservation").value = d.observation; $("demoBuild").value = d.build; }
function readDemoForm() { state.demo = { businessName: $("demoName").value.trim() || "Local Business", website: normalizeUrl($("demoWebsite").value.trim()), industry: $("demoIndustry").value.trim() || "local business", goal: $("demoGoal").value, observation: $("demoObservation").value.trim(), build: $("demoBuild").value.trim() }; persistLocal(); }

function renderDeck() {
  const d = state.demo;
  const slides = [
    `<section class="slide"><p class="kicker">Custom growth demo</p><h3>${esc(d.businessName || "Local Business")} can convert more visitors.</h3><p>${esc(d.observation)}</p><div class="mini-site"><strong>${esc(d.businessName || "Business")}</strong><span>${esc(d.goal)}</span><button>Book / Contact</button></div></section>`,
    `<section class="slide"><p class="kicker">Customer path</p><h3>Make the next step obvious.</h3><div class="steps"><span>Discover</span><span>Understand</span><span>Ask AI</span><span>Book</span></div></section>`,
    `<section class="slide"><p class="kicker">AI assistant</p><h3>A 24/7 front desk.</h3><p>Answers common questions, qualifies leads, and routes serious visitors to the right action.</p></section>`,
    `<section class="slide"><p class="kicker">Recommended build</p><h3>What to build first.</h3><p>${esc(d.build)}</p></section>`,
    `<section class="slide"><p class="kicker">Next step</p><h3>Validate with a 15 minute call.</h3><p>Confirm services, goals, pages, and the fastest useful launch.</p></section>`,
  ];
  $("deck").innerHTML = slides.join(""); showSlide(state.activeSlide);
}
function showSlide(i) { const slides = [...document.querySelectorAll(".slide")]; if (!slides.length) return; state.activeSlide = (i + slides.length) % slides.length; slides.forEach((s, idx) => s.classList.toggle("active", idx === state.activeSlide)); $("slideCounter").textContent = `${state.activeSlide + 1} / ${slides.length}`; }

function exportJson() { const blob = new Blob([JSON.stringify(sharedPayload(), null, 2)], { type: "application/json" }); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = "marketer-crm-backup.json"; a.click(); URL.revokeObjectURL(url); }
function importJsonFile(file) { if (!file) return; const reader = new FileReader(); reader.onload = () => { try { const data = JSON.parse(String(reader.result || "{}")); state.leads = Array.isArray(data.leads) ? data.leads : []; state.selectedId = data.selectedId || state.leads[0]?.id || null; state.demo = { ...defaultDemo, ...(data.demo || {}) }; persistLocal(); renderAll(); } catch (e) { setSync(`Import failed: ${e.message}`, "bad"); } }; reader.readAsText(file); }
function copyText(id) { navigator.clipboard.writeText($(id).textContent); }

async function recordVideo() {
  const status = $("videoStatus"); const canvas = $("videoCanvas");
  if (!("MediaRecorder" in window)) { status.textContent = "Recording is not supported in this browser."; return; }
  const ctx = canvas.getContext("2d"); const stream = canvas.captureStream(30); const mimeType = ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"].find((t) => MediaRecorder.isTypeSupported(t));
  if (!mimeType) { status.textContent = "This browser cannot record WebM video."; return; }
  const chunks = []; const recorder = new MediaRecorder(stream, { mimeType }); recorder.ondataavailable = (e) => chunks.push(e.data); recorder.onstop = () => { const url = URL.createObjectURL(new Blob(chunks, { type: "video/webm" })); const link = $("videoDownload"); link.href = url; link.download = `${(state.demo.businessName || "demo").replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.webm`; link.hidden = false; link.textContent = "Download video"; status.textContent = "Video ready."; };
  recorder.start(); let frame = 0; const frames = [["Custom demo", state.demo.businessName, state.demo.goal], ["Opportunity", state.demo.observation, ""], ["Recommended build", state.demo.build, ""]];
  const interval = setInterval(() => { const f = frames[Math.floor(frame / 90) % frames.length]; ctx.fillStyle = "#f6f8fb"; ctx.fillRect(0,0,1280,720); ctx.fillStyle = "#14315f"; ctx.fillRect(0,0,1280,110); ctx.fillStyle = "white"; ctx.font = "800 34px system-ui"; ctx.fillText("Marketer CRM", 60,70); ctx.fillStyle = "#172033"; ctx.font = "800 60px system-ui"; ctx.fillText(f[0], 70,250); ctx.fillStyle = "#14315f"; ctx.font = "800 42px system-ui"; ctx.fillText(String(f[1]).slice(0,48), 70,360); ctx.fillStyle = "#667085"; ctx.font = "500 30px system-ui"; ctx.fillText(String(f[2]).slice(0,68), 70,450); frame++; }, 1000/30);
  status.textContent = "Recording 10 second demo..."; setTimeout(() => { clearInterval(interval); recorder.stop(); }, 10000);
}

function saveDbConfig() { localStorage.setItem(DB_CONFIG_KEY, JSON.stringify({ url: $("supabaseUrl").value.trim(), anonKey: $("supabaseAnonKey").value.trim(), workspaceId: $("workspaceId").value.trim() || "summit-team" })); setSync("Database settings saved. Reloading shared workspace..."); loadShared(); }
function fillSettings() { const c = getDbConfig(); $("supabaseUrl").value = c.url; $("supabaseAnonKey").value = c.anonKey; $("workspaceId").value = c.workspaceId; }

function renderAll() { renderMetrics(); renderRows(); renderDetail(); fillDemoForm(); renderOutreach(); renderDeck(); }

function bindEvents() {
  document.querySelectorAll(".rail-btn").forEach((btn) => btn.addEventListener("click", () => { document.querySelectorAll(".rail-btn").forEach((b) => b.classList.remove("active")); document.querySelectorAll(".view").forEach((v) => v.classList.remove("active")); btn.classList.add("active"); $(`${btn.dataset.view}View`).classList.add("active"); }));
  $("newLeadBtn").addEventListener("click", blankLead); $("syncNowBtn").addEventListener("click", () => saveShared(false, true)); $("searchInput").addEventListener("input", renderRows); $("statusFilter").addEventListener("change", renderRows); $("leadForm").addEventListener("submit", saveLead); $("deleteLeadBtn").addEventListener("click", deleteLead);
  $("leadRows").addEventListener("click", (e) => { const tr = e.target.closest("tr[data-id]"); if (!tr) return; state.selectedId = tr.dataset.id; hydrateFromLead(selectedLead()); persistLocal(); renderAll(); });
  $("demoForm").addEventListener("submit", (e) => { e.preventDefault(); readDemoForm(); renderAll(); }); $("prevSlideBtn").addEventListener("click", () => showSlide(state.activeSlide - 1)); $("nextSlideBtn").addEventListener("click", () => showSlide(state.activeSlide + 1)); $("printDeckBtn").addEventListener("click", () => window.print()); $("recordVideoBtn").addEventListener("click", recordVideo);
  $("copyEmailBtn").addEventListener("click", () => copyText("emailOutput")); $("copyFollowupBtn").addEventListener("click", () => copyText("followupOutput")); $("markContactedBtn").addEventListener("click", () => { const lead = selectedLead(); if (!lead) return; lead.status = "Contacted"; persistLocal(); renderAll(); });
  $("saveDbConfigBtn").addEventListener("click", saveDbConfig); $("loadSharedBtn").addEventListener("click", loadShared); $("exportJsonBtn").addEventListener("click", exportJson); $("importJsonBtn").addEventListener("click", () => $("importJsonInput").click()); $("importJsonInput").addEventListener("change", (e) => importJsonFile(e.target.files[0]));
}

loadLocal(); bindEvents(); fillSettings(); renderAll(); setTimeout(loadShared, 250);
