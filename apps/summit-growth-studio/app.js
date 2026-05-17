const STORAGE_KEY = "summit_growth_studio_v1";
const DB_CONFIG_KEY = "summit_growth_studio_supabase_v1";
const DEFAULT_DB_CONFIG = {
  url: "https://wfnkfuxyfblocbinsbaj.supabase.co",
  anonKey: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmbmtmdXh5ZmJsb2NiaW5zYmFqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg5ODMxNjcsImV4cCI6MjA5NDU1OTE2N30.56o_zJbkLfTziOgUUSGaL1oqleIC_mHctmn_fuK1DBk",
  workspaceId: "summit-team",
};

const state = {
  leads: [],
  editingId: null,
  activeSlide: 0,
  demo: {
    businessName: "Mane Techniques",
    website: "https://manetechniques.com",
    industry: "hair salon",
    goal: "More booked appointments",
    observation: "The website has service info, but the booking path could be faster and common customer questions could be answered automatically.",
    build: "AI website assistant, booking guidance, service pages, analytics dashboard, and a faster call-to-action flow.",
  },
};

const $ = (id) => document.getElementById(id);
let isHydrating = false;
let autosaveTimer = null;
let lastSavedHash = "";

function getDbConfig() {
  try {
    const config = JSON.parse(localStorage.getItem(DB_CONFIG_KEY) || "{}");
    return {
      url: String(config.url || DEFAULT_DB_CONFIG.url).replace(/\/+$/, ""),
      anonKey: String(config.anonKey || DEFAULT_DB_CONFIG.anonKey),
      workspaceId: String(config.workspaceId || DEFAULT_DB_CONFIG.workspaceId).trim() || DEFAULT_DB_CONFIG.workspaceId,
    };
  } catch {
    return DEFAULT_DB_CONFIG;
  }
}

function setDbStatus(message, isError = false) {
  const el = $("dbStatus");
  if (!el) return;
  el.textContent = message;
  el.style.color = isError ? "#bd3b3b" : "";
}

function fillDbConfigForm() {
  const config = getDbConfig();
  if ($("supabaseUrl")) $("supabaseUrl").value = config.url;
  if ($("supabaseAnonKey")) $("supabaseAnonKey").value = config.anonKey;
  if ($("workspaceId")) $("workspaceId").value = config.workspaceId;
  if (config.url && config.anonKey) setDbStatus(`Ready to sync workspace "${config.workspaceId}".`);
}

function saveDbConfig() {
  const config = {
    url: $("supabaseUrl").value.trim().replace(/\/+$/, ""),
    anonKey: $("supabaseAnonKey").value.trim(),
    workspaceId: $("workspaceId").value.trim() || "summit-team",
  };
  localStorage.setItem(DB_CONFIG_KEY, JSON.stringify(config));
  setDbStatus(`Saved database settings for workspace "${config.workspaceId}".`);
}

async function supabaseRequest(path, options = {}) {
  const config = getDbConfig();
  if (!config.url || !config.anonKey) throw new Error("Add Supabase URL and anon key first.");
  const res = await fetch(`${config.url}/rest/v1/${path}`, {
    ...options,
    headers: {
      apikey: config.anonKey,
      authorization: `Bearer ${config.anonKey}`,
      "content-type": "application/json",
      ...(options.headers || {}),
    },
  });
  if (!res.ok) throw new Error(await res.text());
  const text = await res.text();
  if (!text) return null;
  return JSON.parse(text);
}

function save() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ leads: state.leads, demo: state.demo }));
  scheduleSharedAutosave();
}

function load() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (!saved) return;
  try {
    const parsed = JSON.parse(saved);
    state.leads = Array.isArray(parsed.leads) ? parsed.leads : [];
    state.demo = { ...state.demo, ...(parsed.demo || {}) };
  } catch {
    state.leads = [];
  }
}

function scoreLead(lead) {
  let score = 35;
  const text = `${lead.name} ${lead.industry} ${lead.opportunity} ${lead.notes}`.toLowerCase();
  if (lead.website) score += 8;
  if (/booking|appointment|quote|call|lead|customer|seo|website|slow|outdated|chatbot|ai/.test(text)) score += 24;
  if (/opened|replied|meeting|won/i.test(lead.status)) score += 25;
  if (/specific|owner|demo|follow/.test(text)) score += 8;
  return Math.min(100, score);
}

