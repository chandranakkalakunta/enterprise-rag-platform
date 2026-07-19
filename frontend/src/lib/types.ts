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

/** Document version status (backend VersionStatus). */
export type VersionStatus =
  | "processing"
  | "ready"
  | "failed"
  | "published"
  | "retired";

export interface VersionSummary {
  version_id: string;
  status: VersionStatus;
  filename: string | null;
  gcs_uri: string | null;
  content_type: string | null;
  size_bytes: number | null;
  created_at: string | null;
  created_by: string | null;
  chunk_count: number | null;
  embeddings_status: string | null;
  vector_status: string | null;
  error_message: string | null;
  text_preview: string | null;
}

export interface DocumentSummary {
  document_id: string;
  title: string | null;
  collection: string | null;
  active_version_id: string | null;
  latest_version_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  created_by: string | null;
  latest_version: VersionSummary | null;
}

export interface DocumentListResponse {
  documents: DocumentSummary[];
  count: number;
}

export interface DocumentDetailResponse extends DocumentSummary {
  versions: VersionSummary[];
}

export interface UploadResponse {
  document_id: string;
  version_id: string;
  status: VersionStatus;
  gcs_uri: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  title: string | null;
  collection: string | null;
  extracted_char_count: number | null;
  chunk_count: number | null;
  processed_gcs_prefix: string | null;
  text_preview: string | null;
  error_message: string | null;
  embeddings_status: string | null;
  embedding_model_id: string | null;
  embedded_chunk_count: number | null;
  embeddings_gcs_uri: string | null;
  embeddings_error: string | null;
  vector_status: string | null;
}

export interface VersionLifecycleResponse {
  document_id: string;
  version_id: string;
  status: "published" | "retired";
  active_version_id: string | null;
  published_at: string | null;
  published_by: string | null;
  retired_at: string | null;
  retired_by: string | null;
  previous_published_version_id: string | null;
  cleared_active_pointer: boolean;
}
