// Thin client for the backend routes in docs/ARCHITECTURE.md section 3.6.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function getCase(caseId: string) {
  const res = await fetch(`${API_BASE}/cases/${caseId}`);
  if (!res.ok) throw new Error("Failed to fetch case");
  return res.json();
}

export async function getBatchMetrics(batchId: string) {
  const res = await fetch(`${API_BASE}/batch/${batchId}/metrics`);
  if (!res.ok) throw new Error("Failed to fetch batch metrics");
  return res.json();
}
