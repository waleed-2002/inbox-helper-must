import {
  AlertCircle, Archive, Check, ChevronRight, Clock3, FileText, Inbox, Layers3, LoaderCircle, Search,
} from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/fields";
import { intentLabels, type BatchStatus, type BatchSummary, type CandidateMessage, type DraftSummary,
  type Intent, type IntentGroup } from "./inbox-api";
import { cn } from "@/lib/utils";

export type View = "inbox" | "outbox";

const draftStates = {
  pending_review: "Pending review", approved: "Approved", rejected: "Rejected",
} as const;
const batchStates = {
  imported: "Ready to process", processing: "Processing", interrupted: "Interrupted",
  completed: "Processed", completed_with_errors: "Processed with errors",
} as const;

export function Initials({ name }: { name: string }) {
  const words = name.trim().split(/\s+/);
  const initials = [words[0], words.length > 1 ? words.at(-1) : undefined]
    .filter(Boolean).map((word) => Array.from(word ?? "")[0]).join("").toLocaleUpperCase();
  return <span className="initials" aria-hidden="true">{initials}</span>;
}

export function DraftLabel({ draft }: { draft: DraftSummary | null }) {
  if (!draft) return <span className="draft-label">Unprocessed</span>;
  if (draft.regenerating) return <span className="draft-label"><Loading />Regenerating</span>;
  if (draft.status === "rejected") return <span className="draft-label rejected"><span className="status-dot" />Rejected</span>;
  if (draft.requires_manual_writing) return <span className="draft-label warning"><AlertCircle size={13} />Manual writing</span>;
  return <span className={cn("draft-label", draft.status === "approved" && "success")}>
    {draft.status === "approved" ? <Check size={13} /> : <Clock3 size={13} />}{draftStates[draft.status]}
  </span>;
}

export function Loading() {
  return <LoaderCircle aria-hidden="true" className="spin" size={16} />;
}

export function EmptyState({ title, children, action, icon = "mail" }:
  { title: string; children: ReactNode; action?: ReactNode; icon?: "mail" | "file" | "archive" }) {
  const Icon = icon === "file" ? FileText : icon === "archive" ? Archive : Inbox;
  return <div className="empty-state">
    <span className="empty-icon"><Icon size={20} aria-hidden="true" /></span>
    <h2>{title}</h2><p>{children}</p>{action}
  </div>;
}

export function Sidebar({ batches, batchId, groups, intent, view, approved, onBatch, onView, onIntent }:
  { batches: BatchSummary[]; batchId: number | null; groups: IntentGroup[]; intent: Intent | "all"; view: View;
    approved: number; onBatch: (id: number) => void; onView: (view: View) => void; onIntent: (intent: Intent | "all") => void }) {
  const counts = new Map(groups.map((group) => [group.intent, group.messages.length]));
  return <nav className="sidebar-nav" aria-label="Workspace navigation">
    <div className="nav-section">
      <button className="nav-row" aria-current={view === "inbox" ? "page" : undefined} onClick={() => onView("inbox")}>
        <Inbox size={16} aria-hidden="true" /><span>Inbox</span>
      </button>
      <button className="nav-row" aria-current={view === "outbox" ? "page" : undefined} onClick={() => onView("outbox")}>
        <Archive size={16} aria-hidden="true" /><span>Outbox</span>{approved > 0 && <span className="nav-count">{approved}</span>}
      </button>
    </div>
    <div className="nav-section">
      <h2>Batches</h2>
      {batches.length === 0 && <p className="nav-empty">No batches imported</p>}
      {batches.map((batch) => <button key={batch.batch_id} className="nav-row batch-row"
        aria-pressed={batch.batch_id === batchId} onClick={() => onBatch(batch.batch_id)}>
        <Layers3 size={15} aria-hidden="true" />
        <span className="batch-label">Batch #{batch.batch_id}<small>{new Date(batch.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</small></span>
        <span className="nav-count">{batch.message_count}</span>
      </button>)}
    </div>
    {batchId !== null && <div className="nav-section intent-section">
      <h2>Intent</h2>
      <button className="nav-row intent-row" aria-pressed={view === "inbox" && intent === "all"} onClick={() => onIntent("all")}>
        <span>All intents</span><span className="nav-count">{groups.reduce((sum, group) => sum + group.messages.length, 0)}</span>
      </button>
      {(Object.keys(intentLabels) as Intent[]).map((key) => <button key={key} className="nav-row intent-row"
        aria-pressed={view === "inbox" && intent === key} onClick={() => onIntent(key)}>
        <span>{intentLabels[key]}</span><span className="nav-count">{counts.get(key) ?? 0}</span>
      </button>)}
    </div>}
  </nav>;
}

