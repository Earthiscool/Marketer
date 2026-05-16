import { NextRequest } from "next/server";

export function isValidOrigin(req: NextRequest): boolean {
  if (process.env.NODE_ENV === "development") return true;

  const origin = req.headers.get("origin");
  const host = req.headers.get("host");
  if (!origin || !host) return false;

  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}

export function getClientIp(req: NextRequest): string {
  const forwarded = req.headers.get("x-forwarded-for");
  if (forwarded) return forwarded.split(",")[0].trim();
  return req.headers.get("x-real-ip") ?? "unknown";
}

type RateLimitEntry = {
  count: number;
  resetAt: number;
};

export class RateLimiter {
  private map = new Map<string, RateLimitEntry>();
  private lastClean = Date.now();

  constructor(
    private readonly limit: number,
    private readonly windowMs: number
  ) {}

  check(key: string): boolean {
    const now = Date.now();

    if (now - this.lastClean > 300_000) {
      for (const [k, entry] of this.map) {
        if (now > entry.resetAt) this.map.delete(k);
      }
      this.lastClean = now;
    }

    const entry = this.map.get(key);
    if (!entry || now > entry.resetAt) {
      this.map.set(key, { count: 1, resetAt: now + this.windowMs });
      return true;
    }
    if (entry.count >= this.limit) return false;
    entry.count++;
    return true;
  }
}

export function truncate(value: unknown, max: number): string {
  if (typeof value !== "string") return "";
  return value.slice(0, max);
}
