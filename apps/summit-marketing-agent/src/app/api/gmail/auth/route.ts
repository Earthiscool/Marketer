import { NextResponse } from "next/server";
import { getGmailAuthUrl } from "@/lib/gmail";

export async function GET() {
  return NextResponse.redirect(getGmailAuthUrl());
}
