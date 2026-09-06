import { createFileRoute, Link } from "@tanstack/react-router";
import {
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Check,
  CircleCheckBig,
  Clock3,
  FileCheck2,
  LockKeyhole,
  ReceiptText,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  Waypoints,
  Zap,
} from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Reflo — Recovery you can explain" },
      {
        name: "description",
        content:
          "Reflo recovers failed subscription payments with every decision gated, bounded and auditable.",
      },
      { property: "og:title", content: "Reflo — Recovery you can explain" },
      {
        property: "og:description",
        content:
          "An accountable recovery agent for failed subscription payments.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  errorComponent: ({ error }) => <div role="alert">{error.message}</div>,
  component: LandingPage,
});

function Wordmark() {
  return (
    <Link to="/" className="flex items-center gap-2.5 text-foreground">
      <span className="grid size-7 place-items-center rounded-md bg-primary text-primary-foreground" aria-hidden>
        <span className="size-2 rounded-sm bg-resolved" />
      </span>
      <span className="text-[15px] font-semibold tracking-tight">Reflo</span>
    </Link>
  );
}

function RecoveryPreview() {
  return (
    <div className="landing-reveal relative overflow-hidden rounded-xl border border-border bg-card shadow-2xl shadow-foreground/10 ring-1 ring-black/5">
      <div className="flex items-center justify-between border-b border-border bg-sidebar/70 px-4 py-3">
        <div className="flex items-center gap-2"><span className="size-2 rounded-full bg-resolved" /><span className="section-label">Recovery queue</span></div>
        <span className="code-text text-muted-foreground">LIVE / guarded</span>
      </div>
      <div className="grid grid-cols-3 gap-px border-b border-border bg-border">
        {[["94.2%", "recovery rate", "text-resolved"], ["₹18.4L", "recovered", "text-foreground"], ["17", "guardrail blocks", "text-stopped"]].map(([value, label, color]) => (
          <div key={label} className="bg-card px-4 py-4"><p className={`text-xl font-semibold tabular tracking-[-0.03em] ${color}`}>{value}</p><p className="mt-1 text-[10px] uppercase tracking-[0.08em] text-muted-foreground">{label}</p></div>
        ))}
      </div>
      <div className="divide-y divide-border">
        {[["Cedar & Co.", "Insufficient funds", "Retry scheduled", "pending"], ["Northstar Labs", "Expired instrument", "Customer notified", "resolved"], ["Morrow Studio", "Issuer decline", "Escalated to human", "stopped"]].map(([customer, cause, action, state]) => (
          <div key={customer} className="grid grid-cols-[1fr_auto] gap-3 px-4 py-3 sm:grid-cols-[1.1fr_1fr_1.1fr_auto] sm:items-center">
            <span className="text-[13px] font-semibold">{customer}</span><span className="hidden text-xs text-muted-foreground sm:block">{cause}</span><span className="hidden text-xs text-muted-foreground sm:block">{action}</span>
            <span className="inline-flex items-center gap-1.5 text-[11px] font-medium capitalize text-muted-foreground"><span className={`size-1.5 rounded-full ${state === "resolved" ? "bg-resolved" : state === "stopped" ? "bg-stopped" : "bg-pending"}`} />{state}</span>
          </div>
        ))}
      </div>
      <div className="border-t border-border bg-sidebar/40 px-4 py-3 text-[11px] text-muted-foreground"><span className="mr-2 inline-block size-1.5 rounded-full bg-resolved align-middle" />Every action is evaluated against policy before it executes.</div>
    </div>
  );
}

function SignalCard({
  icon: Icon,
  eyebrow,
  title,
  copy,
  tone = "resolved",
}: {
  icon: typeof BarChart3;
  eyebrow: string;
  title: string;
  copy: string;
  tone?: "resolved" | "pending" | "stopped";
}) {
  const color = tone === "stopped" ? "text-stopped" : tone === "pending" ? "text-pending" : "text-resolved";

  return (
    <article className="group border-t border-border pt-5 transition-colors duration-300 hover:border-foreground/40">
      <div className="flex items-center justify-between">
        <Icon className={`size-5 ${color}`} />
        <ArrowUpRight className="size-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
      </div>
      <p className="section-label mt-7">{eyebrow}</p>
      <h3 className="mt-2 text-lg font-semibold tracking-tight">{title}</h3>
      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{copy}</p>
    </article>
  );
}

