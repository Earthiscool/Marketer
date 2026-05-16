import { mkdir, readFile, writeFile } from "fs/promises";
import path from "path";
import { google } from "googleapis";

const GMAIL_SCOPES = [
  "https://www.googleapis.com/auth/gmail.send",
  "https://www.googleapis.com/auth/gmail.readonly",
];

const TOKEN_PATH = path.join(process.cwd(), "data", "gmail-token.json");

type GmailToken = {
  access_token?: string | null;
  refresh_token?: string | null;
  scope?: string;
  token_type?: string | null;
  expiry_date?: number | null;
};

export function getOAuthClient() {
  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
  const redirectUri = process.env.GOOGLE_REDIRECT_URI || "http://localhost:3000/api/gmail/callback";

  if (!clientId || !clientSecret) {
    throw new Error("Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET.");
  }

  return new google.auth.OAuth2(clientId, clientSecret, redirectUri);
}

export function getGmailAuthUrl() {
  const oauth2Client = getOAuthClient();
  return oauth2Client.generateAuthUrl({
    access_type: "offline",
    prompt: "consent",
    scope: GMAIL_SCOPES,
  });
}

export async function saveGmailToken(token: GmailToken) {
  await mkdir(path.dirname(TOKEN_PATH), { recursive: true });
  await writeFile(TOKEN_PATH, JSON.stringify(token, null, 2), "utf8");
}

export async function loadGmailToken(): Promise<GmailToken | null> {
  try {
    return JSON.parse(await readFile(TOKEN_PATH, "utf8")) as GmailToken;
  } catch {
    return null;
  }
}

export async function exchangeCodeForToken(code: string) {
  const oauth2Client = getOAuthClient();
  const { tokens } = await oauth2Client.getToken(code);
  await saveGmailToken(tokens);
}

export async function getAuthorizedGmailClient() {
  const token = await loadGmailToken();
  if (!token) throw new Error("Gmail is not connected.");

  const oauth2Client = getOAuthClient();
  oauth2Client.setCredentials(token);
  return google.gmail({ version: "v1", auth: oauth2Client });
}

function encodeBase64Url(value: string) {
  return Buffer.from(value)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function header(value: string) {
  return value.replace(/\r?\n/g, " ").trim();
}

export async function sendGmailMessage(input: {
  to: string;
  subject: string;
  body: string;
  fromName?: string;
}) {
  const gmail = await getAuthorizedGmailClient();
  const message = [
    `To: ${header(input.to)}`,
    `Subject: ${header(input.subject)}`,
    input.fromName ? `From: ${header(input.fromName)}` : "",
    "Content-Type: text/plain; charset=utf-8",
    "MIME-Version: 1.0",
    "",
    input.body,
  ].filter(Boolean).join("\r\n");

  const result = await gmail.users.messages.send({
    userId: "me",
    requestBody: {
      raw: encodeBase64Url(message),
    },
  });

  return result.data;
}

export async function getGmailConnectionStatus() {
  const token = await loadGmailToken();
  return {
    connected: Boolean(token?.refresh_token || token?.access_token),
    scopes: token?.scope?.split(" ") ?? [],
  };
}
