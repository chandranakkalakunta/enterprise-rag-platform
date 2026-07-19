/** Public runtime config (NEXT_PUBLIC_*). */

export function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  return raw.replace(/\/$/, "");
}

export function getGoogleClientId(): string {
  return process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";
}

export function getHealthPollMs(): number {
  const raw = process.env.NEXT_PUBLIC_HEALTH_POLL_MS;
  const n = raw ? Number(raw) : 60_000;
  return Number.isFinite(n) && n >= 5_000 ? n : 60_000;
}
