/**
 * API client helpers.
 *
 * Session model (MVP / ADR-0009–0010):
 * - Google Identity Services returns a Google **ID token** (JWT).
 * - Frontend stores it in memory + sessionStorage and sends
 *   `Authorization: Bearer <id_token>` on protected calls.
 * - Backend verifies the token (audience = OAuth client id), domain gate,
 *   and Firestore role. UI never trusts client-only role flags alone.
 *
 * Not used for MVP: BFF httpOnly cookie session (possible later hardening).
 */

import { getApiBaseUrl } from "@/lib/config";
import type { HealthResponse, MeResponse } from "@/lib/types";

const TOKEN_KEY = "erp_google_id_token";

export function getStoredIdToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setStoredIdToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    sessionStorage.setItem(TOKEN_KEY, token);
  } else {
    sessionStorage.removeItem(TOKEN_KEY);
  }
}

export async function fetchMe(idToken: string): Promise<MeResponse> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/me`, {
    headers: {
      Authorization: `Bearer ${idToken}`,
      Accept: "application/json",
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await safeDetail(res);
    throw new Error(detail || `GET /me failed (${res.status})`);
  }
  return res.json() as Promise<MeResponse>;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${getApiBaseUrl()}/health`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`GET /health failed (${res.status})`);
  }
  return res.json() as Promise<HealthResponse>;
}

export async function apiFetch(
  path: string,
  init: RequestInit = {},
  idToken?: string | null,
): Promise<Response> {
  const token = idToken ?? getStoredIdToken();
  const headers = new Headers(init.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  return fetch(`${getApiBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`, {
    ...init,
    headers,
  });
}

async function safeDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string };
    return typeof body.detail === "string" ? body.detail : "";
  } catch {
    return "";
  }
}
