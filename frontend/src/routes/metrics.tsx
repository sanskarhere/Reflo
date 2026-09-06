import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { BarChart3, Loader2, Play, ShieldCheck, TrendingUp } from "lucide-react";

import { AppShell, GhostButton, PageHeader, PrimaryButton, SectionLabel } from "@/components/app-shell";
import { CardsSkeleton, EmptyState, ErrorState } from "@/components/states";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  batchesQueryOptions,
  batchMetricsQueryOptions,
  getStoredAdminSecret,
  runBatch,
  setStoredAdminSecret,
} from "@/lib/api";
import { paise, relativeTime } from "@/lib/format";

export const Route = createFileRoute("/metrics")({
  validateSearch: (search: Record<string, unknown>) => ({
    batch_id: typeof search['batch_id'] === "string" ? (search['batch_id'] as string) : "",
  }),
  head: () => ({
    meta: [
      { title: "Batch Metrics — Reflo" },
      {
        name: "description",
        content:
          "Recovered value, agent recovery rate versus a naive immediate-retry baseline and guardrail blocks for a Reflo recovery batch.",
      },
      { property: "og:title", content: "Batch Metrics — Reflo" },
      {
        property: "og:description",
        content:
          "Recovered value, recovery rate vs. naive retry baseline, and guardrail blocks for a recovery batch.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: MetricsPage,
  errorComponent: ({ error }) => <div role="alert">{error.message}</div>,
  notFoundComponent: () => <div>No batch data.</div>,
});

function Card({
  title,
  children,
  note,
  icon: Icon,
}: {
  title: string;
  children: React.ReactNode;
  note?: string;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <section className="surface flex flex-col p-5">
      <div className="flex items-center justify-between gap-3">
        <SectionLabel>{title}</SectionLabel>
        {Icon ? (
          <span className="grid size-7 place-items-center rounded-md border border-border bg-sidebar">
            <Icon className="size-3.5 text-muted-foreground" aria-hidden />
          </span>
        ) : null}
      </div>
      <div className="mt-4 flex-1">{children}</div>
      {note ? <p className="mt-4 text-xs leading-relaxed text-muted-foreground">{note}</p> : null}
    </section>
  );
}

/**
 * Admin-gated control that triggers POST /admin/run-batch. The secret is
 * entered once per browser session (kept in sessionStorage, never in the
 * bundle) — proportionate friction for an action that fires real Razorpay
 * test-mode calls and writes to the DB, without building a full auth system
 * for a v1 hackathon build.
 */
function RunBatchPanel({ onBatchCreated }: { onBatchCreated: (batchId: string) => void }) {
  const [secret, setSecret] = useState(getStoredAdminSecret);
  const [n, setN] = useState(50);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => runBatch(n, secret),
    onSuccess: (data) => {
      setStoredAdminSecret(secret);
      void queryClient.invalidateQueries({ queryKey: ["reflo", "batches"] });
      onBatchCreated(data.batch_id);
    },
  });

  return (
    <form
      className="flex flex-wrap items-end gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        mutation.reset();
        mutation.mutate();
      }}
    >
      <div className="flex flex-col gap-1">
        <label htmlFor="admin-secret" className="section-label">Admin secret</label>
        <input
          id="admin-secret"
          type="password"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          placeholder="ADMIN_SECRET"
          autoComplete="off"
          className="code-text h-8 w-40 rounded-md border border-border bg-background px-2.5 transition-colors placeholder:text-muted-foreground/60 hover:border-ring/60 focus:border-ring focus:outline-none"
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="batch-n" className="section-label">Batch size</label>
        <input
          id="batch-n"
          type="number"
          min={1}
          max={500}
          value={n}
          onChange={(e) => setN(Number(e.target.value) || 1)}
          className="code-text h-8 w-20 rounded-md border border-border bg-background px-2.5 transition-colors hover:border-ring/60 focus:border-ring focus:outline-none"
        />
      </div>
      <PrimaryButton type="submit" disabled={mutation.isPending} className="h-8">
        {mutation.isPending ? <Loader2 className="size-3.5 animate-spin" /> : <Play className="size-3.5" />}
        Run batch
      </PrimaryButton>
      {mutation.isError ? (
        <span className="meta text-stopped">{(mutation.error as Error).message}</span>
      ) : null}
    </form>
  );
}

