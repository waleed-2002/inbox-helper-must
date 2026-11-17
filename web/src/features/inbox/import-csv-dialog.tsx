import { useRef, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/fields";
import { importBatch, readableError, type ImportReceipt } from "./inbox-api";
import { InlineError, Loading } from "./workspace-parts";

const maxCsvBytes = 1_048_576;

type ImportCsvDialogProps = {
  open: boolean;
  onClose: () => void;
  onImported: (receipt: ImportReceipt) => void;
  onRestoreFocus: () => void;
};

export function ImportCsvDialog({ open, onClose, onImported, onRestoreFocus }: ImportCsvDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);

  function dismiss() {
    if (submitting.current) return;
    setFile(null);
    setError("");
    onClose();
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current) return;
    if (!file || file.size === 0) {
      setError("Choose a non-empty CSV file.");
      return;
    }
    if (file.size > maxCsvBytes) {
      setError("CSV exceeds the 1 MiB upload limit.");
      return;
    }
    submitting.current = true;
    setBusy(true);
    setError("");
    let receipt: ImportReceipt;
    try {
      receipt = await importBatch(file);
    } catch (error) {
      setError(readableError(error));
      return;
    } finally {
      submitting.current = false;
      setBusy(false);
    }
    setFile(null);
    onImported(receipt);
  }

  return <Dialog open={open} onOpenChange={(next) => { if (!next) dismiss(); }}>
    <DialogContent onCloseAutoFocus={(event) => { event.preventDefault(); onRestoreFocus(); }}>
      <DialogTitle>Import CSV</DialogTitle>
      <DialogDescription>Use the columns message_id, candidate_name, and message_text. Up to 50 messages and 1 MiB.</DialogDescription>
      <form className="dialog-form" onSubmit={submit}>
        <label htmlFor="batch-file">Candidate CSV</label>
        <Input id="batch-file" type="file" accept=".csv,text/csv" disabled={busy} aria-invalid={Boolean(error)}
          aria-describedby={error ? "import-error" : undefined} onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setError("");
          }} />
        {error && <InlineError><span id="import-error">{error}</span></InlineError>}
        <div className="dialog-actions">
          <Button variant="outline" disabled={busy} onClick={dismiss}>Cancel</Button>
          <Button type="submit" disabled={busy}>{busy && <Loading />}Import batch</Button>
        </div>
      </form>
    </DialogContent>
  </Dialog>;
}
