import { AlertTriangle, RefreshCw, ScrollText } from "lucide-react";

import { GhostButton } from "@/components/app-shell";
import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-secondary", className)} aria-hidden />;
}

export function TableSkeleton({ rows = 6, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="surface overflow-hidden" role="status" aria-label="Loading">
      <div className="flex gap-4 border-b border-border bg-sidebar/60 px-4 py-2.5">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-2.5 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 border-b border-border px-4 py-3.5 last:border-b-0">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-3 flex-1" />
          ))}
        </div>
      ))}
      <span className="sr-only">Loading data…</span>
    </div>
  );
}

export function CardsSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-4" role="status" aria-label="Loading">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="surface space-y-3 p-5">
          <Skeleton className="h-2.5 w-40" />
          <Skeleton className="h-7 w-64" />
          <Skeleton className="h-3 w-full max-w-lg" />
        </div>
      ))}
      <span className="sr-only">Loading data…</span>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon: Icon = ScrollText,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="surface border-dashed px-6 py-14 text-center">
      <span className="mx-auto grid size-10 place-items-center rounded-lg border border-border bg-sidebar">
        <Icon className="size-4 text-muted-foreground" />
      </span>
      <h3 className="mt-4 text-sm font-semibold">{title}</h3>
      <p className="mx-auto mt-1.5 max-w-md text-sm leading-relaxed text-muted-foreground">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  title = "Could not load this data",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div role="alert" className="rounded-lg border border-stopped/25 bg-stopped-soft px-6 py-12 text-center">
      <span className="mx-auto grid size-10 place-items-center rounded-lg border border-stopped/25 bg-card">
        <AlertTriangle className="size-4 text-stopped" aria-hidden />
      </span>
      <h3 className="mt-4 text-sm font-semibold text-stopped">{title}</h3>
      <p className="mx-auto mt-1.5 max-w-md code-text text-muted-foreground">{message}</p>
      {onRetry ? (
        <GhostButton onClick={onRetry} className="mt-5">
          <RefreshCw className="size-3.5" /> Try again
        </GhostButton>
      ) : null}
    </div>
  );
}
