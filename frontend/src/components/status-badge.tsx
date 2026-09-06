import { cn } from "@/lib/utils";
import type { CaseStatus } from "@/lib/api";

/**
 * Fixed status colour semantics used everywhere in Reflo:
 * teal = resolved/recovered · coral = stopped/blocked · amber = pending/escalated
 * gray = neutral/structural. These meanings are never used decoratively, and
 * every badge always renders a text label so colour is never the only signal.
 */
const STATUS_TONE: Record<string, "resolved" | "stopped" | "pending" | "neutral"> = {
  DETECTED: "neutral",
  CLASSIFIED: "neutral",
  DECIDED: "neutral",
  GATED: "pending",
  EXECUTING: "pending",
  RESOLVED: "resolved",
  STOPPED: "stopped",
  ESCALATED: "pending",
};

const TONE_CLASS = {
  resolved: "bg-resolved-soft text-resolved border-resolved/25",
  stopped: "bg-stopped-soft text-stopped border-stopped/25",
  pending: "bg-pending-soft text-pending border-pending/30",
  neutral: "bg-neutral-status-soft text-neutral-status border-neutral-status/20",
} as const;

export type Tone = keyof typeof TONE_CLASS;

export function statusTone(status: string): Tone {
  return STATUS_TONE[status] ?? "neutral";
}

export function Pill({
  tone,
  children,
  className,
}: {
  tone: Tone;
  children: React.ReactNode;
  className?: string | undefined;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-[22px] shrink-0 items-center gap-1.5 rounded-full border px-2 text-[10.5px] leading-none font-medium tracking-[0.06em] whitespace-nowrap uppercase",
        TONE_CLASS[tone],
        className,
      )}
    >
      <span className="size-1.5 rounded-full bg-current" aria-hidden />
      {children}
    </span>
  );
}

export function StatusBadge({ status, className }: { status: CaseStatus | string; className?: string }) {
  return (
    <Pill tone={statusTone(status)} className={className}>
      {String(status).toLowerCase().replace(/_/g, " ")}
    </Pill>
  );
}

/** Gate outcome shares the same four-colour vocabulary as case status. */
export function GateBadge({ result }: { result: string | null }) {
  if (!result) return <span className="text-xs text-muted-foreground">not gated yet</span>;
  const v = result.toLowerCase();
  const tone: Tone = v.includes("block") || v.includes("fail") || v.includes("stop")
    ? "stopped"
    : v.includes("pass") || v.includes("allow") || v.includes("ok")
      ? "resolved"
      : "pending";
  return <Pill tone={tone}>{v.replace(/_/g, " ")}</Pill>;
}
