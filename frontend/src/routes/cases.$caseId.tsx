import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";

import { AppShell } from "@/components/app-shell";
import { GateBadge, Pill, StatusBadge, statusTone, type Tone } from "@/components/status-badge";
import { CardsSkeleton, EmptyState, ErrorState, Skeleton } from "@/components/states";
import { auditQueryOptions, caseQueryOptions, rootCauseLabel, type Stage } from "@/lib/api";
import { absoluteTime, asText, paise } from "@/lib/format";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/cases/$caseId")({
  head: ({ params }) => ({
    meta: [
      { title: `Case ${params.caseId} — Reflo audit trail` },
      {
        name: "description",
        content: `Full audit trail for recovery case ${params.caseId}: every stage, the input the agent saw, the output it produced and the rule that caused it.`,
      },
      { property: "og:title", content: `Case ${params.caseId} — Reflo audit trail` },
      {
        property: "og:description",
        content: `Every stage of recovery case ${params.caseId}, with the rule or model output behind each decision.`,
      },
      { property: "og:type", content: "article" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: CaseDetail,
  errorComponent: ({ error }) => <div role="alert">{error.message}</div>,
  notFoundComponent: () => (
    <AppShell>
      <div className="px-10 py-16">
        <h1 className="text-lg font-semibold">Case not found</h1>
        <Link to="/recovery" className="mt-3 inline-block text-sm text-muted-foreground underline">
          Back to recovery queue
        </Link>
      </div>
    </AppShell>
  ),
});

const STAGE_ORDER: Stage[] = [
  "DETECTED",
  "CLASSIFIED",
  "DECIDED",
  "GATED",
  "EXECUTING",
  "RESOLVED",
  "STOPPED",
  "ESCALATED",
];

const STAGE_TITLE: Record<string, string> = {
  DETECTED: "Detected",
  CLASSIFIED: "Classified",
  DECIDED: "Decided",
  GATED: "Gated",
  EXECUTING: "Executing",
  RESOLVED: "Resolved",
  STOPPED: "Stopped",
  ESCALATED: "Escalated",
};

const stageTone = (stage: string): Tone =>
  stage === "RESOLVED"
    ? "resolved"
    : stage === "STOPPED"
      ? "stopped"
      : stage === "ESCALATED" || stage === "GATED" || stage === "EXECUTING"
        ? "pending"
        : "neutral";

const NODE: Record<Tone, string> = {
  resolved: "bg-resolved-soft border-resolved text-resolved",
  stopped: "bg-stopped-soft border-stopped text-stopped",
  pending: "bg-pending-soft border-pending text-pending",
  neutral: "bg-card border-neutral-status/40 text-neutral-status",
};

function CodeBlock({ label, value, tone }: { label: string; value: string; tone?: "stopped" }) {
  return (
    <div className="min-w-0">
      <div className="section-label mb-1.5">{label}</div>
      <pre
        className={cn(
          "code-text max-h-64 overflow-auto rounded-md border border-border bg-sidebar px-3 py-2.5 break-words whitespace-pre-wrap text-foreground/90",
          tone === "stopped" && "border-stopped/30 bg-stopped-soft text-stopped",
        )}
      >
        {value}
      </pre>
    </div>
  );
}

function CaseDetail() {
  const { caseId } = Route.useParams();
  const caseQuery = useQuery(caseQueryOptions(caseId));
  const auditQuery = useQuery(auditQueryOptions(caseId));
  const c = caseQuery.data;
  const log = auditQuery.data ?? [];

  const reached = new Set(log.map((e) => e.stage));
  const timeline = STAGE_ORDER.filter((s) => reached.has(s));
  const pending = STAGE_ORDER.slice(0, 5).filter((s) => !reached.has(s));
  const showPending = !["RESOLVED", "STOPPED", "ESCALATED"].some((s) => reached.has(s as Stage));

  return (
    <AppShell>
      <div className="page-header border-b border-border bg-card px-6 py-6 md:px-10">
        <Link
          to="/recovery"
          className="inline-flex items-center gap-1.5 rounded-sm text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" /> Recovery queue
        </Link>

        {caseQuery.isPending ? (
          <div className="mt-4 space-y-3">
            <Skeleton className="h-7 w-64" />
            <Skeleton className="h-4 w-96" />
            <Skeleton className="h-14 w-full max-w-3xl" />
          </div>
        ) : caseQuery.isError ? (
          <div className="mt-4 max-w-2xl">
            <ErrorState
              title="Could not load this case"
              message={(caseQuery.error as Error).message}
              onRetry={() => void caseQuery.refetch()}
            />
          </div>
        ) : !c ? (
          <div className="mt-4 max-w-2xl">
            <EmptyState
              title="No case on record"
              description={`Reflo has no case with id ${caseId}. Every case the agent touches is recorded, so if this id came from a live event the queue will pick it up on its next poll.`}
            />
          </div>
        ) : (
          <>
            <p className="section-label mt-4">Recovery case</p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <h1 className="page-title tabular">{c.customer_id}</h1>
              <StatusBadge status={c.status} />
              <GateBadge result={c.gate_result} />
            </div>
            <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-[13px]">
              {[
                ["Case", c.id, true],
                ["Subscription", c.subscription_id, true],
                ["Amount", paise(c.amount_paise), false],
                ["Root cause", rootCauseLabel(c.root_cause), false],
              ].map(([k, v, mono]) => (
                <div key={String(k)} className="flex items-baseline gap-1.5">
                  <dt className="meta">{k}</dt>
                  <dd className={cn("font-medium", mono ? "code-text text-foreground" : "tabular")}>{v}</dd>
                </div>
              ))}
            </dl>

            <div
              className={cn(
                "mt-5 max-w-3xl rounded-lg border border-border border-l-[3px] bg-background px-4 py-3.5 text-[15px] leading-relaxed",
                statusTone(c.status) === "resolved" && "border-l-resolved",
                statusTone(c.status) === "stopped" && "border-l-stopped",
                statusTone(c.status) === "pending" && "border-l-pending",
                statusTone(c.status) === "neutral" && "border-l-neutral-status/40",
              )}
            >
              <span className="section-label mb-1 block">Why the agent did this</span>
              {c.decision || "No decision has been recorded for this case yet."}
            </div>
          </>
        )}
      </div>

      <div className="px-6 py-6 md:px-10">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="section-label">Audit trail</h2>
          <span className="meta">
            {auditQuery.isPending ? "loading…" : `${log.length} recorded stages · append-only`}
          </span>
        </div>

        {auditQuery.isPending ? (
          <div className="max-w-4xl">
            <CardsSkeleton count={3} />
          </div>
        ) : auditQuery.isError ? (
          <div className="max-w-4xl">
            <ErrorState
              title="Could not load the audit trail"
              message={(auditQuery.error as Error).message}
              onRetry={() => void auditQuery.refetch()}
            />
          </div>
        ) : log.length === 0 ? (
          <div className="max-w-4xl">
            <EmptyState
              title="No stages recorded yet"
              description="Reflo writes an entry the instant a stage completes — the input it saw, the output it produced and the rule that fired. Until the agent acts, there is deliberately nothing here."
            />
          </div>
        ) : (
          <ol className="relative max-w-4xl">
            <div className="absolute top-3 bottom-3 left-[13px] w-px bg-border" aria-hidden />
            {timeline.map((stage, idx) => {
              const entry = log.find((e) => e.stage === stage)!;
              const tone = stageTone(stage);
              const fired = !!entry.rule_fired?.includes("FIRED");
              return (
                <li key={stage} className="relative pb-4 pl-11">
                  <span
                    className={cn(
                      "code-text absolute top-2.5 left-0 grid size-7 place-items-center rounded-md border-2 text-[11px] font-medium",
                      NODE[tone],
                    )}
                    aria-hidden
                  >
                    {String(idx + 1).padStart(2, "0")}
                  </span>
                  <div className="surface overflow-hidden transition-colors hover:border-ring/50">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-sidebar/60 px-4 py-2.5">
                      <div className="flex items-center gap-2.5">
                        <span className="text-sm font-semibold">{STAGE_TITLE[stage] ?? stage}</span>
                        <Pill tone={tone}>{stage.toLowerCase()}</Pill>
                      </div>
                      <span className="code-text text-muted-foreground">{absoluteTime(entry.timestamp)}</span>
                    </div>
                    <div className="grid gap-4 px-4 py-4 sm:grid-cols-2">
                      <CodeBlock label="Input snapshot" value={asText(entry.input)} />
                      <CodeBlock label="Output" value={asText(entry.output)} />
                    </div>
                    <div className="border-t border-border px-4 py-3">
                      <div className="section-label mb-1.5">Rule / model output</div>
                      <code
                        className={cn(
                          "code-text inline-block rounded-sm border px-2 py-1",
                          fired
                            ? "border-stopped/30 bg-stopped-soft text-stopped"
                            : "border-border bg-sidebar text-foreground/80",
                        )}
                      >
                        {entry.rule_fired ?? "— no policy evaluation at this stage"}
                      </code>
                    </div>
                  </div>
                </li>
              );
            })}

            {showPending &&
              pending.map((stage) => (
                <li key={stage} className="relative pb-4 pl-11">
                  <span
                    className="absolute top-2 left-0 size-7 rounded-md border-2 border-dashed border-border bg-background"
                    aria-hidden
                  />
                  <div className="rounded-lg border border-dashed border-border px-4 py-3 text-[13px] text-muted-foreground">
                    {STAGE_TITLE[stage]} <span className="meta">· not yet reached</span>
                  </div>
                </li>
              ))}
          </ol>
        )}
      </div>
    </AppShell>
  );
}
