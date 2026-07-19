"use client";

import type { VersionStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STYLES: Record<VersionStatus, string> = {
  processing: "bg-slate-100 text-slate-700 border-slate-200",
  ready: "bg-sky-50 text-sky-800 border-sky-200",
  published: "bg-emerald-50 text-emerald-800 border-emerald-200",
  retired: "bg-zinc-100 text-zinc-600 border-zinc-200",
  failed: "bg-red-50 text-red-800 border-red-200",
};

export function StatusBadge({ status }: { status: VersionStatus | string }) {
  const key = status as VersionStatus;
  const style = STYLES[key] ?? "bg-muted text-muted-foreground border-border";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium capitalize",
        style,
      )}
    >
      {status}
    </span>
  );
}
