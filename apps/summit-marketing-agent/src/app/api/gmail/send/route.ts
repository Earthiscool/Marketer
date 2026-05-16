import { NextRequest, NextResponse } from "next/server";
import { getClientIp, isValidOrigin, RateLimiter, truncate } from "@/lib/api-security";
import { sendGmailMessage } from "@/lib/gmail";

const limiter = new RateLimiter(20, 60_000);

function isEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export async function POST(req: NextRequest) {
  if (!isValidOrigin(req)) return NextResponse.json({ message: "Forbidden" }, { status: 403 });
  if (!limiter.check(getClientIp(req))) return NextResponse.json({ message: "Too many requests." }, { status: 429 });

  try {
    const body = await req.json();
    const to = truncate(body.to, 254).trim();
    const subject = truncate(body.subject, 300).trim();
    const emailBody = truncate(body.body, 8_000).trim();
    const approved = body.approved === true;

    if (!approved) return NextResponse.json({ message: "Approval required before sending." }, { status: 400 });
    if (!isEmail(to)) return NextResponse.json({ message: "Valid recipient email is required." }, { status: 400 });
    if (!subject || !emailBody) return NextResponse.json({ message: "Subject and body are required." }, { status: 400 });

    const result = await sendGmailMessage({
      to,
      subject,
      body: emailBody,
      fromName: "Summit Intelligent Systems",
    });

    return NextResponse.json({ success: true, id: result.id });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Email send failed.";
    return NextResponse.json({ message }, { status: 500 });
  }
}