function formatUrl(url) {
  if (!url) return "";
  return /^https?:\/\//i.test(url) ? url : `https://${url}`;
}

function getLeadForm() {
  return {
    id: state.editingId || crypto.randomUUID(),
    name: $("leadName").value.trim(),
    website: formatUrl($("leadWebsite").value.trim()),
    email: $("leadEmail").value.trim(),
    industry: $("leadIndustry").value.trim(),
    status: $("leadStatus").value,
    followup: $("leadFollowup").value,
    opportunity: $("leadOpportunity").value.trim(),
    notes: $("leadNotes").value.trim(),
    updatedAt: new Date().toISOString(),
  };
}

function fillLeadForm(lead) {
  state.editingId = lead.id;
  $("leadName").value = lead.name || "";
  $("leadWebsite").value = lead.website || "";
  $("leadEmail").value = lead.email || "";
  $("leadIndustry").value = lead.industry || "";
  $("leadStatus").value = lead.status || "New";
  $("leadFollowup").value = lead.followup || "";
  $("leadOpportunity").value = lead.opportunity || "";
  $("leadNotes").value = lead.notes || "";
}

function clearLeadForm() {
  state.editingId = null;
  $("leadForm").reset();
  $("leadStatus").value = "New";
}

function saveLead(event) {
  event.preventDefault();
  const lead = getLeadForm();
  if (!lead.name) return;
  const index = state.leads.findIndex((item) => item.id === lead.id);
  if (index >= 0) state.leads[index] = lead;
  else state.leads.unshift(lead);
  clearLeadForm();
  save();
  renderAll();
}

function statusClass(score) {
  if (score >= 75) return "score-hot";
  if (score < 50) return "score-cold";
  return "";
}

function renderLeads() {
  const query = $("leadSearch").value.toLowerCase();
  const status = $("statusFilter").value;
  const list = $("leadList");
  const leads = state.leads
    .map((lead) => ({ ...lead, score: scoreLead(lead) }))
    .filter((lead) => status === "All" || lead.status === status)
    .filter((lead) => `${lead.name} ${lead.website} ${lead.email} ${lead.industry} ${lead.opportunity}`.toLowerCase().includes(query))
    .sort((a, b) => b.score - a.score);

  if (!leads.length) {
    list.innerHTML = `<div class="lead-card"><p>No leads yet. Add one or load samples.</p></div>`;
    return;
  }

  list.innerHTML = leads.map((lead) => `
    <article class="lead-card">
      <header>
        <div>
          <h4>${escapeHtml(lead.name)}</h4>
          <span class="pill ${statusClass(lead.score)}">${lead.score} score</span>
          <span class="pill">${escapeHtml(lead.status)}</span>
        </div>
        <span class="pill">${escapeHtml(lead.industry || "local business")}</span>
      </header>
      <p>${escapeHtml(lead.opportunity || "Add a specific opportunity before outreach.")}</p>
      <p>${lead.website ? `<a href="${escapeAttr(lead.website)}" target="_blank" rel="noreferrer">${escapeHtml(lead.website)}</a>` : "No website saved"} ${lead.email ? ` · ${escapeHtml(lead.email)}` : ""}</p>
      <div class="lead-actions">
        <button type="button" data-action="edit" data-id="${lead.id}">Edit</button>
        <button type="button" data-action="demo" data-id="${lead.id}">Build demo</button>
        <button type="button" data-action="opened" data-id="${lead.id}">Mark opened</button>
        <button type="button" data-action="delete" data-id="${lead.id}">Delete</button>
      </div>
    </article>
  `).join("");
}

function renderMetrics() {
  const hot = state.leads.filter((lead) => scoreLead(lead) >= 75).length;
  const today = new Date().toISOString().slice(0, 10);
  const followups = state.leads.filter((lead) => lead.followup && lead.followup <= today && !["Won", "Not fit"].includes(lead.status)).length;
  $("metricLeads").textContent = state.leads.length;
  $("metricHot").textContent = hot;
  $("metricFollowups").textContent = followups;
}

function readDemoForm() {
  state.demo = {
    businessName: $("demoName").value.trim() || "Local Business",
    website: formatUrl($("demoWebsite").value.trim()),
    industry: $("demoIndustry").value.trim() || "local business",
    goal: $("demoGoal").value,
    observation: $("demoObservation").value.trim() || "The current customer journey can be made faster, clearer, and easier to act on.",
    build: $("demoBuild").value.trim() || "AI assistant, clearer conversion path, stronger service pages, and analytics.",
  };
  save();
}

