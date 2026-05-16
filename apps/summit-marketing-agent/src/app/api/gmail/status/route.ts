import { NextResponse } from "next/server";
import { getGmailConnectionStatus } from "@/lib/gmail";

export async function GET() {
  return NextResponse.json(await getGmailConnectionStatus());
}
