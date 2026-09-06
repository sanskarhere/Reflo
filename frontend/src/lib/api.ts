import { queryOptions } from "@tanstack/react-query";

/**
 * Single fetching layer for Reflo. Every network call in the app goes through
 * this file — screens only consume the query options exported at the bottom.
 * Base URL comes from VITE_API_BASE_URL.
 */

export const API_BASE_URL = (import.meta.env['VITE_API_BASE_URL'] as string | undefined)?.replace(
  /\/+$/,
  "",
);

export type CaseStatus =
  | "DETECTED"
  | "CLASSIFIED"
  | "DECIDED"
  | "GATED"
  | "EXECUTING"
  | "RESOLVED"
  | "STOPPED"
  | "ESCALATED";

export type Stage = CaseStatus;

export const CASE_STATUSES: CaseStatus[] = [
  "DETECTED",
  "CLASSIFIED",
  "DECIDED",
  "GATED",
  "EXECUTING",
  "RESOLVED",
  "STOPPED",
  "ESCALATED",
];

export interface RecoveryCase {
  id: string;
  subscription_id: string;
  customer_id: string;
  amount_paise: number;
  root_cause: string;
  decision: string;
  gate_result: string | null;
  status: CaseStatus;
  created_at: string;
}

export interface AuditEntry {
  stage: Stage;
  input: unknown;
  output: unknown;
  rule_fired: string | null;
  timestamp: string;
}

export interface BatchMetrics {
  batch_id: string;
  batch_size: number;
  recovered_amount_paise: number;
  recovery_rate: number;
  baseline_recovery_rate: number;
  guardrail_blocked_count: number;
}

export interface BatchSummary {
  batch_id: string;
  batch_size: number;
  recovered_amount_paise: number;
  recovery_rate: number | null;
  created_at: string | null;
}

export interface GuardrailRule {
  id: string;
  name: string;
  condition: string;
  forced_action: string;
  severity: "hard_stop" | "escalate" | "throttle" | string;
}

export const ROOT_CAUSES = [
  "insufficient_funds",
  "expired_instrument",
  "mandate_revoked",
  "bank_timeout",
  "issuer_decline",
  "unknown",
] as const;

const ROOT_CAUSE_LABELS: Record<string, string> = {
  insufficient_funds: "Insufficient funds",
  expired_instrument: "Expired instrument",
  mandate_revoked: "Mandate revoked",
  bank_timeout: "Bank timeout",
  issuer_decline: "Issuer decline",
  unknown: "Unknown",
};

export const rootCauseLabel = (value: string) =>
  ROOT_CAUSE_LABELS[value] ?? value.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

export class ApiError extends Error {}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  if (!API_BASE_URL) {
    throw new ApiError(
      "VITE_API_BASE_URL is not set. Point it at your Reflo backend and reload.",
    );
  }
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      headers: { Accept: "application/json" },
      ...(signal ? { signal } : {}),
    });
  } catch {
    throw new ApiError(`Could not reach the Reflo API at ${API_BASE_URL}.`);
  }
  if (!res.ok) {
    throw new ApiError(`Request to ${path} failed (${res.status} ${res.statusText}).`);
  }
  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiError(`The API returned a response that was not valid JSON (${path}).`);
  }
}

/**
 * Admin-secret storage for the "run a batch" action (POST /admin/run-batch).
 * That endpoint fires real Razorpay test-mode calls and writes to the DB, so
 * it isn't opened up with zero friction — the secret is typed once by
 * whoever is driving the demo and kept in sessionStorage only. It is never
 * bundled into the app's JS and is cleared automatically when the tab closes.
 */
const ADMIN_SECRET_KEY = "reflo:admin-secret";

export const getStoredAdminSecret = (): string =>
  (typeof window !== "undefined" && window.sessionStorage.getItem(ADMIN_SECRET_KEY)) || "";