function fillDemoForm() {
  $("demoName").value = state.demo.businessName;
  $("demoWebsite").value = state.demo.website;
  $("demoIndustry").value = state.demo.industry;
  $("demoGoal").value = state.demo.goal;
  $("demoObservation").value = state.demo.observation;
  $("demoBuild").value = state.demo.build;
}

function renderDeck() {
  const d = state.demo;
  const slides = [
    `<section class="slide">
      <div>
        <p class="eyebrow">Custom growth demo</p>
        <h3 class="slide-title">${escapeHtml(d.businessName)} can turn more visitors into customers.</h3>
        <p class="slide-subtitle">A focused AI website assistant and clearer conversion flow built around ${escapeHtml(d.goal.toLowerCase())}.</p>
      </div>
      <div class="visual-grid">
        <div class="mock-browser">
          <div class="browser-bar"><span></span><span></span><span></span></div>
          <div class="mock-hero"><h4>${escapeHtml(d.businessName)}</h4><p>${escapeHtml(d.goal)}</p><span class="mock-button">Book / Contact</span></div>
        </div>
        <div class="proof-card"><strong>What we noticed</strong><p>${escapeHtml(d.observation)}</p></div>
      </div>
    </section>`,
    `<section class="slide">
      <div>
        <p class="eyebrow">Customer path</p>
        <h3 class="slide-title">Make the next step obvious in under 10 seconds.</h3>
        <p class="slide-subtitle">The build should guide people from question to action without making them hunt through pages.</p>
      </div>
      <div class="journey-row">
        <div class="journey-card"><strong>Discover</strong><p>Google, social, referral, or direct site visit.</p></div>
        <div class="journey-card"><strong>Understand</strong><p>Services, trust signals, pricing context, availability.</p></div>
        <div class="journey-card"><strong>Ask</strong><p>AI assistant answers common questions instantly.</p></div>
        <div class="journey-card"><strong>Act</strong><p>Book, call, request quote, or submit intake.</p></div>
      </div>
    </section>`,
    `<section class="slide">
      <div>
        <p class="eyebrow">AI assistant concept</p>
        <h3 class="slide-title">A 24/7 front desk for ${escapeHtml(d.businessName)}.</h3>
      </div>
      <div class="visual-grid">
        <div class="mock-phone">
          <div class="chat-bubble">Hi, what can I help you find?</div>
          <div class="chat-bubble user">Do you have openings this week?</div>
          <div class="chat-bubble">Yes. I can show the best next options and collect the details needed before booking.</div>
          <div class="chat-bubble user">Can I see services?</div>
          <div class="chat-bubble">Here are the recommended services for your goal.</div>
        </div>
        <ul class="deck-list">
          <li>Answers repeat questions before the owner has to respond.</li>
          <li>Routes serious customers toward the right next action.</li>
          <li>Captures intent, service interest, and contact details.</li>
          <li>Gives you better follow-up data than a basic contact form.</li>
        </ul>
      </div>
    </section>`,
    `<section class="slide">
      <div>
        <p class="eyebrow">Recommended build</p>
        <h3 class="slide-title">What I would build first.</h3>
        <p class="slide-subtitle">${escapeHtml(d.build)}</p>
      </div>
      <ul class="deck-list">
        <li><strong>Conversion homepage:</strong> clearer headline, trust proof, service paths, and primary CTA.</li>
        <li><strong>AI intake assistant:</strong> answers questions and qualifies visitors by need.</li>
        <li><strong>Service pages:</strong> stronger Google visibility for high-intent searches.</li>
        <li><strong>Owner dashboard:</strong> leads, common questions, and conversion activity in one place.</li>
      </ul>
    </section>`,
    `<section class="slide">
      <div>
        <p class="eyebrow">Next step</p>
        <h3 class="slide-title">A short demo call is enough to validate fit.</h3>
        <p class="slide-subtitle">If this looks useful, the next step is a 15 minute call to confirm goals, pages, services, and the fastest launch path.</p>
      </div>
      <div class="visual-grid">
        <div class="proof-card"><strong>No service fee</strong><p>Client covers domain and hosting. Finished code and assets belong to the client.</p></div>
        <div class="proof-card"><strong>Fast pilot</strong><p>Start with the smallest useful version: lead capture, AI FAQ, and conversion-focused page flow.</p></div>
      </div>
    </section>`,
  ];
  $("deck").innerHTML = slides.join("");
  showSlide(Math.min(state.activeSlide, slides.length - 1));
  renderOutreach();
}

