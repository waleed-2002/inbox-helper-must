export const intentLabels = {
  application_status: "Application status",
  interview_scheduling: "Interview scheduling",
  role_information: "Role information",
  document_update: "Document update",
  withdrawal: "Withdrawal",
  other: "Other",
  unclassified: "Unclassified",
} as const;

export type Intent = keyof typeof intentLabels;
export type DraftStatus = "pending_review" | "approved" | "rejected";
export type BatchSummary = { batch_id: number; created_at: string; message_count: number };
export type BatchStatus = BatchSummary & {
  status: "imported" | "processing" | "interrupted" | "completed" | "completed_with_errors";
  processed: number;
  processing_failures: number;
  classified: number;
  pending_review: number;
  approved: number;
  rejected: number;
  manual_writing: number;
  regenerating: number;
};
export type DraftSummary = {
  id: number;
  status: DraftStatus;
  revision: number;
  approved_revision: number | null;
  regenerating: boolean;
  requires_manual_writing: boolean;
};
export type ReviewEvent = {
  id: number;
  action: "edit" | "approve" | "reject" | "regenerate";
  from_revision: number;
  to_revision: number;
  from_status: DraftStatus;
  to_status: DraftStatus;
  reply_before: string | null;
  reply_after: string | null;
  safety_flags_before: string[];
  generation_failure_before: string | null;
  reason: string | null;
  created_at: string;
};
export type Draft = DraftSummary & {
  message_id: number;
  generated_reply: string | null;
  edited_reply: string | null;
  reply: string | null;
  review_reason: string;
  generation_failure: string | null;
  generation_safety_flags: string[];
  safety_flags: string[];
  review_events: ReviewEvent[];
};
export type CandidateMessage = {
  id: number;
  source_id: string;
  candidate_name: string;
  message_text: string;
  classification: {
    primary_intent: Exclude<Intent, "unclassified">;
    secondary_intents: Exclude<Intent, "unclassified">[];
    short_summary: string;
    needs_review: boolean;
    review_reason: string;
  } | null;
  classification_failure: string | null;
  candidate_instruction_detected: boolean;
  draft: DraftSummary | null;
};
export type IntentGroup = { intent: Intent; messages: CandidateMessage[] };
export type ImportReceipt = { batch_id: number; message_count: number; duplicate: boolean };
export type ReviewAction = "edit" | "approve" | "reject" | "regenerate";

const apiUrl = (process.env.NEXT_PUBLIC_INBOX_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function request(path: string, options: RequestInit = {}) {
  let response: Response;
  try {
    response = await fetch(`${apiUrl}${path}`, { ...options, cache: "no-store", credentials: "omit" });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError("Could not reach the inbox backend. Check the local servers and try again.", 0);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const fallback = response.status === 422 ? "Check the submitted details and try again." :
      `The backend could not complete this request (HTTP ${response.status}).`;
    throw new ApiError(typeof body?.detail === "string" ? body.detail : fallback, response.status);
  }
  return response;
}

async function json<T>(path: string, options?: RequestInit): Promise<T> {
  return (await request(path, options)).json();
}

export const listBatches = (_key: "batches", signal: AbortSignal) =>
  json<{ batches: BatchSummary[] }>("/batches", { signal });
export const getDraft = (id: number, signal: AbortSignal) => json<Draft>(`/drafts/${id}`, { signal });

export async function getBatch(id: number, signal: AbortSignal) {
  const [status, groups] = await Promise.all([
    json<BatchStatus>(`/batches/${id}/status`, { signal }),
    json<{ batch_id: number; groups: IntentGroup[] }>(`/batches/${id}/groups`, { signal }),
  ]);
  return { status, groups: groups.groups };
}

export function importBatch(file: File) {
  return json<ImportReceipt>("/batches", { method: "POST", headers: { "Content-Type": "text/csv" }, body: file });
}

export function processBatch(id: number) {
  return json<BatchStatus>(`/batches/${id}/process`, { method: "POST", headers: { "Content-Type": "application/json" } });
}

export function reviewDraft(id: number, action: ReviewAction, revision: number, values: { reply?: string; reason?: string }) {
  const path = action === "edit" ? `/drafts/${id}` : `/drafts/${id}/${action}`;
  return json<Draft>(path, {
    method: action === "edit" ? "PATCH" : "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ revision, ...values }),
  });
}

export function exportBatch(id: number) {
  return request(`/batches/${id}/export`);
}

export function isExportable(draft: DraftSummary | null) {
  return draft?.status === "approved" && draft.approved_revision === draft.revision &&
    !draft.requires_manual_writing && !draft.regenerating;
}

export function readableError(error: unknown) {
  return error instanceof ApiError ? error.message : "The request failed. Try again.";
}
