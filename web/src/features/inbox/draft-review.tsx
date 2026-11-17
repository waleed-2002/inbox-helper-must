import { AlertCircle, ArrowLeft, FilePenLine, History, RotateCw, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/fields";
import { DraftLabel, EmptyState, Initials, InlineError, Loading } from "./workspace-parts";
import { intentLabels, readableError, type CandidateMessage, type Draft, type ReviewAction } from "./inbox-api";

const eventLabels = { approve: "Approved", reject: "Rejected", edit: "Edited", regenerate: "Regenerated" };
const flagLabels: Record<string, string> = {
  date: "Date reference", time: "Time reference", monetary_amount: "Monetary amount",
  hiring_commitment: "Hiring commitment", company_policy: "Company policy claim",
  unsupported_followup: "Unverified follow-up promise", assistant_instruction: "Assistant instruction",
  control_characters: "Unsupported characters",
};

function readableCode(code: string) {
  return flagLabels[code] ?? code.replaceAll("_", " ");
}

function SafetyNotes({ draft }: { draft: Draft }) {
  if (draft.regenerating) return <p className="inline-loading" role="status"><Loading />Regenerating this draft…</p>;
  return <>
    {draft.requires_manual_writing && <div className="notice warning-notice">
      <ShieldAlert size={17} aria-hidden="true" />
      <div><strong>Manual writing required</strong>
        <p>{draft.safety_flags.length ? `Resolve before approval: ${draft.safety_flags.map(readableCode).join(", ")}.` : draft.review_reason}</p>
      </div>
    </div>}
    {!draft.requires_manual_writing && draft.review_reason !== "Human review is required." &&
      <p className="draft-note">{draft.review_reason}</p>}
    {(draft.generation_safety_flags.length > 0 || draft.generation_failure) &&
      <details className="minor-details"><summary>Generation details</summary>
        {draft.generation_safety_flags.length > 0 && <p>Original flags: {draft.generation_safety_flags.map(readableCode).join(", ")}</p>}
        {draft.generation_failure && <p>Generation result: {readableCode(draft.generation_failure)}</p>}
      </details>}
  </>;
}

export function DraftReview({ message, draft, loading, error, busy, generationBusy, draftText, dirty, conflict,
  onBack, onRefresh, onText, onDiscard, onRebase, onReview }: {
  message: CandidateMessage | null; draft: Draft | undefined; loading: boolean; error: unknown;
  busy: boolean; generationBusy: boolean; draftText: string; dirty: boolean; conflict: boolean;
  onBack: () => void; onRefresh: () => void; onText: (text: string) => void;
  onDiscard: () => void; onRebase: () => void; onReview: (action: ReviewAction) => void;
}) {
  if (!message) return <section className="review-pane review-empty" aria-label="Review panel">
    <EmptyState title="Select a message" icon="file">Read the candidate’s message and review the reply here.</EmptyState>
  </section>;

  const length = Array.from(draftText.trim()).length;
  const blocked = busy || Boolean(error) || !draft || draft.regenerating || conflict;
  const classification = message.classification;

  return <section className="review-pane" aria-labelledby="review-title">
    <div className="review-scroll">
      <div className="review-content">
        <Button variant="ghost" className="review-back" onClick={onBack}><ArrowLeft aria-hidden="true" />Back to messages</Button>
        <header className="review-heading">
          <Initials name={message.candidate_name} />
          <div>
            <h2 id="review-title" tabIndex={-1}>{message.candidate_name}</h2>
            <p>{classification ? intentLabels[classification.primary_intent] : "Unclassified"}<span aria-hidden="true"> · </span>Message {message.source_id}</p>
          </div>
          <DraftLabel draft={draft ?? message.draft} />
        </header>

        <section aria-labelledby="original-title" className="review-section">
          <h3 id="original-title">Original message</h3>
          <div className="original-message">{message.message_text}</div>
          {(classification || message.classification_failure || message.candidate_instruction_detected) &&
            <details className="minor-details classification-details"><summary>Classification notes</summary>
              {classification && <p>{classification.short_summary}</p>}
              {classification?.secondary_intents.length ?
                <p>Additional intents: {classification.secondary_intents.map((intent) => intentLabels[intent]).join(", ")}</p> : null}
              {classification?.needs_review && <p>{classification.review_reason}</p>}
              {message.classification_failure && <p>Classification unavailable: {readableCode(message.classification_failure)}</p>}
              {message.candidate_instruction_detected && <p>Instructions embedded in the message were detected. Verify the classification manually.</p>}
            </details>}
        </section>

        <section aria-labelledby="reply-title" className="review-section">
          <div className="section-heading"><h3 id="reply-title">Reply draft</h3>
            {draft && <span className="revision-label">Revision {draft.revision}</span>}</div>
          {error ? <InlineError retry={onRefresh}>{readableError(error)}</InlineError> : null}
          {loading && <p className="inline-loading" role="status"><Loading />Loading draft…</p>}
          {!message.draft && <p className="muted-text">Process this batch to create a draft for review.</p>}
          {draft && <>
            <SafetyNotes draft={draft} />
            {conflict && <div className="notice warning-notice" role="alert">
              <AlertCircle size={17} aria-hidden="true" />
              <div><strong>The draft has changed</strong>
                <p>Revision {draft.revision} is current. Your unsaved text is still below.</p>
                <details><summary>Compare with the current reply</summary><p className="plain-text">{draft.reply ?? "This revision has no reply."}</p></details>
                <div className="action-row">
                  <Button variant="outline" onClick={onRebase} disabled={busy || Boolean(error) || draft.regenerating}>Keep my edit</Button>
                  <Button variant="ghost" onClick={onDiscard}>Use current reply</Button>
                </div>
              </div>
            </div>}
            <label className="sr-only" htmlFor="reply-editor">Reply text</label>
            <Textarea id="reply-editor" value={draftText} readOnly={blocked} aria-describedby="reply-length"
              placeholder="Write a reply for human review…" onChange={(event) => onText(event.target.value)} />
            <div className="editor-footer">
              <span>{dirty ? "Unsaved changes" : draft.edited_reply !== null ? "Edited reply" : draft.generated_reply !== null ? "AI draft" : "No reply saved"}</span>
              <span id="reply-length" className={length > 1200 ? "text-danger" : undefined}>{length} / 1,200</span>
            </div>
            {draft.status === "approved" && <p className="draft-note">Saving an edit or regenerating will clear approval.</p>}
            <div className="review-actions">
              <Button variant="outline" className="reject-action" disabled={blocked || dirty || draft.status === "rejected"} onClick={() => onReview("reject")}>Reject</Button>
              <Button variant="outline" disabled={blocked || generationBusy} onClick={() => onReview("regenerate")}><RotateCw aria-hidden="true" />Regenerate</Button>
              <div className="primary-actions">
                <Button variant={dirty ? "default" : "outline"} disabled={blocked || !dirty || !length || length > 1200} onClick={() => onReview("edit")}>Save changes</Button>
                <Button disabled={blocked || dirty || draft.status !== "pending_review" || draft.requires_manual_writing || !draft.reply}
                  onClick={() => onReview("approve")}>Approve reply</Button>
              </div>
            </div>
          </>}
        </section>

        {draft && <section className="review-section history-section" aria-labelledby="history-title">
          <div className="section-heading"><h3 id="history-title"><History size={16} aria-hidden="true" />Review history</h3>
            <span className="revision-label">{draft.review_events.length}</span></div>
          {draft.review_events.length === 0 ? <p className="muted-text">No review actions yet.</p> :
            <ol className="history-list">{[...draft.review_events].reverse().map((event) => <li key={event.id}>
              <FilePenLine size={15} aria-hidden="true" />
              <div><p><strong>{eventLabels[event.action]}</strong> <span>Revision {event.to_revision}</span></p>
                <time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}</time>
                {event.reason && <p className="event-reason">{event.reason}</p>}
                {(event.reply_before || event.reply_after) && <details className="minor-details"><summary>View revision text</summary>
                  {event.reply_before && <p className="plain-text"><strong>Previous reply</strong><br />{event.reply_before}</p>}
                  {event.reply_after && event.reply_after !== event.reply_before && <p className="plain-text"><strong>Resulting reply</strong><br />{event.reply_after}</p>}
                </details>}
              </div>
            </li>)}</ol>}
        </section>}
      </div>
    </div>
  </section>;
}