function WorkflowStep({
  number,
  icon: Icon,
  title,
  copy,
}: {
  number: string;
  icon: typeof Waypoints;
  title: string;
  copy: string;
}) {
  return (
    <div className="relative grid gap-4 border-l border-border pl-6 md:grid-cols-[auto_1fr] md:gap-8 md:pl-8">
      <span className="absolute -left-[5px] top-0 size-2.5 rounded-full bg-resolved ring-4 ring-background" />
      <span className="code-text text-muted-foreground">{number}</span>
      <div>
        <div className="flex items-center gap-2">
          <Icon className="size-4 text-resolved" />
          <h3 className="font-semibold">{title}</h3>
        </div>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">{copy}</p>
      </div>
    </div>
  );
}

function LandingPage() {
  return (
    <div className="min-h-screen overflow-hidden bg-background text-foreground">
      <header className="sticky top-0 z-20 border-b border-border/80 bg-card/90 backdrop-blur"><div className="mx-auto flex h-[4.5rem] max-w-6xl items-center justify-between px-5 md:px-8"><Wordmark /><nav className="hidden items-center gap-8 text-[13px] text-muted-foreground md:flex" aria-label="Main"><a href="#how-it-works" className="transition-colors hover:text-foreground">How it works</a><a href="#signals" className="transition-colors hover:text-foreground">Why Reflo</a><Link to="/recovery" className="inline-flex items-center gap-1.5 font-medium text-foreground transition-colors hover:text-resolved">Open workspace <ArrowRight className="size-3.5" /></Link></nav><Link to="/recovery" className="inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-3.5 text-xs font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 md:hidden">Workspace <ArrowRight className="size-3.5" /></Link></div></header>
      <main>
        <section className="relative border-b border-border bg-card px-5 pb-16 pt-8 md:px-8 md:pb-20 md:pt-14 lg:min-h-[calc(100svh-4.5rem)]"><div className="pointer-events-none absolute -right-32 -top-24 size-96 rounded-full border-[32px] border-resolved/10" /><div className="mx-auto grid max-w-6xl items-center gap-12 lg:min-h-[calc(100svh-8rem)] lg:grid-cols-[0.86fr_1.14fr] lg:gap-20"><div className="relative max-w-xl"><div className="landing-reveal mb-6 inline-flex items-center gap-2 rounded-full border border-resolved/30 bg-resolved-soft px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.1em] text-resolved"><Sparkles className="size-3.5" />Accountable payment recovery</div><h1 className="landing-reveal landing-delay-1 max-w-xl text-5xl font-semibold leading-[1.02] tracking-[-0.045em] md:text-6xl xl:text-7xl">Recover failed payments.<br /><span className="text-resolved">Keep customer trust.</span></h1><p className="landing-reveal landing-delay-2 mt-5 max-w-lg text-base font-medium leading-relaxed text-foreground/75 md:text-[17px]">An accountable recovery agent for failed subscription payments.</p><p className="landing-reveal landing-delay-2 mt-3 max-w-lg text-sm leading-relaxed text-muted-foreground md:text-base">Reflo proposes the next best step, checks it against your policies, and leaves a clear record of what happened.</p><div className="landing-reveal landing-delay-3 mt-8 flex flex-wrap items-center gap-3"><Link to="/recovery" className="inline-flex h-11 items-center gap-2 rounded-md bg-primary px-5 text-sm font-medium text-primary-foreground shadow-lg shadow-primary/10 transition-transform hover:-translate-y-0.5 hover:bg-primary/90">Enter the workspace <ArrowRight className="size-4" /></Link><a href="#how-it-works" className="inline-flex h-11 items-center px-3 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">See how it works</a></div><div className="landing-reveal landing-delay-3 mt-10 flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted-foreground">{["Bounded by policy", "Human escalation built in", "Every decision logged"].map((item) => <span key={item} className="inline-flex items-center gap-1.5"><Check className="size-3.5 text-resolved" />{item}</span>)}</div></div><div className="relative lg:translate-y-2"><RecoveryPreview /><p className="mt-3 text-right font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">A clearer path from failure to resolution</p></div></div></section>
        <section id="signals" className="mx-auto max-w-6xl px-5 py-16 md:px-8 md:py-24"><div className="grid gap-10 md:grid-cols-[0.8fr_1.2fr] md:gap-20"><div><p className="section-label">The cost of guessing</p><h2 className="mt-3 max-w-sm text-3xl font-semibold leading-tight tracking-[-0.03em] md:text-4xl">Failed payments are signals, not just errors.</h2><p className="mt-5 max-w-sm text-sm leading-relaxed text-muted-foreground">A better recovery starts by understanding what actually happened.</p></div><div className="grid gap-8 sm:grid-cols-3"><SignalCard icon={TriangleAlert} eyebrow="Diagnosis" title="Know the why" copy="Separate a soft decline from a real customer risk before an action is proposed." tone="stopped" /><SignalCard icon={Zap} eyebrow="Momentum" title="Move with intent" copy="Turn the next best action into a clear, reviewable decision instead of a blind retry." tone="pending" /><SignalCard icon={ReceiptText} eyebrow="Confidence" title="Keep the receipt" copy="Give your team the context to explain every recovery, stop, and escalation." /></div></div></section>
        <section id="how-it-works" className="border-y border-border bg-sidebar/50 px-5 py-16 md:px-8 md:py-24"><div className="mx-auto grid max-w-6xl gap-12 md:grid-cols-[0.75fr_1.25fr] md:gap-24"><div><p className="section-label">The operating model</p><h2 className="mt-3 max-w-sm text-3xl font-semibold leading-tight tracking-[-0.03em] md:text-4xl">A recovery loop your team can inspect.</h2><p className="mt-4 max-w-sm text-base leading-relaxed text-muted-foreground">The agent does the repetitive work. Your policies stay in charge, and every handoff leaves a useful record.</p><Link to="/rules" className="mt-7 inline-flex items-center gap-2 text-sm font-medium text-foreground transition-colors hover:text-resolved">Read the guardrails <ArrowRight className="size-4" /></Link></div><div className="space-y-10"><WorkflowStep number="01 / UNDERSTAND" icon={Waypoints} title="Classify the failure" copy="An expired instrument should not follow the same path as a bank timeout. The case starts with context." /><WorkflowStep number="02 / BOUND" icon={ShieldCheck} title="Apply the boundary" copy="Run the proposed action through explicit guardrails. The rules are code, not a hidden instruction in a prompt." /><WorkflowStep number="03 / RECORD" icon={FileCheck2} title="Leave a receipt" copy="See what happened, why it happened, and where a human needs to step in." /></div></div></section>
        <section id="principles" className="mx-auto max-w-6xl px-5 py-16 md:px-8 md:py-24"><div className="flex flex-col gap-8 border-b border-border pb-10 md:flex-row md:items-end md:justify-between"><div><p className="section-label">Built for accountable automation</p><h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-[-0.03em] md:text-4xl">Trust is a product feature.</h2></div><p className="max-w-sm text-sm leading-relaxed text-muted-foreground">Every control exists to protect the customer relationship while giving your team a faster answer.</p></div><div className="grid gap-8 pt-10 sm:grid-cols-3">{[{ icon: CircleCheckBig, title: "No blind retries", copy: "Every move has a reason." }, { icon: Clock3, title: "Human when it matters", copy: "Escalate with context intact." }, { icon: LockKeyhole, title: "Nothing disappears", copy: "Actions live in the audit trail." }].map(({ icon: Icon, title, copy }) => <div key={title} className="flex gap-3"><Icon className="mt-0.5 size-5 shrink-0 text-resolved" /><div><p className="text-sm font-semibold">{title}</p><p className="mt-1 text-sm text-muted-foreground">{copy}</p></div></div>)}</div></section>
        <section className="border-y border-border bg-primary px-5 py-16 text-primary-foreground md:px-8 md:py-20"><div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-[1fr_auto] md:items-end"><div><p className="section-label text-primary-foreground/60">Make the next decision clear</p><h2 className="mt-3 max-w-xl text-3xl font-semibold tracking-[-0.04em] md:text-5xl">Your queue is waiting for a better answer.</h2><p className="mt-4 max-w-lg text-sm leading-relaxed text-primary-foreground/70">Open the workspace to see how a bounded recovery flow turns payment noise into accountable action.</p></div><Link to="/recovery" className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-resolved px-5 text-sm font-medium text-white shadow-lg shadow-black/10 transition-transform hover:-translate-y-0.5 hover:bg-resolved/90">Open the workspace <ArrowRight className="size-4" /></Link></div></section>
      </main>
      <footer className="mx-auto flex max-w-6xl flex-col gap-3 px-5 py-8 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between md:px-8"><Wordmark /><span>Recovery infrastructure for teams who need to know what happened.</span></footer>
    </div>
  );
}