export function BatchProgress({ status, requested }: { status: BatchStatus; requested: boolean }) {
  const working = requested || status.status === "processing";
  return <div className="batch-progress" role="status">
    <div className="batch-progress-label">
      <span>{working && <Loading />}{working ? "Processing messages" : batchStates[status.status]}</span>
      <span className="tabular-nums">{status.processed}/{status.message_count}</span>
    </div>
    {working && <progress aria-label="Messages processed" max={status.message_count} value={status.processed} />}
    {status.processing_failures > 0 && <p>{status.processing_failures} processing {status.processing_failures === 1 ? "failure" : "failures"}. Open the affected messages to review or regenerate.</p>}
  </div>;
}

export function InboxList({ view, groups, total, selected, search, disabled, loading, hasBatch, intent,
  onSearch, onSelect }: {
  view: View; groups: IntentGroup[]; total: number; selected: number | null; search: string; disabled: boolean;
  loading: boolean; hasBatch: boolean; intent: Intent | "all";
  onSearch: (value: string) => void; onSelect: (message: CandidateMessage) => void;
}) {
  return <section className="inbox-pane" aria-labelledby="inbox-title">
    <div className="inbox-heading">
      <div className="heading-line"><h1 id="inbox-title">{view === "inbox" ? "Inbox" : "Outbox"}</h1>
        {hasBatch && !loading && <span className="total-count">{total}</span>}
      </div>
      {hasBatch && <div className="search-field">
        <Search size={16} aria-hidden="true" />
        <Input aria-label="Search messages" type="search" placeholder="Search messages…" value={search} onChange={(event) => onSearch(event.target.value)} />
      </div>}
      {view === "inbox" && intent !== "all" && <p className="muted-text active-filter">{intentLabels[intent]}</p>}
    </div>
    <div className="inbox-scroll" aria-busy={loading}>
      {loading ? <p className="inline-loading" role="status"><Loading />Loading messages…</p> : !groups.length ?
        <EmptyState title={search ? "No matching messages" : !hasBatch ? "No messages yet" : view === "outbox" ? "No approved replies" : "No messages in this view"}
          icon={view === "outbox" ? "archive" : "mail"}>
          {search ? "Try a different name, message ID, or search term." : !hasBatch ? "Import a CSV to start reviewing candidate messages." :
            view === "outbox" ? "Approved replies for this batch will appear here." : "Choose another intent filter to see more messages."}
        </EmptyState> : groups.map((group) => <section key={group.intent} className="message-group" aria-label={intentLabels[group.intent]}>
          <h2>{intentLabels[group.intent]}<span>{group.messages.length}</span></h2>
          <ul>{group.messages.map((message) => <li key={message.id}>
            <button id={`candidate-${message.id}`} className="message-row" disabled={disabled}
              aria-pressed={selected === message.id} onClick={() => onSelect(message)}>
              <Initials name={message.candidate_name} />
              <span className="message-row-body">
                <span className="message-name">{message.candidate_name}</span>
                <span className="message-preview">{message.message_text}</span>
                <DraftLabel draft={message.draft} />
              </span>
              <ChevronRight className="message-chevron" size={15} aria-hidden="true" />
            </button>
          </li>)}</ul>
        </section>)}
    </div>
  </section>;
}

export function InlineError({ children, retry }: { children: ReactNode; retry?: () => void }) {
  return <div className="notice error-notice" role="alert">
    <AlertCircle size={16} aria-hidden="true" /><div>{children}</div>
    {retry && <Button variant="outline" className="notice-button" onClick={retry}>Retry</Button>}
  </div>;
}
