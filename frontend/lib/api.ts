export interface Finding {
  id?: string;
  category: string;
  severity: "low" | "medium" | "high";
  title: string;
  detail: string;
  amount?: number | null;
  quote?: string | null;
}

export interface CompetitorPrice {
  id?: string;
  domain: string;
  url: string;
  price: number;
}

export interface EvidenceItem {
  id: string;
  kind: string;
  object_key: string;
  url?: string;
}

export interface AuditReport {
  id: string;
  parent_id?: string | null;
  url: string;
  domain: string;
  status: "queued" | "running" | "done" | "failed";
  reached_stage?: string | null;
  score?: number | null;
  score_change?: number | null;
  tinyfish_run_id?: string | null;
  streaming_url?: string | null;
  listing?: {
    title?: string | null;
    sale_price?: number | null;
    mrp?: number | null;
    currency?: string | null;
    discount_badge_text?: string | null;
    urgency_texts?: string[];
    stock_texts?: string[];
    preselected_options?: string[];
  } | null;
  agent_result?: {
    reached_stage?: string;
    charge_lines?: Array<{ label: string; amount: number; shown_at_stage: string }>;
    preselected_addons?: Array<{ label: string; amount: number }>;
    timers?: string[];
    urgency_messages?: string[];
    subscription_optins?: string[];
    total?: number | null;
  } | null;
  watch: boolean;
  created_at: string;
  finished_at?: string | null;
  findings: Finding[];
  competitor_prices: CompetitorPrice[];
  evidence: EvidenceItem[];
}

export async function createAudit(url: string, watch: boolean = false): Promise<{ id: string }> {
  const res = await fetch("/api/audits", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, watch }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: "Failed to submit audit" }));
    throw new Error(errorData.detail || `Server responded with ${res.status}`);
  }
  return res.json();
}

export async function getAuditReport(id: string): Promise<AuditReport> {
  const res = await fetch(`/api/audits/${id}`);
  if (!res.ok) {
    throw new Error("Audit report not found");
  }
  return res.json();
}

export async function toggleWatch(id: string): Promise<{ id: string; watch: boolean }> {
  const res = await fetch(`/api/audits/${id}/watch`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error("Failed to toggle watch status");
  }
  return res.json();
}