export const setStoredAdminSecret = (secret: string): void => {
  if (typeof window === "undefined") return;
  if (secret) window.sessionStorage.setItem(ADMIN_SECRET_KEY, secret);
  else window.sessionStorage.removeItem(ADMIN_SECRET_KEY);
};

async function post<T>(path: string, body: unknown, headers: Record<string, string> = {}): Promise<T> {
  if (!API_BASE_URL) {
    throw new ApiError(
      "VITE_API_BASE_URL is not set. Point it at your Reflo backend and reload.",
    );
  }
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json", ...headers },
      body: JSON.stringify(body ?? {}),
    });
  } catch {
    throw new ApiError(`Could not reach the Reflo API at ${API_BASE_URL}.`);
  }
  if (!res.ok) {
    if (res.status === 401) {
      throw new ApiError("Admin secret was missing or incorrect.");
    }
    throw new ApiError(`Request to ${path} failed (${res.status} ${res.statusText}).`);
  }
  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiError(`The API returned a response that was not valid JSON (${path}).`);
  }
}

export interface CaseFilters {
  status?: string;
  root_cause?: string;
  sort_by?: string;
  order?: "asc" | "desc";
}

const qs = (filters: CaseFilters) => {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(filters)) if (v && v !== "all") p.set(k, v);
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const casesQueryOptions = (filters: CaseFilters = {}) =>
  queryOptions({
    queryKey: ["reflo", "cases", filters],
    queryFn: ({ signal }) =>
      request<{ cases: RecoveryCase[] }>(`/cases${qs(filters)}`, signal).then(
        (d) => d.cases ?? [],
      ),
  });

export const caseQueryOptions = (caseId: string) =>
  queryOptions({
    queryKey: ["reflo", "case", caseId],
    queryFn: ({ signal }) =>
      request<RecoveryCase | { case: RecoveryCase }>(
        `/cases/${encodeURIComponent(caseId)}`,
        signal,
      ).then((d) => ("case" in d ? d.case : d)),
  });

export const auditQueryOptions = (caseId: string) =>
  queryOptions({
    queryKey: ["reflo", "audit", caseId],
    queryFn: ({ signal }) =>
      request<{ case_id: string; audit_trail: AuditEntry[] }>(
        `/cases/${encodeURIComponent(caseId)}/audit`,
        signal,
      ).then((d) => d.audit_trail ?? []),
  });

export const batchMetricsQueryOptions = (batchId: string) =>
  queryOptions({
    queryKey: ["reflo", "batch", batchId],
    queryFn: ({ signal }) =>
      request<BatchMetrics>(`/batch/${encodeURIComponent(batchId)}/metrics`, signal),
    enabled: batchId.length > 0,
  });

export const rulesQueryOptions = queryOptions({
  queryKey: ["reflo", "rules"],
  queryFn: ({ signal }) =>
    request<{ rules: GuardrailRule[] }>(`/rules`, signal).then((d) => d.rules ?? []),
});

/** Recent batches, for the picker on the Metrics screen. Newest first. */
export const batchesQueryOptions = queryOptions({
  queryKey: ["reflo", "batches"],
  queryFn: ({ signal }) =>
    request<{ batches: BatchSummary[] }>(`/batches`, signal).then((d) => d.batches ?? []),
});

/**
 * Triggers POST /admin/run-batch — generates a fresh synthetic batch and
 * runs it through the full pipeline against the live backend. Requires the
 * admin secret configured in Render's ADMIN_SECRET env var; see
 * getStoredAdminSecret/setStoredAdminSecret above for how that's supplied.
 */
export async function runBatch(n: number, adminSecret: string): Promise<{ batch_id: string }> {
  if (!adminSecret) {
    throw new ApiError("Enter the admin secret before running a batch.");
  }
  return post<{ batch_id: string }>(`/admin/run-batch?n=${encodeURIComponent(String(n))}`, {}, {
    "X-Admin-Secret": adminSecret,
  });
}
