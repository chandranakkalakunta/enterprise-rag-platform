"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";

import { StatusBadge } from "@/components/admin/status-badge";
import { Button } from "@/components/ui/button";
import {
  getDocument,
  listDocuments,
  publishVersion,
  retireVersion,
} from "@/lib/api";
import type { DocumentDetailResponse, DocumentSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

interface DocumentListProps {
  idToken: string | null;
  refreshKey?: number;
  onError: (message: string) => void;
  onSuccess: (message: string) => void;
}

export function DocumentList({
  idToken,
  refreshKey = 0,
  onError,
  onSuccess,
}: DocumentListProps) {
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DocumentDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [actionKey, setActionKey] = useState<string | null>(null);

  const loadList = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listDocuments(idToken, 50);
      setDocs(res.documents);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, [idToken, onError]);

  useEffect(() => {
    void loadList();
  }, [loadList, refreshKey]);

  async function toggleExpand(documentId: string) {
    if (expandedId === documentId) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    setExpandedId(documentId);
    setDetailLoading(true);
    setDetail(null);
    try {
      const d = await getDocument(documentId, idToken);
      setDetail(d);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to load document");
      setExpandedId(null);
    } finally {
      setDetailLoading(false);
    }
  }

  async function onPublish(documentId: string, versionId: string) {
    if (
      !window.confirm(
        `Publish version ${versionId}? This becomes the active published version.`,
      )
    ) {
      return;
    }
    const key = `${documentId}:${versionId}:publish`;
    setActionKey(key);
    try {
      await publishVersion(documentId, versionId, idToken);
      onSuccess(`Published ${versionId}`);
      const d = await getDocument(documentId, idToken);
      setDetail(d);
      await loadList();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Publish failed");
    } finally {
      setActionKey(null);
    }
  }

  async function onRetire(documentId: string, versionId: string) {
    if (
      !window.confirm(
        `Retire version ${versionId}? It will no longer be used for answers.`,
      )
    ) {
      return;
    }
    const key = `${documentId}:${versionId}:retire`;
    setActionKey(key);
    try {
      await retireVersion(documentId, versionId, idToken);
      onSuccess(`Retired ${versionId}`);
      const d = await getDocument(documentId, idToken);
      setDetail(d);
      await loadList();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Retire failed");
    } finally {
      setActionKey(null);
    }
  }

  return (
    <section
      className="rounded-xl border border-border bg-card p-4 shadow-sm sm:p-5"
      aria-labelledby="docs-heading"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 id="docs-heading" className="text-base font-semibold">
          Documents
        </h2>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => void loadList()}
          disabled={loading}
          aria-label="Refresh document list"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
          Refresh
        </Button>
      </div>

      {loading && docs.length === 0 ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Loading…
        </p>
      ) : docs.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No documents yet. Upload a PDF or Markdown file above.
        </p>
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border">
          {docs.map((doc) => {
            const latest = doc.latest_version;
            const isOpen = expandedId === doc.document_id;
            return (
              <li key={doc.document_id} className="bg-background/50">
                <button
                  type="button"
                  className="flex w-full flex-col gap-1 px-3 py-3 text-left hover:bg-muted/50 sm:flex-row sm:items-center sm:justify-between"
                  onClick={() => void toggleExpand(doc.document_id)}
                  aria-expanded={isOpen}
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">
                      {doc.title || "Untitled"}
                    </p>
                    <p className="truncate font-mono text-xs text-muted-foreground">
                      {doc.document_id}
                      {doc.collection ? ` · ${doc.collection}` : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {latest && <StatusBadge status={latest.status} />}
                    {latest?.filename && (
                      <span className="text-xs text-muted-foreground">
                        {latest.filename}
                      </span>
                    )}
                  </div>
                </button>

                {isOpen && (
                  <div className="border-t border-border bg-muted/30 px-3 py-3">
                    {detailLoading || !detail ? (
                      <p className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Loading versions…
                      </p>
                    ) : (
                      <ul className="space-y-3">
                        {detail.versions.map((v) => {
                          const pubKey = `${doc.document_id}:${v.version_id}:publish`;
                          const retKey = `${doc.document_id}:${v.version_id}:retire`;
                          const canPublish = v.status === "ready";
                          const canRetire =
                            v.status === "ready" || v.status === "published";
                          return (
                            <li
                              key={v.version_id}
                              className="rounded-lg border border-border bg-card p-3 text-sm"
                            >
                              <div className="flex flex-wrap items-start justify-between gap-2">
                                <div className="min-w-0 space-y-1">
                                  <div className="flex flex-wrap items-center gap-2">
                                    <code className="text-xs">{v.version_id}</code>
                                    <StatusBadge status={v.status} />
                                    {detail.active_version_id ===
                                      v.version_id && (
                                      <span className="text-xs font-medium text-emerald-700">
                                        active
                                      </span>
                                    )}
                                  </div>
                                  {v.filename && (
                                    <p className="text-xs text-muted-foreground">
                                      {v.filename}
                                      {v.chunk_count != null
                                        ? ` · ${v.chunk_count} chunks`
                                        : ""}
                                      {v.embeddings_status
                                        ? ` · emb ${v.embeddings_status}`
                                        : ""}
                                    </p>
                                  )}
                                  {v.gcs_uri && (
                                    <p className="break-all font-mono text-[11px] text-muted-foreground">
                                      {v.gcs_uri}
                                    </p>
                                  )}
                                  {v.error_message && (
                                    <p className="text-xs text-red-700">
                                      {v.error_message}
                                    </p>
                                  )}
                                </div>
                                <div className="flex flex-wrap gap-2">
                                  <Button
                                    type="button"
                                    size="sm"
                                    disabled={
                                      !canPublish || actionKey === pubKey
                                    }
                                    onClick={() =>
                                      void onPublish(
                                        doc.document_id,
                                        v.version_id,
                                      )
                                    }
                                    aria-label={`Publish version ${v.version_id}`}
                                  >
                                    {actionKey === pubKey
                                      ? "Publishing…"
                                      : "Publish"}
                                  </Button>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="outline"
                                    disabled={
                                      !canRetire || actionKey === retKey
                                    }
                                    onClick={() =>
                                      void onRetire(
                                        doc.document_id,
                                        v.version_id,
                                      )
                                    }
                                    aria-label={`Retire version ${v.version_id}`}
                                  >
                                    {actionKey === retKey
                                      ? "Retiring…"
                                      : "Retire"}
                                  </Button>
                                </div>
                              </div>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
