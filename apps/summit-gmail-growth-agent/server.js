import http from "node:http";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { existsSync, createReadStream, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import crypto from "node:crypto";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(__dirname, "public");
const dataDir = path.join(__dirname, "data");
const dbPath = path.join(dataDir, "db.json");
const env = loadEnv(path.join(__dirname, ".env"));
const PORT = Number(env.PORT || process.env.PORT || 5180);
const REDIRECT_URI = `http://localhost:${PORT}/oauth2callback`;
const SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"];

function loadEnv(file) {
  const out = {};
  if (!existsSync(file)) return out;
  const text = readFileSync(file, "utf8");
  for (const line of text.split(/\r?\n/)) {
    const clean = line.trim();
    if (!clean || clean.startsWith("#")) continue;
    const index = clean.indexOf("=");
    if (index > 0) out[clean.slice(0, index)] = clean.slice(index + 1);
  }
  return out;
}

async function readDb() {
  await mkdir(dataDir, { recursive: true });
  if (!existsSync(dbPath)) {
    return { tokens: null, leads: [], messages: [], strategy: null, sync: null };
  }
  return JSON.parse(await readFile(dbPath, "utf8"));
}

async function writeDb(db) {
  await mkdir(dataDir, { recursive: true });
  await writeFile(dbPath, JSON.stringify(db, null, 2));
}

function sendJson(res, body, status = 200) {
  res.writeHead(status, { "content-type": "application/json" });
  res.end(JSON.stringify(body));
}

async function readBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const text = Buffer.concat(chunks).toString("utf8");
  return text ? JSON.parse(text) : {};
}

function oauthConfig() {
  return {
    clientId: env.GOOGLE_CLIENT_ID || process.env.GOOGLE_CLIENT_ID,
    clientSecret: env.GOOGLE_CLIENT_SECRET || process.env.GOOGLE_CLIENT_SECRET,
  };
}

function getAuthUrl() {
  const { clientId } = oauthConfig();
  if (!clientId) return null;
  const state = crypto.randomBytes(12).toString("hex");
  const url = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("redirect_uri", REDIRECT_URI);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("scope", SCOPES.join(" "));
  url.searchParams.set("access_type", "offline");
  url.searchParams.set("prompt", "consent");
  url.searchParams.set("state", state);
  return url.toString();
}

async function exchangeCode(code) {
  const { clientId, clientSecret } = oauthConfig();
  const response = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: clientId,
      client_secret: clientSecret,
      redirect_uri: REDIRECT_URI,
      grant_type: "authorization_code",
    }),
  });
  if (!response.ok) throw new Error(await response.text());
  const token = await response.json();
  return { ...token, expires_at: Date.now() + token.expires_in * 1000 };
}

async function refreshAccessToken(db) {
  if (!db.tokens?.refresh_token) throw new Error("No refresh token saved.");
  if (db.tokens.access_token && db.tokens.expires_at && db.tokens.expires_at - Date.now() > 60_000) return db.tokens.access_token;
  const { clientId, clientSecret } = oauthConfig();
  const response = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      refresh_token: db.tokens.refresh_token,
      grant_type: "refresh_token",
    }),
  });
  if (!response.ok) throw new Error(await response.text());
  const token = await response.json();
  db.tokens = { ...db.tokens, ...token, expires_at: Date.now() + token.expires_in * 1000 };
  await writeDb(db);
  return db.tokens.access_token;
}

