import { NextRequest, NextResponse } from "next/server";
import Groq from "groq-sdk";
import { getClientIp, isValidOrigin, RateLimiter, truncate } from "@/lib/api-security";
import {
  buildFallbackMarketingPlan,
  MarketingAgentInput,
  MarketingAgentOutput,
  summitMarketingContext,
} from "@/lib/marketing-agent";

const limiter = new RateLimiter(8, 60_000);

function normalizeInput(body: Record<string, unknown>): MarketingAgentInput {
  return {
    objective: truncate(body.objective, 1_500).trim(),
    market: truncate(body.market, 1_500).trim(),
    offer: truncate(body.offer, 1_500).trim(),
    location: truncate(body.location, 1_500).trim(),
    audience: truncate(body.audience, 1_500).trim(),
    constraints: truncate(body.constraints, 1_500).trim(),
  };
}

function extractJson(text: string): MarketingAgentOutput | null {
  try {
    return JSON.parse(text) as MarketingAgentOutput;
  } catch {
    const match = text.match(/\{[\s\S]*\}/);
    if (!match) return null;
    try {
      return JSON.parse(match[0]) as MarketingAgentOutput;
    } catch {
      return null;
    }
  }
}

export async function POST(req: NextRequest) {
  if (!isValidOrigin(req)) return NextResponse.json({ message: "Forbidden" }, { status: 403 });
  if (!limiter.check(getClientIp(req))) return NextResponse.json({ message: "Too many requests." }, { status: 429 });

  try {
    const body = await req.json();
    const input = normalizeInput(body ?? {});
    const fallback = buildFallbackMarketingPlan(input);

    if (!process.env.GROQ_API_KEY) return NextResponse.json({ plan: fallback, source: "fallback" });

    const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });
    const completion = await groq.chat.completions.create({
      model: "llama-3.3-70b-versatile",
      temperature: 0.35,
      max_tokens: 3_500,
      messages: [
        {
          role: "system",
          content: `You are Summit Intelligent Systems' senior growth strategist. Return valid JSON only matching this shape:
{
  "positioning": { "headline": string, "angle": string, "proof": string[] },
  "customerTargets": [{ "segment": string, "pain": string, "trigger": string, "whereToFind": string[], "pitch": string }],
  "campaignPlan": [{ "channel": string, "action": string, "cadence": string, "successMetric": string }],
  "outreach": { "coldEmail": string, "dm": string, "callScript": string, "followUp": string },
  "content": { "googleBusinessPosts": string[], "linkedinPosts": string[], "blogIdeas": string[], "landingPageSections": string[] },
  "weeklyExecution": [{ "day": string, "priority": string, "tasks": string[] }],
  "leadScoring": [{ "signal": string, "score": number, "reason": string }],
  "cautions": string[]
}
Do not promise guaranteed rankings, revenue, or customers. Make the plan executable.`,
        },
        {
          role: "user",
          content: `Summit context:\n${summitMarketingContext}\n\nCampaign input:\n${JSON.stringify(input, null, 2)}`,
        },
      ],
    });

    const plan = extractJson(completion.choices[0]?.message?.content ?? "") ?? fallback;
    return NextResponse.json({ plan, source: plan === fallback ? "fallback" : "model" });
  } catch {
    return NextResponse.json({ plan: buildFallbackMarketingPlan({ objective: "", market: "", offer: "", location: "", audience: "", constraints: "" }), source: "fallback" });
  }
}
