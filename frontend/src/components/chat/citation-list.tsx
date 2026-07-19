"use client";

import {
  citationDisplayTitle,
  meaningfulCitationField,
} from "@/lib/chat-utils";
import type { AnswerCitation } from "@/lib/types";

interface CitationListProps {
  citations: AnswerCitation[];
}

export function CitationList({ citations }: CitationListProps) {
  if (!citations.length) return null;

  return (
    <div className="mt-3 border-t border-border/80 pt-3">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Sources ({citations.length})
      </h3>
      <ol className="space-y-2">
        {citations.map((c, i) => {
          const heading = citationDisplayTitle(c, i);
          const filename = meaningfulCitationField(c.filename);
          const title = meaningfulCitationField(c.title);
          const showFilenameSub =
            Boolean(filename) && Boolean(title) && filename !== title;

          return (
            <li
              key={`${c.document_id ?? "d"}-${c.chunk_index ?? i}-${i}`}
              className="rounded-md border border-border bg-background/80 px-3 py-2 text-sm"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-medium text-foreground">
                  [{i + 1}] {heading}
                </span>
                {typeof c.score === "number" && (
                  <span className="text-xs tabular-nums text-muted-foreground">
                    score {c.score.toFixed(3)}
                  </span>
                )}
              </div>
              {showFilenameSub && (
                <p className="mt-0.5 text-xs text-muted-foreground">{filename}</p>
              )}
              {c.snippet && (
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                  {c.snippet.length > 280
                    ? `${c.snippet.slice(0, 280)}…`
                    : c.snippet}
                </p>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