function showSlide(index) {
  const slides = [...document.querySelectorAll(".slide")];
  state.activeSlide = (index + slides.length) % slides.length;
  slides.forEach((slide, i) => slide.classList.toggle("active", i === state.activeSlide));
  $("slideCounter").textContent = `${state.activeSlide + 1} / ${slides.length}`;
}

function renderOutreach() {
  const d = state.demo;
  $("emailOutput").textContent = `Subject: Question about ${d.businessName}'s website

Hi,

I was looking at ${d.businessName}${d.website ? ` (${d.website})` : ""} and noticed this:

${d.observation}

I build AI websites and customer intake tools for local businesses, and I made a short demo concept for how ${d.businessName} could get ${d.goal.toLowerCase()}.

Would you be open to seeing the 60-second version?`;

  $("followupOutput").textContent = `Subject: Re: Question about ${d.businessName}'s website

Quick follow-up in case this got buried.

The main idea is simple: ${d.build}

Should I send over the demo page I mocked up for ${d.businessName}?`;
}

function saveDemoAsLead() {
  readDemoForm();
  const lead = {
    id: crypto.randomUUID(),
    name: state.demo.businessName,
    website: state.demo.website,
    email: "",
    industry: state.demo.industry,
    status: "Researched",
    followup: "",
    opportunity: state.demo.observation,
    notes: `Recommended build: ${state.demo.build}`,
    updatedAt: new Date().toISOString(),
  };
  state.leads.unshift(lead);
  save();
  renderAll();
}

function seedLeads() {
  const samples = [
    ["Mane Techniques", "https://manetechniques.com", "salon", "Booking and service questions could be handled faster with an AI assistant."],
    ["Blue Skies Pottery", "https://blueskiespottery.com", "pottery studio", "Product discovery and class questions could convert better with guided shopping."],
    ["Solo Realty", "https://solorealty.com", "real estate", "Property inquiries could be routed into a clearer intake flow."],
  ];
  state.leads = samples.map(([name, website, industry, opportunity]) => ({
    id: crypto.randomUUID(),
    name,
    website,
    email: "",
    industry,
    status: "Researched",
    followup: "",
    opportunity,
    notes: "Sample lead based on your strongest open-rate patterns.",
    updatedAt: new Date().toISOString(),
  }));
  save();
  renderAll();
}

async function recordVideo() {
  readDemoForm();
  const button = $("recordVideoBtn");
  const status = $("videoStatus");
  const download = $("videoDownload");
  download.hidden = true;
  status.textContent = "";

  if (!("MediaRecorder" in window)) {
    status.textContent = "This browser does not support built-in video recording. Try Chrome or Edge.";
    return;
  }

  const canvas = $("videoCanvas");
  const ctx = canvas.getContext("2d");
  const stream = canvas.captureStream(30);
  const mimeType = [
    "video/webm;codecs=vp9",
    "video/webm;codecs=vp8",
    "video/webm",
  ].find((type) => MediaRecorder.isTypeSupported(type));
  if (!mimeType) {
    status.textContent = "This browser cannot record WebM video from a canvas.";
    return;
  }

  const chunks = [];
  let recorder;
  try {
    recorder = new MediaRecorder(stream, { mimeType });
  } catch (error) {
    status.textContent = `Recorder failed to start: ${error.message}`;
    return;
  }

  recorder.ondataavailable = (event) => chunks.push(event.data);
  recorder.onstop = () => {
    const blob = new Blob(chunks, { type: "video/webm" });
    const url = URL.createObjectURL(blob);
    const link = download;
    link.href = url;
    link.download = `${state.demo.businessName.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}-demo.webm`;
    link.hidden = false;
    link.textContent = "Download video";
    status.textContent = "Video ready.";
    button.disabled = false;
    button.textContent = "Record video";
  };

  recorder.onerror = () => {
    status.textContent = "Recording failed. Try Chrome, then reload the page.";
    button.disabled = false;
    button.textContent = "Record video";
  };

  button.disabled = true;
  button.textContent = "Recording...";
  status.textContent = "Recording a 12-second demo video...";
  recorder.start();

  const frames = [
    ["Custom AI website demo", state.demo.businessName, state.demo.goal],
    ["What we noticed", state.demo.observation, "Clearer path from visitor to customer"],
    ["Recommended build", state.demo.build, "AI assistant + service pages + analytics"],
    ["Next step", "60-second demo walkthrough", "15 minute strategy call"],
  ];

  let frame = 0;
  drawVideoFrame(ctx, frames[0], frame);
  const interval = setInterval(() => {
    const f = frames[Math.floor(frame / 90) % frames.length];
    drawVideoFrame(ctx, f, frame);
    frame++;
  }, 1000 / 30);

  setTimeout(() => {
    clearInterval(interval);
    recorder.stop();
  }, 12000);
}

