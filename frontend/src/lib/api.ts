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
import type {
  AnswerRequest,
  AnswerResponse,
  DocumentDetailResponse,
  DocumentListResponse,
  HealthResponse,
  MeResponse,
  UploadResponse,
  VersionLifecycleResponse,
} from "@/lib/types";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail || `Request failed (${status})`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

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

/**
 * Grounded answer (Phase 3.4 API / Phase 5.2 UI).
 * Requires Google ID token (viewer+).
 */
export async function postAnswer(
  body: AnswerRequest,
  idToken?: string | null,
): Promise<AnswerResponse> {
  const token = idToken ?? getStoredIdToken();
  if (!token) {
    throw new ApiError(401, "Not signed in — please sign in again");
  }

  const res = await apiFetch(
    "/api/v1/query/answer",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: body.query,
        ...(body.top_k != null ? { top_k: body.top_k } : {}),
        ...(body.collection ? { collection: body.collection } : {}),
      }),
      cache: "no-store",
    },
    token,
  );

  if (!res.ok) {
    const detail = await safeDetail(res);
    if (res.status === 401) {
      throw new ApiError(
        401,
        detail || "Session expired or invalid — please sign in again",
      );
    }
    if (res.status === 403) {
      throw new ApiError(403, detail || "Access denied for this account");
    }
    if (res.status === 503) {
      throw new ApiError(
        503,
        detail || "Answer service temporarily unavailable",
      );
    }
    throw new ApiError(res.status, detail || `Answer failed (${res.status})`);
  }

  return res.json() as Promise<AnswerResponse>;
}

function requireToken(idToken?: string | null): string {
  const token = idToken ?? getStoredIdToken();
  if (!token) {
    throw new ApiError(401, "Not signed in — please sign in again");
  }
  return token;
}

async function raiseIfNotOk(res: Response, fallback: string): Promise<never> {
  const detail = await safeDetail(res);
  if (res.status === 401) {
    throw new ApiError(
      401,
      detail || "Session expired or invalid — please sign in again",
    );
  }
  if (res.status === 403) {
    throw new ApiError(403, detail || "Access denied for this account");
  }
  throw new ApiError(res.status, detail || fallback);
}

/** Admin: list documents (content_admin | admin). */
export async function listDocuments(
  idToken?: string | null,
  limit = 50,
): Promise<DocumentListResponse> {
  const token = requireToken(idToken);
  const res = await apiFetch(
    `/api/v1/documents?limit=${limit}`,
    { method: "GET", cache: "no-store" },
    token,
  );
  if (!res.ok) await raiseIfNotOk(res, `List documents failed (${res.status})`);
  return res.json() as Promise<DocumentListResponse>;
}

/** Admin: get document + versions. */
export async function getDocument(
  documentId: string,
  idToken?: string | null,
): Promise<DocumentDetailResponse> {
  const token = requireToken(idToken);
  const res = await apiFetch(
    `/api/v1/documents/${encodeURIComponent(documentId)}`,
    { method: "GET", cache: "no-store" },
    token,
  );
  if (!res.ok) await raiseIfNotOk(res, `Get document failed (${res.status})`);
  return res.json() as Promise<DocumentDetailResponse>;
}

/** Admin: multipart upload (PDF/Markdown ≤50MB). */
export async function uploadDocument(
  form: {
    file: File;
    title?: string;
    collection?: string;
  },
  idToken?: string | null,
): Promise<UploadResponse> {
  const token = requireToken(idToken);
  const body = new FormData();
  body.append("file", form.file);
  if (form.title?.trim()) body.append("title", form.title.trim());
  if (form.collection?.trim()) body.append("collection", form.collection.trim());

  const res = await apiFetch(
    "/api/v1/documents/upload",
    { method: "POST", body, cache: "no-store" },
    token,
  );
  if (!res.ok) await raiseIfNotOk(res, `Upload failed (${res.status})`);
  return res.json() as Promise<UploadResponse>;
}

/** Admin: publish ready version. */
export async function publishVersion(
  documentId: string,
  versionId: string,
  idToken?: string | null,
): Promise<VersionLifecycleResponse> {
  const token = requireToken(idToken);
  const res = await apiFetch(
    `/api/v1/documents/${encodeURIComponent(documentId)}/versions/${encodeURIComponent(versionId)}/publish`,
    { method: "POST", cache: "no-store" },
    token,
  );
  if (!res.ok) await raiseIfNotOk(res, `Publish failed (${res.status})`);
  return res.json() as Promise<VersionLifecycleResponse>;
}

/** Admin: retire ready or published version. */
export async function retireVersion(
  documentId: string,
  versionId: string,
  idToken?: string | null,
): Promise<VersionLifecycleResponse> {
  const token = requireToken(idToken);
  const res = await apiFetch(
    `/api/v1/documents/${encodeURIComponent(documentId)}/versions/${encodeURIComponent(versionId)}/retire`,
    { method: "POST", cache: "no-store" },
    token,
  );
  if (!res.ok) await raiseIfNotOk(res, `Retire failed (${res.status})`);
  return res.json() as Promise<VersionLifecycleResponse>;
}

async function safeDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((d) =>
          typeof d === "object" && d && "msg" in d
            ? String((d as { msg: string }).msg)
            : JSON.stringify(d),
        )
        .join("; ");
    }
    return "";
  } catch {
    return "";
  }
}