async function gmailFetch(db, endpoint) {
  const accessToken = await refreshAccessToken(db);
  const response = await fetch(`https://gmail.googleapis.com/gmail/v1/users/me/${endpoint}`, {
    headers: { authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function listMessageIds(db, q, max = 250) {
  const ids = [];
  let pageToken = "";
  while (ids.length < max) {
    const params = new URLSearchParams({ q, maxResults: String(Math.min(100, max - ids.length)) });
    if (pageToken) params.set("pageToken", pageToken);
    const data = await gmailFetch(db, `messages?${params}`);
    ids.push(...(data.messages || []).map((m) => m.id));
    pageToken = data.nextPageToken;
    if (!pageToken) break;
  }
  return ids;
}

async function getMetadata(db, id) {
  const headers = ["Subject", "From", "To", "Cc", "Bcc", "Date", "Message-ID", "In-Reply-To", "References"];
  const params = new URLSearchParams({ format: "metadata" });
  headers.forEach((h) => params.append("metadataHeaders", h));
  const msg = await gmailFetch(db, `messages/${id}?${params}`);
  const headerMap = {};
  for (const header of msg.payload?.headers || []) headerMap[header.name.toLowerCase()] = header.value;
  return {
    id: msg.id,
    threadId: msg.threadId,
    labelIds: msg.labelIds || [],
    snippet: msg.snippet || "",
    internalDate: Number(msg.internalDate || 0),
    subject: cleanSubject(headerMap.subject || ""),
    from: headerMap.from || "",
    to: headerMap.to || "",
    cc: headerMap.cc || "",
    bcc: headerMap.bcc || "",
    date: headerMap.date || "",
    messageId: headerMap["message-id"] || "",
    inReplyTo: headerMap["in-reply-to"] || "",
    references: headerMap.references || "",
  };
}

async function syncGmail() {
  const db = await readDb();
  if (!db.tokens) throw new Error("Connect Gmail first.");
  const labels = await gmailFetch(db, "labels");
  const labelNames = Object.fromEntries((labels.labels || []).map((l) => [l.id, l.name]));
  const openedLabelIds = new Set((labels.labels || []).filter((l) => /opened/i.test(l.name)).map((l) => l.id));

  const [sentIds, inboxIds] = await Promise.all([
    listMessageIds(db, "in:sent newer_than:180d", 350),
    listMessageIds(db, "in:inbox newer_than:180d", 350),
  ]);
  const uniqueIds = [...new Set([...sentIds, ...inboxIds])];
  const messages = [];
  for (const id of uniqueIds) {
    messages.push(await getMetadata(db, id));
  }

  const sentSet = new Set(sentIds);
  const inboxSet = new Set(inboxIds);
  const inboundThreads = new Set(messages.filter((m) => inboxSet.has(m.id)).map((m) => m.threadId));
  const sent = messages.filter((m) => sentSet.has(m.id)).map((m) => ({
    ...m,
    kind: "sent",
    opened: m.labelIds.some((id) => openedLabelIds.has(id) || /opened/i.test(labelNames[id] || "")),
    replied: inboundThreads.has(m.threadId),
    recipients: parseRecipients(`${m.to}, ${m.cc}, ${m.bcc}`),
  }));

  db.messages = [...sent, ...messages.filter((m) => inboxSet.has(m.id)).map((m) => ({ ...m, kind: "inbox" }))];
  db.strategy = analyzeStrategy(sent);
  db.leads = mergeLeads(db.leads || [], sent);
  db.sync = { at: new Date().toISOString(), sent: sent.length, inbox: inboxIds.length, labels: labels.labels?.length || 0 };
  await writeDb(db);
  return { sync: db.sync, strategy: db.strategy, leads: db.leads };
}

function mergeLeads(existing, sent) {
  const byEmail = new Map(existing.map((lead) => [lead.email, lead]));
  for (const msg of sent) {
    for (const email of msg.recipients) {
      if (!email || email.includes("example.") || email === "your@email.com") continue;
      const lead = byEmail.get(email) || {
        id: crypto.randomUUID(),
        email,
        business: inferBusiness(email),
        website: inferWebsite(email),
        status: "New",
        sent: 0,
        opened: 0,
        replied: 0,
        subjects: [],
        lastContact: null,
        notes: "",
      };
      lead.sent += 1;
      lead.opened += msg.opened ? 1 : 0;
      lead.replied += msg.replied ? 1 : 0;
      lead.status = msg.replied ? "Replied" : msg.opened ? "Opened" : lead.status;
      lead.lastContact = new Date(msg.internalDate).toISOString();
      if (msg.subject && !lead.subjects.includes(msg.subject)) lead.subjects.push(msg.subject);
      byEmail.set(email, lead);
    }
  }
  return [...byEmail.values()].sort((a, b) => (b.replied - a.replied) || (b.opened - a.opened) || (b.sent - a.sent));
}

function analyzeStrategy(sent) {
  const features = [
    ["specificBusiness", (s) => hasBusinessName(s.subject)],
    ["question", (s) => /\?/.test(s.subject) || /\bquestion\b/i.test(s.subject)],
    ["followUp", (s) => /follow[- ]?up|following up|checking in/i.test(s.subject)],
    ["shortSubject", (s) => s.subject.length <= 45],
    ["longSubject", (s) => s.subject.length >= 90],
    ["quickIdea", (s) => /quick idea/i.test(s.subject)],
    ["free", (s) => /\bfree\b|no cost/i.test(s.subject)],
    ["studentRadnor", (s) => /radnor|student|highschool|high school/i.test(s.subject)],
    ["demoMeeting", (s) => /demo|meeting|call/i.test(s.subject)],
  ];

  const overall = summarize(sent);
  const featureStats = features.map(([name, fn]) => {
    const yes = sent.filter(fn);
    const no = sent.filter((s) => !fn(s));
    return { name, count: yes.length, ...summarize(yes), without: summarize(no) };
  });

  const subjectWords = wordStats(sent);
  const recommendations = buildRecommendations(overall, featureStats);
  return { overall, featureStats, subjectWords, recommendations, updatedAt: new Date().toISOString() };
}

function summarize(items) {
  const count = items.length;
  const opened = items.filter((m) => m.opened).length;
  const replied = items.filter((m) => m.replied).length;
  return {
    count,
    opened,
    replied,
    openRate: count ? Math.round((opened / count) * 1000) / 10 : 0,
    replyRate: count ? Math.round((replied / count) * 1000) / 10 : 0,
  };
}

function wordStats(sent) {
  const stop = new Set("the and for with from your you our about this that are was website online presence quick idea".split(" "));
  const map = new Map();
  for (const msg of sent) {
    const words = new Set((msg.subject.toLowerCase().match(/[a-z][a-z0-9'-]{2,}/g) || []).filter((w) => !stop.has(w)));
    for (const word of words) {
      const stat = map.get(word) || { word, count: 0, opened: 0, replied: 0 };
      stat.count += 1;
      stat.opened += msg.opened ? 1 : 0;
      stat.replied += msg.replied ? 1 : 0;
      map.set(word, stat);
    }
  }
  return [...map.values()]
    .filter((s) => s.count >= 3)
    .map((s) => ({ ...s, openRate: Math.round((s.opened / s.count) * 1000) / 10, replyRate: Math.round((s.replied / s.count) * 1000) / 10 }))
    .sort((a, b) => b.replyRate - a.replyRate || b.openRate - a.openRate)
    .slice(0, 24);
}

function buildRecommendations(overall, stats) {
  const byName = Object.fromEntries(stats.map((s) => [s.name, s]));
  const tips = [];
  if (byName.shortSubject?.replyRate >= byName.shortSubject?.without.replyRate) tips.push("Keep subject lines under 45 characters.");
  if (byName.longSubject?.replyRate < overall.replyRate) tips.push("Avoid long scraped-looking website-title subjects.");
  if (byName.question?.replyRate >= overall.replyRate || byName.question?.openRate >= overall.openRate) tips.push("Use question framing when the ask is specific.");
  if (byName.followUp?.openRate >= overall.openRate) tips.push("Follow-up language works when there is real context.");
  if (byName.quickIdea?.openRate < overall.openRate) tips.push("Use 'quick idea' less often; make it more specific when used.");
  if (byName.studentRadnor?.openRate < overall.openRate) tips.push("Do not lead with the student/Radnor angle in cold subjects.");
  if (byName.free?.replyRate < overall.replyRate) tips.push("Mention no-cost later, not as the main hook.");
  return tips.length ? tips : ["Lead with business-specific observations, short subjects, and a concrete next step."];
}

function parseRecipients(value) {
  return [...new Set((value.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g) || []).map((x) => x.toLowerCase()))];
}

function cleanSubject(subject) {
  return subject.replace(/=\?[^?]+\?[BQ]\?[^?]+\?=/gi, "").replace(/^(re|fw|fwd):\s*/i, "").replace(/\s+/g, " ").trim();
}

function hasBusinessName(subject) {
  return /[A-Z][a-z]+(?:\s+[A-Z][a-z]+)|'s|&|LLC|Studio|Pottery|Salon|Realty|Dental|Fitness|Florist|Roofing|Electric/i.test(subject);
}

function inferBusiness(email) {
  const domain = email.split("@")[1] || "";
  return domain.split(".")[0].replace(/[-_]/g, " ").replace(/\b\w/g, (m) => m.toUpperCase());
}

function inferWebsite(email) {
  const domain = email.split("@")[1] || "";
  return domain && !/gmail|yahoo|icloud|outlook|hotmail|comcast|verizon/.test(domain) ? `https://${domain}` : "";
}

function buildDraft(lead, strategy) {
  const business = lead.business || inferBusiness(lead.email);
  const observation = lead.notes || `I noticed there may be a practical opportunity to make ${business}'s website convert more visitors into calls, bookings, or quote requests.`;
  const subject = `Question about ${business}'s website`;
  return {
    subject,
    body: `Hi,\n\nI was looking at ${business}${lead.website ? ` (${lead.website})` : ""} and noticed this:\n\n${observation}\n\nI build AI websites and customer intake tools for local businesses, and I can mock up a short demo showing how ${business} could turn more visitors into customers.\n\nWould you be open to seeing the 60-second version?`,
    strategyNotes: strategy?.recommendations || [],
  };
}

async function route(req, res) {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  try {
    if (url.pathname === "/api/auth/url") return sendJson(res, { url: getAuthUrl(), redirectUri: REDIRECT_URI, configured: Boolean(oauthConfig().clientId && oauthConfig().clientSecret) });
    if (url.pathname === "/oauth2callback") {
      const token = await exchangeCode(url.searchParams.get("code"));
      const db = await readDb();
      db.tokens = db.tokens?.refresh_token && !token.refresh_token ? { ...token, refresh_token: db.tokens.refresh_token } : token;
      await writeDb(db);
      res.writeHead(302, { location: "/?connected=1" });
      return res.end();
    }
    if (url.pathname === "/api/status") {
      const db = await readDb();
      return sendJson(res, { connected: Boolean(db.tokens), sync: db.sync, strategy: db.strategy, leads: db.leads || [] });
    }
    if (url.pathname === "/api/sync" && req.method === "POST") return sendJson(res, await syncGmail());
    if (url.pathname === "/api/leads" && req.method === "POST") {
      const body = await readBody(req);
      const db = await readDb();
      db.leads = body.leads || [];
      await writeDb(db);
      return sendJson(res, { leads: db.leads });
    }
    if (url.pathname === "/api/draft" && req.method === "POST") {
      const body = await readBody(req);
      const db = await readDb();
      return sendJson(res, buildDraft(body.lead, db.strategy));
    }
    return serveStatic(url.pathname, res);
  } catch (error) {
    return sendJson(res, { message: error.message }, 500);
  }
}

function serveStatic(pathname, res) {
  const file = pathname === "/" ? "index.html" : pathname.slice(1);
  const full = path.normalize(path.join(publicDir, file));
  if (!full.startsWith(publicDir) || !existsSync(full)) return sendJson(res, { message: "Not found" }, 404);
  const type = full.endsWith(".css") ? "text/css" : full.endsWith(".js") ? "text/javascript" : "text/html";
  res.writeHead(200, { "content-type": type });
  createReadStream(full).pipe(res);
}

http.createServer(route).listen(PORT, () => {
  console.log(`Summit Gmail Growth Agent running at http://localhost:${PORT}`);
});
