import { NextRequest, NextResponse } from "next/server";
import { exchangeCodeForToken } from "@/lib/gmail";

export async function GET(req: NextRequest) {
  const code = req.nextUrl.searchParams.get("code");
  const error = req.nextUrl.searchParams.get("error");

  if (error) {
    return NextResponse.redirect(new URL(`/?gmail=error&reason=${encodeURIComponent(error)}`, req.url));
  }

  if (!code) {
    return NextResponse.redirect(new URL("/?gmail=missing_code", req.url));
  }

  try {
    await exchangeCodeForToken(code);
    return NextResponse.redirect(new URL("/?gmail=connected", req.url));
  } catch {
    return NextResponse.redirect(new URL("/?gmail=error", req.url));
  }
}