function drawVideoFrame(ctx, lines, frame) {
  const w = ctx.canvas.width;
  const h = ctx.canvas.height;
  const pulse = Math.sin(frame / 18) * 20;
  ctx.fillStyle = "#f4f7fb";
  ctx.fillRect(0, 0, w, h);
  ctx.fillStyle = "#14315f";
  ctx.fillRect(0, 0, w, 110);
  ctx.fillStyle = "#f47b20";
  ctx.fillRect(0, 110, w, 8);
  ctx.fillStyle = "#ffffff";
  ctx.font = "700 30px system-ui";
  ctx.fillText("Summit Growth Studio", 58, 68);
  ctx.fillStyle = "#ffffff";
  ctx.globalAlpha = 0.16;
  ctx.beginPath();
  ctx.arc(1030, 360, 190 + pulse, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.fillStyle = "#172033";
  ctx.font = "800 58px system-ui";
  wrapCanvasText(ctx, lines[0], 70, 230, 880, 68);
  ctx.fillStyle = "#14315f";
  ctx.font = "800 42px system-ui";
  wrapCanvasText(ctx, lines[1], 70, 360, 900, 52);
  ctx.fillStyle = "#667085";
  ctx.font = "500 30px system-ui";
  wrapCanvasText(ctx, lines[2], 70, 485, 860, 40);
  ctx.fillStyle = "#16845b";
  ctx.fillRect(70, 610, 330, 58);
  ctx.fillStyle = "#ffffff";
  ctx.font = "800 24px system-ui";
  ctx.fillText("See the demo concept", 96, 647);
}

function wrapCanvasText(ctx, text, x, y, maxWidth, lineHeight) {
  const words = String(text).split(/\s+/);
  let line = "";
  for (const word of words) {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width > maxWidth && line) {
      ctx.fillText(line, x, y);
      line = word;
      y += lineHeight;
    } else {
      line = test;
    }
  }
  ctx.fillText(line, x, y);
}

