"use client";

import { ArrowDownToLine, ClipboardList, Menu, PanelLeft, Plus, RotateCw, Upload } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { DraftReview } from "@/components/draft-review";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input, Textarea } from "@/components/ui/fields";
import { BatchProgress, EmptyState, InboxList, InlineError, Loading, Sidebar, type View } from "@/components/workspace-parts";
import { ApiError, exportBatch, getBatch, getDraft, importBatch, isExportable, listBatches, processBatch,
  readableError, reviewDraft, type CandidateMessage, type Draft, type Intent, type IntentGroup, type ReviewAction } from "@/lib/inbox-api";
import { useResource } from "@/lib/use-resource";

type Selection = { batchId: number | null; messageId: number | null; view: View };
type EditBuffer = { draftId: number; revision: number; text: string };
type Notice = { kind: "error" | "info"; text: string };
type Job = { batchId: number; kind: "process" | "regenerate" };

const noGroups: IntentGroup[] = [];
const maxCsvBytes = 1_048_576;

export function InboxWorkspace({ initial }: { initial: Selection }) {
  const [selection, setSelection] = useState(initial);
  const [intent, setIntent] = useState<Intent | "all">("all");
  const [search, setSearch] = useState("");
  const [edit, setEdit] = useState<EditBuffer | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [importError, setImportError] = useState("");
  const [importBusy, setImportBusy] = useState(false);
  const [reviewDialog, setReviewDialog] = useState<{ action: "reject" | "regenerate"; draft: Draft } | null>(null);
  const [reason, setReason] = useState("");
  const [discard, setDiscard] = useState<{ proceed: () => void } | null>(null);
  const generationLock = useRef(false);
  const reviewLock = useRef(false);
  const importLock = useRef(false);
  const exportLock = useRef(false);
  const importFocus = useRef<HTMLElement | null>(null);
  const reviewFocus = useRef<HTMLElement | null>(null);
  const discardFocus = useRef<HTMLElement | null>(null);
  const navTrigger = useRef<HTMLButtonElement>(null);

  const batches = useResource("batches", listBatches);
  const batchList = batches.value?.batches ?? [];
  const batchId = selection.batchId ?? batchList[0]?.batch_id ?? null;
  const batch = useResource(batchId, getBatch);
  const status = batch.value?.status;
  const groups = batch.value?.groups ?? noGroups;
  const allMessages = groups.flatMap((group) => group.messages);
  const approved = allMessages.filter((message) => isExportable(message.draft)).length;
  const selected = allMessages.find((message) => message.id === selection.messageId) ?? null;
  const message = selection.view === "outbox" && selected && !isExportable(selected.draft) ? null : selected;
  const draft = useResource(message?.draft?.id ?? null, getDraft);
  const currentDraft = draft.value;
  const buffer = edit && edit.draftId === currentDraft?.id ? edit : null;
  const draftText = buffer?.text ?? currentDraft?.reply ?? "";
  const dirty = !!buffer && buffer.text !== (currentDraft?.reply ?? "");
  const conflict = dirty && buffer.revision !== currentDraft?.revision;
  const busyGeneration = job !== null || status?.status === "processing" || Boolean(status?.regenerating);
  const processingHere = job?.kind === "process" && job.batchId === batchId;
  const shouldPoll = job?.batchId === batchId || status?.status === "processing" || Boolean(status?.regenerating);
  const pollDraft = (job?.kind === "regenerate" && job.batchId === batchId) || Boolean(status?.regenerating);

  const { refresh: refreshBatch } = batch;
  const { refresh: refreshDraft } = draft;

  useEffect(() => {
    if (!shouldPoll || batchId === null) return;
    const timer = window.setInterval(() => { refreshBatch(); if (pollDraft) refreshDraft(); }, 2000);
    return () => window.clearInterval(timer);
  }, [batchId, shouldPoll, pollDraft, refreshBatch, refreshDraft]);

  useEffect(() => {
    const url = new URL(window.location.href);
    for (const [key, id] of [["batch", batchId], ["message", selection.messageId]] as const) {
      if (id === null) url.searchParams.delete(key);
      else url.searchParams.set(key, String(id));
    }
    if (selection.view === "outbox") url.searchParams.set("view", "outbox");
    else url.searchParams.delete("view");
    if (window.location.href !== url.href) window.history.replaceState(window.history.state, "", url);
  }, [batchId, selection.messageId, selection.view]);

  const visibleMessageId = message?.id;
  useEffect(() => {
    if (!visibleMessageId || !window.matchMedia("(max-width: 767px)").matches) return;
    document.getElementById("review-title")?.focus();
  }, [visibleMessageId]);

  useEffect(() => {
    if (!dirty) return;
    function warn(event: BeforeUnloadEvent) { event.preventDefault(); }
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const searchTerm = search.trim().toLocaleLowerCase();
  const filteredGroups = groups.filter((group) => selection.view === "outbox" || intent === "all" || intent === group.intent)
    .map((group) => ({ ...group, messages: group.messages.filter((candidate) => {
      if (selection.view === "outbox" && !isExportable(candidate.draft)) return false;
      return !searchTerm || `${candidate.candidate_name} ${candidate.source_id} ${candidate.message_text}`.toLocaleLowerCase().includes(searchTerm);
    }) })).filter((group) => group.messages.length);
  const visibleCount = filteredGroups.reduce((count, group) => count + group.messages.length, 0);

  function guardEdits(proceed: () => void) {
    if (!dirty) { proceed(); return; }
    discardFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setDiscard({ proceed });
  }

  function changeBatch(id: number) {
    setNavOpen(false);
    if (id === batchId) return;
    guardEdits(() => {
      setSelection({ batchId: id, messageId: null, view: "inbox" });
      setIntent("all"); setSearch(""); setEdit(null); setNotice(null);
    });
  }

  function changeView(view: View) {
    setNavOpen(false);
    if (view === selection.view) return;
    guardEdits(() => {
      setSelection({ batchId, messageId: null, view });
      setSearch(""); setEdit(null); setNotice(null);
    });
  }

  function selectIntent(next: Intent | "all") {
    setNavOpen(false);
    if (selection.view === "inbox") { setIntent(next); return; }
    guardEdits(() => {
      setSelection({ batchId, messageId: null, view: "inbox" });
      setIntent(next); setSearch(""); setEdit(null); setNotice(null);
    });
  }

  function selectMessage(candidate: CandidateMessage) {
    if (candidate.id === selection.messageId) return;
    guardEdits(() => {
      setSelection({ ...selection, batchId, messageId: candidate.id });
      setEdit(null); setNotice(null);
    });
  }

  function backToList() {
    guardEdits(() => {
      const id = selection.messageId;
      setSelection({ ...selection, batchId, messageId: null });
      setEdit(null); setNotice(null);
      window.requestAnimationFrame(() => document.getElementById(`candidate-${id}`)?.focus());
    });
  }

  function openImport() {
    importFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    guardEdits(() => {
      setEdit(null); setCsvFile(null); setImportError(""); setImportOpen(true);
    });
  }

  async function submitImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (importLock.current) return;
    if (!csvFile || csvFile.size === 0) { setImportError("Choose a non-empty CSV file."); return; }
    if (csvFile.size > maxCsvBytes) { setImportError("CSV exceeds the 1 MiB upload limit."); return; }
    importLock.current = true;
    setImportBusy(true); setImportError("");
    try {
      const receipt = await importBatch(csvFile);
      setSelection({ batchId: receipt.batch_id, messageId: null, view: "inbox" });
      setSearch(""); setIntent("all"); setImportOpen(false);
      batches.refresh(); refreshBatch();
      setNotice({ kind: "info", text: receipt.duplicate ? `Opened existing batch #${receipt.batch_id}.` :
        `Imported ${receipt.message_count} ${receipt.message_count === 1 ? "message" : "messages"}.` });
    } catch (error) {
      setImportError(readableError(error));
    } finally {
      importLock.current = false;
      setImportBusy(false);
    }
  }

  async function startProcessing() {
    if (batchId === null || generationLock.current || busyGeneration || batch.refreshing || batch.error) return;
    generationLock.current = true;
    setJob({ batchId, kind: "process" }); setNotice(null);
    try {
      const result = await processBatch(batchId);
      setNotice({ kind: "info", text: result.processing_failures ?
        `Batch #${batchId} was processed with ${result.processing_failures} ${result.processing_failures === 1 ? "failure" : "failures"}.` :
        `Processed ${result.processed} ${result.processed === 1 ? "message" : "messages"} in batch #${batchId}.` });
    } catch (error) {
      const disconnected = error instanceof ApiError && error.status === 0;
      setNotice({ kind: "error", text: disconnected ? "The processing request disconnected. Checking batch status before you retry." : readableError(error) });
    } finally {
      generationLock.current = false;
      setJob(null); refreshBatch(); refreshDraft();
    }
  }

  function updateText(text: string) {
    if (!currentDraft) return;
    setEdit(text === (currentDraft.reply ?? "") ? null : {
      draftId: currentDraft.id, revision: buffer?.revision ?? currentDraft.revision, text,
    });
  }

  async function submitReview(action: ReviewAction, target: Draft, values: { reply?: string; reason?: string } = {}) {
    if (reviewLock.current || (action === "regenerate" && (generationLock.current || busyGeneration))) return;
    reviewLock.current = true;
    if (action === "regenerate" && batchId !== null) {
      generationLock.current = true;
      setJob({ batchId, kind: "regenerate" });
    }
    setReviewBusy(true); setNotice(null);
    try {
      const updated = await reviewDraft(target.id, action, target.revision, values);
      draft.replace(target.id, updated);
      setEdit((previous) => previous?.draftId === target.id ? null : previous);
      const messages = { edit: "Saved a new revision for review.", approve: "Reply approved for export.",
        reject: "Reply rejected.", regenerate: "New revision ready for review." };
      setNotice({ kind: "info", text: messages[action] });
    } catch (error) {
      const changed = error instanceof ApiError && error.status === 409;
      setNotice({ kind: "error", text: changed ? `${readableError(error)} Refreshing the draft.` : readableError(error) });
      refreshDraft();
    } finally {
      reviewLock.current = false;
      if (action === "regenerate") { generationLock.current = false; setJob(null); }
      setReviewBusy(false); refreshBatch();
    }
  }

  function handleReview(action: ReviewAction) {
    if (!currentDraft || conflict || reviewLock.current) return;
    if (action === "edit" || action === "approve") {
      void submitReview(action, currentDraft, action === "edit" ? { reply: draftText.trim() } : {});
      return;
    }
    reviewFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setReason(""); setReviewDialog({ action, draft: currentDraft });
  }

  function confirmReview(event: FormEvent) {
    event.preventDefault();
    if (!reviewDialog) return;
    setReviewDialog(null);
    void submitReview(reviewDialog.action, reviewDialog.draft, reason.trim() ? { reason: reason.trim() } : {});
  }

  async function downloadExport() {
    if (batchId === null || !approved || exportLock.current) return;
    exportLock.current = true;
    setExporting(true); setNotice(null);
    try {
      const response = await exportBatch(batchId);
      const contents = await response.text();
      if (!contents.slice(contents.indexOf("\n") + 1).trim()) {
        setNotice({ kind: "info", text: "There are no eligible approved replies to export." });
        return;
      }
      const filename = /filename="(batch-\d+-approved\.csv)"/i.exec(response.headers.get("Content-Disposition") ?? "")?.[1]
        ?? `batch-${batchId}-approved.csv`;
      const url = URL.createObjectURL(new Blob([contents], { type: "text/csv;charset=utf-8" }));
      const link = document.createElement("a");
      link.href = url; link.download = filename;
      document.body.append(link); link.click(); link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setNotice({ kind: "info", text: "Approved replies exported." });
    } catch (error) {
      setNotice({ kind: "error", text: readableError(error) });
    } finally {
      exportLock.current = false;
      setExporting(false); refreshBatch();
    }
  }

  const sidebar = <Sidebar batches={batchList} batchId={batchId} groups={groups} intent={intent} view={selection.view}
    approved={approved} onBatch={changeBatch} onView={changeView} onIntent={selectIntent} />;
  const canProcess = status?.status === "imported" || status?.status === "interrupted";

  return <div className="workspace">
    <aside className="desktop-sidebar">
      <div className="brand"><span className="brand-mark"><ClipboardList size={18} aria-hidden="true" /></span>
        <div><strong>MUST</strong><span>Hiring inbox</span></div></div>
      {sidebar}
    </aside>

    <main className="workspace-main" aria-label="Hiring inbox workspace">
      <header className="topbar">
        <div className="breadcrumbs">
          <Button ref={navTrigger} variant="ghost" size="icon" className="navigation-toggle" aria-label="Open navigation" onClick={() => setNavOpen(true)}><Menu /></Button>
          <PanelLeft aria-hidden="true" className="desktop-top-icon" size={17} />
          <span className="workspace-label">Hiring inbox</span>
          {batchId !== null && <><span aria-hidden="true" className="slash">/</span><strong>Batch #{batchId}</strong></>}
        </div>
        <div className="top-actions">
          {selection.view === "outbox" ? <Button variant="outline" disabled={!approved || exporting || reviewBusy || batch.refreshing || Boolean(batch.error)} onClick={downloadExport}>
            {exporting ? <Loading /> : <ArrowDownToLine aria-hidden="true" />}<span>Export CSV</span>
          </Button> : canProcess && <Button disabled={busyGeneration || batch.refreshing || Boolean(batch.error)} onClick={startProcessing}>
            {processingHere ? <Loading /> : <RotateCw aria-hidden="true" />}<span>{status.status === "interrupted" ? "Resume" : "Process batch"}</span>
          </Button>}
          <Button variant="outline" onClick={openImport}><Plus aria-hidden="true" /><span>Import CSV</span></Button>
        </div>
      </header>

      {(batches.error || batch.error || notice) && <div className="workspace-notices">
        {batches.error ? <InlineError retry={batches.refresh}>{readableError(batches.error)}</InlineError> : null}
        {batch.error ? <InlineError retry={refreshBatch}>{readableError(batch.error)}</InlineError> : null}
        {notice?.kind === "error" && <InlineError>{notice.text}</InlineError>}
        {notice?.kind === "info" && <p className="notice info-notice" role="status">{notice.text}</p>}
      </div>}

      <div className="workspace-columns" data-review={!!message}>
        <div className="inbox-column">
          {status && <BatchProgress status={status} requested={processingHere} />}
          <InboxList view={selection.view} groups={filteredGroups} total={visibleCount} selected={message?.id ?? null}
            search={search} disabled={false} loading={batches.loading || batch.loading} hasBatch={batchId !== null}
            intent={intent} onSearch={setSearch} onSelect={selectMessage} />
        </div>
        {batchId === null && !batches.loading && !batches.error ?
          <section className="review-pane review-empty" aria-label="Getting started"><EmptyState title="Import your first batch"
            icon="file" action={<Button onClick={openImport}><Upload aria-hidden="true" />Import candidate messages</Button>}>
            Upload a CSV with a message ID, candidate name, and message text.
          </EmptyState></section> :
          <DraftReview message={message} draft={currentDraft} loading={draft.loading} error={draft.error} busy={reviewBusy || draft.refreshing}
            generationBusy={busyGeneration} draftText={draftText} dirty={dirty} conflict={conflict}
            onBack={backToList} onRefresh={refreshDraft} onText={updateText} onDiscard={() => setEdit(null)}
            onRebase={() => currentDraft && setEdit({ draftId: currentDraft.id, revision: currentDraft.revision, text: draftText })}
            onReview={handleReview} />}
      </div>
    </main>

    <Dialog open={navOpen} onOpenChange={setNavOpen}>
      <DialogContent className="nav-drawer" onCloseAutoFocus={(event) => { event.preventDefault(); navTrigger.current?.focus(); }}>
        <DialogTitle>Hiring inbox</DialogTitle>
        <DialogDescription className="sr-only">Choose a batch, view, or intent.</DialogDescription>
        {sidebar}
      </DialogContent>
    </Dialog>

    <Dialog open={importOpen} onOpenChange={(open) => { if (!importLock.current) setImportOpen(open); }}>
      <DialogContent onCloseAutoFocus={(event) => { event.preventDefault(); importFocus.current?.focus(); }}>
        <DialogTitle>Import CSV</DialogTitle>
        <DialogDescription>Use the columns message_id, candidate_name, and message_text. Up to 50 messages and 1 MiB.</DialogDescription>
        <form className="dialog-form" onSubmit={submitImport}>
          <label htmlFor="batch-file">Candidate CSV</label>
          <Input id="batch-file" type="file" accept=".csv,text/csv" disabled={importBusy} aria-invalid={Boolean(importError)}
            aria-describedby={importError ? "import-error" : undefined} onChange={(event) => { setCsvFile(event.target.files?.[0] ?? null); setImportError(""); }} />
          {importError && <InlineError><span id="import-error">{importError}</span></InlineError>}
          <div className="dialog-actions">
            <Button variant="outline" disabled={importBusy} onClick={() => setImportOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={importBusy}>{importBusy && <Loading />}Import batch</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>

    <Dialog open={reviewDialog !== null} onOpenChange={(open) => { if (!open) setReviewDialog(null); }}>
      <DialogContent onCloseAutoFocus={(event) => { event.preventDefault(); reviewFocus.current?.focus(); }}>
        <DialogTitle>{reviewDialog?.action === "reject" ? "Reject reply?" : "Regenerate draft?"}</DialogTitle>
        <DialogDescription>{reviewDialog?.action === "reject" ? "The current revision will be excluded from export." :
          "A new revision will replace the current draft and clear any approval." + (dirty ? " Your unsaved edit will be discarded when regeneration succeeds." : "")}</DialogDescription>
        <form className="dialog-form" onSubmit={confirmReview}>
          <label htmlFor="review-reason">Reason <span className="muted-text">(optional)</span></label>
          <Textarea id="review-reason" rows={3} maxLength={500} value={reason} onChange={(event) => setReason(event.target.value)} />
          <div className="dialog-actions">
            <Button variant="outline" onClick={() => setReviewDialog(null)}>Cancel</Button>
            <Button type="submit" variant={reviewDialog?.action === "reject" ? "destructive" : "default"}>
              {reviewDialog?.action === "reject" ? "Reject reply" : "Regenerate draft"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>

    <Dialog open={discard !== null} onOpenChange={(open) => { if (!open) setDiscard(null); }}>
      <DialogContent onCloseAutoFocus={(event) => {
        event.preventDefault();
        if (!importOpen) discardFocus.current?.focus();
      }}>
        <DialogTitle>Discard unsaved changes?</DialogTitle>
        <DialogDescription>Your edits have not been saved to the draft.</DialogDescription>
        <div className="dialog-actions">
          <Button variant="outline" onClick={() => setDiscard(null)}>Keep editing</Button>
          <Button variant="destructive" onClick={() => { setDiscard(null); discard?.proceed(); }}>Discard changes</Button>
        </div>
      </DialogContent>
    </Dialog>
  </div>;
}
