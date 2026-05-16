import { NextRequest, NextResponse } from "next/server";
import Groq from "groq-sdk";
import { getClientIp, isValidOrigin, RateLimiter, truncate } from "@/lib/api-security";
import {
  buildFallbackProspectAnalysis,
  parseProspects,
  ProspectAnalysis,
  ProspectInput,
  summitMarketingContext,
} from "@/lib/marketing-agent";

const limiter = new RateLimiter(5, 60_000);

function isBlockedHost(hostname: string): boolean {
  const host = hostname.toLowerCase();
  return host === "localhost" || host.endsWith(".local") || host === "0.0.0.0" || host === "127.0.0.1" || host.startsWith("10.") || host.startsWith("192.168.") || /^172\.(1[6-9]|2\d|3[0-1])\./.test(host);
}

async function fetchWebsiteSummary(website?: string): Promise<string> {
  if (!website) return "";
  try {
    const url = new URL(website);
    if (!["http:", "https:"].includes(url.protocol) || isBlockedHost(url.hostname)) return "";
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4_000);
    const response = await fetch(url.toString(), {
      signal: controller.signal,
      headers: { "user-agent": "SummitMarketingAgent/1.0", accept: "text/html, text/plain" },
    });
    clearTimeout(timeout);
    if (!response.ok) return "";
    const html = await response.text();
    return html.replace(/<script[\s\S]*?<\/script>/gi, " ").replace(/<style[\s\S]*?<\/style>/gi, " ").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 2_400);
  } catch {
    return "";
  }
}

function extractJson(text: string): ProspectAnalysis[] | null {
  try {
    return JSON.parse(text) as ProspectAnalysis[];
  } catch {
    const match = text.match(/\[[\s\S]*\]/);
    if (!match) return null;
    try {
      return JSON.parse(match[0]) as ProspectAnalysis[];
    } catch {
      return null;
    }
  }
}

function polish(analysis: ProspectAnalysis): ProspectAnalysis {
  const clean = (draft: string) =>
    draft
      .replace(/hi\s+\{?[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\}?[,]?/gi, "Hi {{first_name}},")
      .replace(/\{first_name\}/g, "{{first_name}}")
      .replace(/\{business_name\}/g, "{{business_name}}")
      .replace(/\{\{\{first_name\}\}\}/g, "{{first_name}}")
      .replace(/\{\{\{business_name\}\}\}/g, "{{business_name}}");

  return {
    ...analysis,
    score: Math.max(0, Math.min(100, Number(analysis.score) || 0)),
    status: analysis.status || "new",
    emailDraft: clean(analysis.emailDraft),
    dmDraft: clean(analysis.dmDraft),
    followUpDraft: clean(analysis.followUpDraft),
  };
}

function merge(prospects: ProspectInput[], analyses: ProspectAnalysis[] | null): ProspectAnalysis[] {
  const fallback = prospects.map(buildFallbackProspectAnalysis);
  if (!analyses?.length) return fallback;
  return fallback.map((base, index) =>
    polish({
      ...base,
      ...(analyses[index] ?? {}),
      businessName: analyses[index]?.businessName || base.businessName,
      website: analyses[index]?.website || base.website,
      email: analyses[index]?.email || base.email,
      phone: analyses[index]?.phone || base.phone,
      status: "new",
    })
  );
}

export async function POST(req: NextRequest) {
  if (!isValidOrigin(req)) return NextResponse.json({ message: "Forbidden" }, { status: 403 });
  if (!limiter.check(getClientIp(req))) return NextResponse.json({ message: "Too many requests." }, { status: 429 });

  try {
    const body = await req.json();
    const rawLeads = truncate(body.rawLeads, 8_000);
    const prospects = parseProspects(rawLeads);
    if (!prospects.length) return NextResponse.json({ message: "Paste at least one lead." }, { status: 400 });

    const websiteResearch = await Promise.all(
      prospects.map(async (prospect) => ({
        businessName: prospect.businessName,
        website: prospect.website,
        text: await fetchWebsiteSummary(prospect.website),
      }))
    );

    if (!process.env.GROQ_API_KEY) return NextResponse.json({ prospects: prospects.map(buildFallbackProspectAnalysis), source: "fallback" });

    const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });
    const completion = await groq.chat.completions.create({
      model: "llama-3.3-70b-versatile",
      temperature: 0.25,
      max_tokens: 4_000,
      messages: [
        {
          role: "system",
          content: `You are Summit Intelligent Systems' semi-autonomous marketing operator. Score and prepare outreach for each prospect. Return JSON only as an array. Never greet an email address; use {{first_name}} when owner name is unknown. Do not invent contact info. Do not promise guaranteed rankings, revenue, or customers.`,
        },
        {
          role: "user",
          content: `Summit context:\n${summitMarketingContext}\n\nProspects:\n${JSON.stringify(prospects, null, 2)}\n\nWebsite research:\n${JSON.stringify(websiteResearch, null, 2)}`,
        },
      ],
    });

    return NextResponse.json({ prospects: merge(prospects, extractJson(completion.choices[0]?.message?.content ?? "")), source: "model" });
  } catch {
    return NextResponse.json({ message: "Prospect analysis failed." }, { status: 500 });
  }
}