function exportJson() {
  const blob = new Blob([JSON.stringify({ leads: state.leads, demo: state.demo }, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "summit-growth-studio-data.json";
  link.click();
  URL.revokeObjectURL(url);
}

function sharedPayload() {
  return { leads: state.leads, demo: state.demo };
}

function sharedPayloadHash() {
  return JSON.stringify(sharedPayload());
}

function scheduleSharedAutosave() {
  if (isHydrating) return;
  const config = getDbConfig();
  if (!config.url || !config.anonKey) return;
  window.clearTimeout(autosaveTimer);
  autosaveTimer = window.setTimeout(() => saveSharedState({ silent: true }), 900);
}

async function loadSharedState() {
  const config = getDbConfig();
  setDbStatus("Loading shared workspace...");
  try {
    const rows = await supabaseRequest(`marketing_engine_states?id=eq.${encodeURIComponent(config.workspaceId)}&select=data,updated_at`);
    if (!rows.length) {
      setDbStatus(`Creating shared workspace "${config.workspaceId}"...`);
      await saveSharedState({ silent: true, force: true });
      return;
    }
    const data = rows[0].data || {};
    isHydrating = true;
    state.leads = Array.isArray(data.leads) ? data.leads : [];
    state.demo = { ...state.demo, ...(data.demo || {}) };
    save();
    isHydrating = false;
    lastSavedHash = sharedPayloadHash();
    renderAll();
    setDbStatus(`Loaded shared workspace "${config.workspaceId}" from ${new Date(rows[0].updated_at).toLocaleString()}.`);
  } catch (error) {
    isHydrating = false;
    setDbStatus(`Load failed: ${error.message}`, true);
  }
}

async function saveSharedState(options = {}) {
  const config = getDbConfig();
  const hash = sharedPayloadHash();
  if (!options.force && hash === lastSavedHash) {
    if (!options.silent) setDbStatus(`No changes to sync for "${config.workspaceId}".`);
    return;
  }
  if (!options.silent) setDbStatus("Saving shared workspace...");
  try {
    await supabaseRequest("marketing_engine_states?on_conflict=id", {
      method: "POST",
      headers: { prefer: "resolution=merge-duplicates,return=minimal" },
      body: JSON.stringify({
        id: config.workspaceId,
        data: sharedPayload(),
        updated_at: new Date().toISOString(),
      }),
    });
    lastSavedHash = hash;
    setDbStatus(`${options.silent ? "Autosaved" : "Saved"} shared workspace "${config.workspaceId}" at ${new Date().toLocaleTimeString()}.`);
  } catch (error) {
    setDbStatus(`Save failed: ${error.message}`, true);
  }
}

function importJsonFile(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const imported = JSON.parse(String(reader.result || "{}"));
      if (!Array.isArray(imported.leads)) throw new Error("Missing leads array.");
      state.leads = imported.leads;
      state.demo = { ...state.demo, ...(imported.demo || {}) };
      save();
      renderAll();
      setDbStatus("Imported campaign data. Autosave will sync it.");
    } catch (error) {
      alert(`Import failed: ${error.message}`);
    }
  };
  reader.readAsText(file);
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#96;");
}

function copyText(id) {
  navigator.clipboard.writeText($(id).textContent);
}

function bindEvents() {
  document.querySelectorAll(".nav-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".nav-tab").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
      tab.classList.add("active");
      $(`${tab.dataset.view}View`).classList.add("active");
      $("viewTitle").textContent = tab.textContent;
    });
  });

  $("leadForm").addEventListener("submit", saveLead);
  $("clearLeadBtn").addEventListener("click", clearLeadForm);
  $("leadSearch").addEventListener("input", renderLeads);
  $("statusFilter").addEventListener("change", renderLeads);
  $("seedLeadsBtn").addEventListener("click", seedLeads);
  $("exportJsonBtn").addEventListener("click", exportJson);
  $("exportJsonBtnSecondary").addEventListener("click", exportJson);
  $("saveDbConfigBtn").addEventListener("click", saveDbConfig);
  $("loadSharedBtn").addEventListener("click", loadSharedState);
  $("loadSharedBtnSecondary").addEventListener("click", loadSharedState);
  $("saveSharedBtn").addEventListener("click", saveSharedState);
  $("saveSharedBtnSecondary").addEventListener("click", saveSharedState);
  $("importJsonBtn").addEventListener("click", () => $("importJsonInput").click());
  $("importJsonBtnSecondary").addEventListener("click", () => $("importJsonInput").click());
  $("importJsonInput").addEventListener("change", (event) => importJsonFile(event.target.files[0]));
  $("demoForm").addEventListener("submit", (event) => {
    event.preventDefault();
    readDemoForm();
    renderDeck();
  });
  $("saveDemoLeadBtn").addEventListener("click", saveDemoAsLead);
  $("prevSlideBtn").addEventListener("click", () => showSlide(state.activeSlide - 1));
  $("nextSlideBtn").addEventListener("click", () => showSlide(state.activeSlide + 1));
  $("printDeckBtn").addEventListener("click", () => window.print());
  $("recordVideoBtn").addEventListener("click", recordVideo);
  $("copyEmailBtn").addEventListener("click", () => copyText("emailOutput"));
  $("copyFollowupBtn").addEventListener("click", () => copyText("followupOutput"));

  $("leadList").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    const lead = state.leads.find((item) => item.id === button.dataset.id);
    if (!lead) return;
    if (button.dataset.action === "edit") fillLeadForm(lead);
    if (button.dataset.action === "delete") state.leads = state.leads.filter((item) => item.id !== lead.id);
    if (button.dataset.action === "opened") lead.status = "Opened";
    if (button.dataset.action === "demo") {
      state.demo = {
        ...state.demo,
        businessName: lead.name,
        website: lead.website,
        industry: lead.industry || "local business",
        observation: lead.opportunity || state.demo.observation,
        build: lead.notes?.replace(/^Recommended build:\s*/i, "") || state.demo.build,
      };
      fillDemoForm();
      renderDeck();
      document.querySelector('[data-view="demo"]').click();
    }
    save();
    renderAll();
  });
}

function renderAll() {
  renderMetrics();
  renderLeads();
  fillDemoForm();
  renderDeck();
}

load();
bindEvents();
renderAll();
fillDbConfigForm();
window.setTimeout(loadSharedState, 250);
