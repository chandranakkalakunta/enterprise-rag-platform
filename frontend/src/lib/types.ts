export type UserRole = "viewer" | "content_admin" | "admin";

export interface MeResponse {
  uid: string;
  email: string;
  name: string;
  picture: string | null;
  role: UserRole;
}

export interface HealthResponse {
  status: string;
  service?: string;
  version: string;
  deployed_at: string;
}

/** POST /api/v1/query/answer request (backend SearchRequest). */
export interface AnswerRequest {
  query: string;
  top_k?: number;
  collection?: string;
}

/** Citation from grounded answer API. */
export interface AnswerCitation {
  document_id: string | null;
  version_id: string | null;
  chunk_index: number | null;
  title: string | null;
  filename: string | null;
  snippet: string;
  score: number;
}

export interface AnswerRetrievalMeta {
  top_k: number;
  hit_count: number;
}

/** POST /api/v1/query/answer response body. */
export interface AnswerResponse {
  query: string;
  answer: string;
  refused: boolean;
  refusal_reason: string | null;
  citations: AnswerCitation[];
  retrieval: AnswerRetrievalMeta;
}

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  /** Present on assistant messages from /answer. */
  refused?: boolean;
  refusalReason?: string | null;
  citations?: AnswerCitation[];
  createdAt: number;
}

export function canAccessAdmin(role: UserRole | null | undefined): boolean {
  return role === "content_admin" || role === "admin";
}