function BatchPicker({ value, onChange }: { value: string; onChange: (batchId: string) => void }) {
  const query = useQuery(batchesQueryOptions);
  const batches = query.data ?? [];

  if (query.isPending || batches.length === 0) return null;

  return (
    <Select {...(value ? { value } : {})} onValueChange={onChange}>
      <SelectTrigger
        aria-label="Recent batches"
        className="h-8 w-auto min-w-[220px] gap-2 rounded-md border-border bg-card px-2.5 text-xs shadow-none hover:bg-secondary/60 focus:ring-2 focus:ring-ring focus:ring-offset-1"
      >
        <SelectValue placeholder="Recent batches" />
      </SelectTrigger>
      <SelectContent className="rounded-md border-border shadow-none">
        {batches.map((b) => (
          <SelectItem key={b.batch_id} value={b.batch_id} className="text-xs">
            <span className="code-text">{b.batch_id.slice(0, 8)}</span> · {b.batch_size} cases ·{" "}
            {b.created_at ? relativeTime(b.created_at) : "—"}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function MetricsPage() {
  const { batch_id: batchId } = Route.useSearch();
  const navigate = useNavigate({ from: "/metrics" });
  const [draft, setDraft] = useState(batchId);
  const [showRunPanel, setShowRunPanel] = useState(false);

  const query = useQuery(batchMetricsQueryOptions(batchId));
  const batch = query.data;
  const pct = (n: number) => `${Math.round((n ?? 0) * 100)}%`;

  const loadBatch = (id: string) => {
    setDraft(id);
    void navigate({ search: { batch_id: id } });
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Performance"
        title="Batch Metrics"
        description="Results for a single recovery batch, measured against a naive “retry immediately” policy run on the same cases."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <BatchPicker value={batchId} onChange={loadBatch} />
            <form
              className="flex items-center gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                void navigate({ search: { batch_id: draft.trim() } });
              }}
            >
              <label htmlFor="batch-id" className="section-label">
                Batch
              </label>
              <input
                id="batch-id"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="paste a batch id"
                className="code-text h-8 w-40 rounded-md border border-border bg-background px-2.5 transition-colors placeholder:text-muted-foreground/60 hover:border-ring/60 focus:border-ring focus:outline-none"
              />
              <PrimaryButton type="submit">Load</PrimaryButton>
            </form>
            <GhostButton onClick={() => setShowRunPanel((v) => !v)} className="h-8">
              {showRunPanel ? "Hide" : "Run new batch"}
            </GhostButton>
          </div>
        }
      />

      {showRunPanel ? (
        <div className="border-b border-border bg-sidebar/40 px-6 py-4 md:px-10">
          <RunBatchPanel onBatchCreated={loadBatch} />
        </div>
      ) : null}

      <div className="space-y-4 px-6 py-6 md:px-10">
        {!batchId ? (
          <EmptyState
            icon={BarChart3}
            title="Pick a batch to audit"
            description="Every batch Reflo runs is scored against the same naive-retry baseline on identical cases, so the lift is real, not cherry-picked. Pick a recent batch above, paste an id, or run a new one."
          />
        ) : query.isPending ? (
          <CardsSkeleton count={3} />
        ) : query.isError ? (
          <ErrorState
            title="Could not load batch metrics"
            message={(query.error as Error).message}
            onRetry={() => void query.refetch()}
          />
        ) : !batch ? (
          <EmptyState
            icon={BarChart3}
            title="No results for this batch"
            description={`Batch ${batchId} has no recorded metrics. Results are written once a batch finishes and every case in it has reached a terminal state.`}
          />
        ) : (
          <>
            <section className="surface overflow-hidden p-6 md:p-8">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <SectionLabel>Total recovered</SectionLabel>
                <span className="code-text text-muted-foreground">{batch.batch_id}</span>
              </div>
              <p className="mt-4 text-7xl leading-none font-bold tracking-[-0.04em] text-resolved tabular md:text-[104px]">
                {paise(batch.recovered_amount_paise)}
              </p>
              <dl className="mt-6 grid grid-cols-2 gap-4 border-t border-border pt-5 sm:grid-cols-4">
                {[
                  ["Batch size", `${batch.batch_size}`],
                  ["Recovery rate", pct(batch.recovery_rate)],
                  ["Baseline rate", pct(batch.baseline_recovery_rate)],
                  ["Blocked by guardrails", `${batch.guardrail_blocked_count}`],
                ].map(([k, v]) => (
                  <div key={k}>
                    <dt className="section-label">{k}</dt>
                    <dd className="mt-1.5 text-lg font-semibold tabular">{v}</dd>
                  </div>
                ))}
              </dl>
            </section>

            <div className="grid gap-4 lg:grid-cols-2">
              <Card
                title="Recovery rate vs. naive retry baseline"
                icon={TrendingUp}
                note="Baseline replays the same batch with an immediate retry on every failure — no classification and no guardrails."
              >
                <div className="space-y-4">
                  {[
                    { label: "Reflo agent", value: batch.recovery_rate, bar: "bg-resolved", text: "text-resolved" },
                    {
                      label: "Naive immediate retry",
                      value: batch.baseline_recovery_rate,
                      bar: "bg-neutral-status/35",
                      text: "text-muted-foreground",
                    },
                  ].map((row) => (
                    <div key={row.label}>
                      <div className="mb-2 flex items-baseline justify-between">
                        <span className="text-[13px] font-medium">{row.label}</span>
                        <span className={`text-2xl font-semibold tabular ${row.text}`}>{pct(row.value)}</span>
                      </div>
                      <div className="h-7 w-full overflow-hidden rounded-md border border-border bg-secondary p-0.5">
                        <div
                          className={`h-full rounded-sm ${row.bar}`}
                          style={{ width: `${Math.min(100, (row.value ?? 0) * 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                  <p className="text-sm text-muted-foreground">
                    <span className="font-semibold text-foreground tabular">
                      +{Math.round((batch.recovery_rate - batch.baseline_recovery_rate) * 100)} pts
                    </span>{" "}
                    over baseline on identical cases.
                  </p>
                </div>
              </Card>

              <Card
                title="Guardrail blocks"
                icon={ShieldCheck}
                note="A block means the agent proposed an action and policy prevented it. These count as successful enforcement, not agent failures."
              >
                <div className="flex items-baseline gap-3">
                  <span className="text-5xl font-bold tracking-tight text-stopped tabular">
                    {batch.guardrail_blocked_count}
                  </span>
                  <span className="text-sm text-muted-foreground">actions stopped before execution</span>
                </div>
                <div className="mt-5 h-7 w-full overflow-hidden rounded-md border border-border bg-secondary p-0.5">
                  <div
                    className="h-full rounded-sm bg-stopped"
                    style={{
                      width: `${Math.min(100, (batch.guardrail_blocked_count / Math.max(1, batch.batch_size)) * 100)}%`,
                    }}
                  />
                </div>
                <p className="meta mt-2">
                  {Math.round((batch.guardrail_blocked_count / Math.max(1, batch.batch_size)) * 100)}% of the
                  batch
                </p>
              </Card>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
