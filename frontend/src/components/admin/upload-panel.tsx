"use client";

import { useId, useState, type FormEvent } from "react";
import { Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { uploadDocument } from "@/lib/api";
import type { UploadResponse } from "@/lib/types";

const MAX_BYTES = 50 * 1024 * 1024;
const ACCEPT = ".pdf,.md,text/markdown,application/pdf,text/x-markdown";

interface UploadPanelProps {
  idToken: string | null;
  onUploaded: (result: UploadResponse) => void;
  onError: (message: string) => void;
}

export function UploadPanel({ idToken, onUploaded, onError }: UploadPanelProps) {
  const fileId = useId();
  const titleId = useId();
  const collectionId = useId();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [collection, setCollection] = useState("");
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<UploadResponse | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file || busy) return;
    if (file.size > MAX_BYTES) {
      onError("File too large (max 50 MB)");
      return;
    }
    setBusy(true);
    try {
      const result = await uploadDocument(
        {
          file,
          title: title || undefined,
          collection: collection || undefined,
        },
        idToken,
      );
      setLast(result);
      onUploaded(result);
      setFile(null);
      setTitle("");
      setCollection("");
      // reset file input by remounting via form reset of file field
      const input = document.getElementById(fileId) as HTMLInputElement | null;
      if (input) input.value = "";
    } catch (err) {
      onError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="rounded-xl border border-border bg-card p-4 shadow-sm sm:p-5"
      aria-labelledby="upload-heading"
    >
      <h2
        id="upload-heading"
        className="mb-3 flex items-center gap-2 text-base font-semibold"
      >
        <Upload className="h-4 w-4 text-primary" aria-hidden />
        Upload document
      </h2>
      <p className="mb-4 text-xs text-muted-foreground">
        PDF or Markdown only · max 50&nbsp;MB · requires content_admin or admin
      </p>
      <form onSubmit={onSubmit} className="space-y-3">
        <div>
          <label htmlFor={fileId} className="mb-1 block text-sm font-medium">
            File
          </label>
          <input
            id={fileId}
            type="file"
            accept={ACCEPT}
            required
            disabled={busy}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-primary-foreground"
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor={titleId} className="mb-1 block text-sm font-medium">
              Title <span className="font-normal text-muted-foreground">(optional)</span>
            </label>
            <input
              id={titleId}
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={busy}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
          <div>
            <label
              htmlFor={collectionId}
              className="mb-1 block text-sm font-medium"
            >
              Collection{" "}
              <span className="font-normal text-muted-foreground">(optional)</span>
            </label>
            <input
              id={collectionId}
              type="text"
              value={collection}
              onChange={(e) => setCollection(e.target.value)}
              disabled={busy}
              placeholder="e.g. policies"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
        </div>
        <Button type="submit" disabled={busy || !file} aria-busy={busy}>
          {busy ? "Uploading…" : "Upload"}
        </Button>
      </form>

      {last && (
        <div
          className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-950"
          role="status"
        >
          <p className="font-medium">Upload complete</p>
          <ul className="mt-1 space-y-0.5 font-mono text-xs">
            <li>document_id: {last.document_id}</li>
            <li>version_id: {last.version_id}</li>
            <li>status: {last.status}</li>
            <li className="break-all">gcs_uri: {last.gcs_uri}</li>
            {last.chunk_count != null && <li>chunks: {last.chunk_count}</li>}
            {last.embeddings_status && (
              <li>embeddings: {last.embeddings_status}</li>
            )}
          </ul>
        </div>
      )}
    </section>
  );
}
