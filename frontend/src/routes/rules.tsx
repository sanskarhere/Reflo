import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";

import { AppShell, PageHeader } from "@/components/app-shell";
import { Pill, type Tone } from "@/components/status-badge";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/states";
import { rulesQueryOptions } from "@/lib/api";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/rules")({
  head: () => ({
    meta: [
      { title: "Guardrail Rules — Reflo" },
      {
        name: "description",
        content:
          "The explicit, read-only policy set that bounds Reflo's recovery agent: each rule's condition and the action it forces.",
      },
      { property: "og:title", content: "Guardrail Rules — Reflo" },
      {
        property: "og:description",
        content: "The explicit policy set that bounds what Reflo's recovery agent may do.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: RulesPage,
  errorComponent: ({ error }) => <div role="alert">{error.message}</div>,
  notFoundComponent: () => <div>No rules found.</div>,
});

const SEVERITY_TONE = (severity: string): Tone =>
  severity === "hard_stop" ? "stopped" : severity === "escalate" || severity === "throttle" ? "pending" : "neutral";

function RulesPage() {
  const query = useQuery(rulesQueryOptions);
  const rules = query.data ?? [];

  return (
    <AppShell>
      <PageHeader
        title="Guardrail Rules"
        description="These are the complete boundaries of the recovery agent. They are evaluated as code before any action executes — not embedded in a prompt — and every evaluation is written to the case audit trail. This view is read-only."
      />

      <div className="px-6 py-6 md:px-10">
        {!query.isPending && !query.isError && (
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-card px-4 py-3 text-xs text-muted-foreground">
              <span>
                Policy set <span className="code-text text-foreground">reflo-recovery</span>
              </span>
              <span className="inline-flex items-center gap-1.5 font-medium text-resolved">
                <span className="size-1.5 rounded-full bg-current" aria-hidden />
                <span className="tabular">{rules.length} active rules</span>
              </span>
          </div>
        )}

        {query.isPending ? (
          <TableSkeleton rows={5} cols={5} />
        ) : query.isError ? (
          <ErrorState
            title="Could not load the guardrail rules"
            message={(query.error as Error).message}
            onRetry={() => void query.refetch()}
          />
        ) : rules.length === 0 ? (
          <EmptyState
            title="No guardrail rules configured"
            description="The API returned an empty policy set. Without rules, every agent action would be unbounded — add rules on the backend before enabling recovery."
          />
        ) : (
          <div className="surface overflow-x-auto">
            <table className="w-full min-w-[860px] text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs font-medium tracking-wide text-muted-foreground uppercase">
                  <th className="w-20 px-4 py-3">Rule</th>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Condition</th>
                  <th className="px-4 py-3">Forced action</th>
                  <th className="px-4 py-3">Type</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((r, i) => (
                  <tr key={r.id} className={cn(i !== rules.length - 1 && "border-b border-border")}>
                    <td className="px-4 py-4 align-top font-medium tabular">{r.id}</td>
                    <td className="px-4 py-4 align-top font-medium">{r.name}</td>
                    <td className="max-w-[320px] px-4 py-4 align-top text-muted-foreground">
                      {r.condition}
                    </td>
                    <td className="max-w-[320px] px-4 py-4 align-top text-muted-foreground">
                      {r.forced_action}
                    </td>
                    <td className="px-4 py-4 align-top">
                      <Pill tone={SEVERITY_TONE(r.severity)}>
                        {String(r.severity).replace(/_/g, " ")}
                      </Pill>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}
