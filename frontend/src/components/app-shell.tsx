import { Link } from "@tanstack/react-router";
import { Inbox, BarChart3, ShieldCheck, ScrollText, Activity } from "lucide-react";

import { cn } from "@/lib/utils";

const NAV = [
  { to: "/recovery", label: "Recovery Queue", icon: Inbox },
  { to: "/metrics", label: "Batch Metrics", icon: BarChart3 },
  { to: "/rules", label: "Guardrail Rules", icon: ShieldCheck },
] as const;

function Wordmark() {
  return (
    <div className="flex items-center gap-2.5">
      <span
        className="grid size-6 place-items-center rounded-md bg-primary text-primary-foreground"
        aria-hidden
      >
        <span className="size-2 rounded-sm bg-resolved" />
      </span>
      <span className="text-[15px] font-semibold tracking-tight">Reflo</span>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen w-full bg-background text-foreground">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-border bg-sidebar md:flex">
        <div className="flex h-16 items-center border-b border-border px-5">
          <Wordmark />
        </div>
        <div className="px-4 pb-2 pt-5">
          <p className="section-label">Workspace</p>
        </div>
        <nav className="flex flex-col gap-1 px-3" aria-label="Primary">
          {NAV.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              activeOptions={{ exact: false }}
              className="group relative flex items-center gap-2.5 rounded-md px-3 py-2.5 text-[13px] text-muted-foreground transition-colors hover:bg-card hover:text-foreground"
              activeProps={{
                className:
                  "bg-card text-foreground font-medium border border-border before:absolute before:left-0 before:top-2 before:bottom-2 before:w-0.5 before:rounded-full before:bg-primary",
              }}
              inactiveProps={{ className: "border border-transparent" }}
            >
              <Icon className="size-4 opacity-80 group-hover:opacity-100" />
              {label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto border-t border-border p-4">
          <div className="mb-4 flex items-center gap-2 text-[11px] font-medium text-resolved">
            <Activity className="size-3.5" aria-hidden />
            <span>Policy enforcement active</span>
          </div>
          <div className="flex items-start gap-2 text-[11px] leading-relaxed text-muted-foreground">
            <ScrollText className="mt-0.5 size-3.5 shrink-0" aria-hidden />
            <span>Every action is bounded by an explicit rule and written to the audit trail.</span>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-1 overflow-x-auto border-b border-border bg-sidebar px-4 py-2 md:hidden">
          <div className="mr-3 shrink-0">
            <Wordmark />
          </div>
          {NAV.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              activeOptions={{ exact: false }}
              className="shrink-0 rounded-md px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground"
              activeProps={{ className: "bg-card border border-border text-foreground font-medium" }}
            >
              {label}
            </Link>
          ))}
        </div>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}

export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
}: {
  title: string;
  description: string;
  eyebrow?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="page-header border-b border-border bg-card px-6 py-7 md:px-10 md:py-8">
      <div className="page-header-inner flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          {eyebrow ? <p className="section-label mb-2">{eyebrow}</p> : null}
          <h1 className="page-title">{title}</h1>
          <p className="mt-2 max-w-4xl text-sm leading-relaxed text-muted-foreground">{description}</p>
        </div>
        {actions ? <div className="w-full shrink-0 sm:w-auto">{actions}</div> : null}
      </div>
    </div>
  );
}

/** Level-2 label: section / card headings. */
export function SectionLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return <h2 className={cn("section-label", className)}>{children}</h2>;
}

/** The one card treatment used everywhere. */
export function Surface({
  children,
  className,
  as: Tag = "div",
}: {
  children: React.ReactNode;
  className?: string;
  as?: "div" | "section";
}) {
  return <Tag className={cn("surface", className)}>{children}</Tag>;
}

export function GhostButton({
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={cn(
        "inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs font-medium text-foreground transition-colors hover:bg-secondary active:bg-secondary/70",
        className,
      )}
    />
  );
}

export function PrimaryButton({
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={cn(
        "inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90 active:bg-primary/80",
        className,
      )}
    />
  );
}
