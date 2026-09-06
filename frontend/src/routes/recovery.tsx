import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronRight, Inbox } from "lucide-react";

import { AppShell, GhostButton, PageHeader } from "@/components/app-shell";
import { GateBadge, StatusBadge } from "@/components/status-badge";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/states";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CASE_STATUSES, ROOT_CAUSES, casesQueryOptions, rootCauseLabel } from "@/lib/api";
import { paise, relativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/recovery")({
  head: () => ({
    meta: [
      { title: "Recovery Queue — Reflo" },
      { name: "description", content: "Reflo's recovery queue: every failed subscription payment, its root cause, the agent's decision and current guarded status." },
      { property: "og:title", content: "Recovery Queue — Reflo" },
      { property: "og:description", content: "Every failed subscription payment, its root cause, the agent's decision and current guarded status." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: QueuePage,
  errorComponent: ({ error }) => <div role="alert">{error.message}</div>,
  notFoundComponent: () => <div>No cases found.</div>,
});

type SortKey = "amount_paise" | "created_at";

function Filter({ value, onChange, label, options }: { value: string; onChange: (v: string) => void; label: string; options: { value: string; label: string }[] }) {
  return (
    <div className="flex items-center gap-2">
      <span className="section-label">{label}</span>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger aria-label={label} className="h-8 w-auto min-w-[150px] gap-2 rounded-md border-border bg-card px-2.5 text-xs shadow-none hover:bg-secondary/60 focus:ring-2 focus:ring-ring focus:ring-offset-1 data-[state=open]:bg-secondary/60"><SelectValue /></SelectTrigger>
        <SelectContent className="rounded-md border-border shadow-none">{options.map((o) => <SelectItem key={o.value} value={o.value} className="text-xs">{o.label}</SelectItem>)}</SelectContent>
      </Select>
    </div>
  );
}

function QueuePage() {
  const [status, setStatus] = useState("all");
  const [cause, setCause] = useState("all");
  const [sortKey, setSortKey] = useState<SortKey>("created_at");
  const [asc, setAsc] = useState(false);
  const navigate = useNavigate();
  const query = useQuery(casesQueryOptions({ status, root_cause: cause, sort_by: sortKey, order: asc ? "asc" : "desc" }));
  const rows = query.data ?? [];
  const toggleSort = (key: SortKey) => {
    if (key === sortKey) setAsc((v) => !v);
    else { setSortKey(key); setAsc(false); }
  };
  const SortHeader = ({ k, children }: { k: SortKey; children: React.ReactNode }) => {
    const active = sortKey === k;
    return <button onClick={() => toggleSort(k)} aria-sort={active ? (asc ? "ascending" : "descending") : "none"} className={cn("inline-flex items-center gap-1 rounded-sm transition-colors hover:text-foreground", active && "text-foreground")}>{children}{active ? (asc ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />) : <ArrowUpDown className="size-3 opacity-40" />}</button>;
  };
  const filtered = status !== "all" || cause !== "all";
  const clearFilters = () => { setStatus("all"); setCause("all"); };
  const th = "section-label px-4 py-2.5 text-left font-medium normal-case tracking-[0.08em] uppercase";

  return (
    <AppShell>
      <PageHeader eyebrow="Operations" title="Recovery Queue" description="Failed subscription payments currently under the agent's care. Each case carries a root cause, a decision and a status that reflects where it sits in the guarded state machine." />
      <div className="px-6 py-6 md:px-10">
        <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card px-3 py-2.5 md:gap-4 md:px-4">
          <Filter label="Status" value={status} onChange={setStatus} options={[{ value: "all", label: "All statuses" }, ...CASE_STATUSES.map((s) => ({ value: s, label: s.charAt(0) + s.slice(1).toLowerCase() }))]} />
          <Filter label="Root cause" value={cause} onChange={setCause} options={[{ value: "all", label: "All causes" }, ...ROOT_CAUSES.map((c) => ({ value: c, label: rootCauseLabel(c) }))]} />
          {filtered ? <GhostButton onClick={clearFilters} className="h-8">Clear</GhostButton> : null}
          <span className="meta ml-auto">{query.isPending ? "loading…" : `${rows.length} ${rows.length === 1 ? "case" : "cases"}`}</span>
        </div>
        {query.isPending ? <TableSkeleton rows={6} cols={7} /> : query.isError ? <ErrorState title="Could not load the recovery queue" message={(query.error as Error).message} onRetry={() => void query.refetch()} /> : rows.length === 0 ? (
          <EmptyState icon={Inbox} title={filtered ? "No cases match these filters" : "Queue is clear — nothing needs recovery"} description={filtered ? "Widen the status or root-cause filter to see the rest of the queue." : "The moment a subscription payment fails, Reflo opens a case here with its root cause, a proposed action and the rule that will gate it — before anything is retried."} {...(filtered ? { action: <GhostButton onClick={clearFilters}>Clear filters</GhostButton> } : {})} />
        ) : (
          <div className="surface overflow-x-auto"><table className="w-full min-w-[960px] text-[13px]"><thead><tr className="border-b border-border bg-sidebar/60"><th className={cn(th, "pl-5")}>Customer</th><th className={th}>Case</th><th className={cn(th, "text-right")}><SortHeader k="amount_paise">Amount</SortHeader></th><th className={th}>Root cause</th><th className={th}>Proposed action</th><th className={cn(th, "w-[1%]")}>Gate</th><th className={cn(th, "w-[1%]")}>Status</th><th className={cn(th, "text-right")}><SortHeader k="created_at">Created</SortHeader></th><th className="w-8" /></tr></thead><tbody>
            {rows.map((c, i) => <tr key={c.id} tabIndex={0} onClick={() => void navigate({ to: "/cases/$caseId", params: { caseId: c.id } })} onKeyDown={(e) => { if (e.key === "Enter") void navigate({ to: "/cases/$caseId", params: { caseId: c.id } }); }} className={cn("group cursor-pointer transition-colors hover:bg-secondary/55 focus-visible:bg-secondary/60", i !== rows.length - 1 && "border-b border-border")}>
              <td className="px-4 py-3 pl-5 font-semibold text-foreground"><Link to="/cases/$caseId" params={{ caseId: c.id }} className="tabular focus-visible:outline-none" onClick={(e) => e.stopPropagation()}>{c.customer_id}</Link></td><td className="px-4 py-3"><span className="code-text text-muted-foreground">{c.id}</span></td><td className="px-4 py-3 text-right font-medium tabular">{paise(c.amount_paise)}</td><td className="px-4 py-3 text-muted-foreground">{rootCauseLabel(c.root_cause)}</td><td className="max-w-[240px] truncate px-4 py-3 text-muted-foreground">{c.decision || "—"}</td><td className="w-[1%] px-4 py-3"><GateBadge result={c.gate_result} /></td><td className="w-[1%] px-4 py-3"><StatusBadge status={c.status} /></td><td className="meta px-4 py-3 text-right">{relativeTime(c.created_at)}</td><td className="pr-3"><ChevronRight className="size-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100" /></td>
            </tr>)}
          </tbody></table></div>
        )}
      </div>
    </AppShell>
  );
}