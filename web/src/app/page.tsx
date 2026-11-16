import { InboxWorkspace } from "@/components/inbox-workspace";

function validId(value: string | string[] | undefined) {
  if (typeof value !== "string" || !/^\d+$/.test(value)) return null;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
}

export default async function Home({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  return <InboxWorkspace initial={{
    batchId: validId(params.batch), messageId: validId(params.message),
    view: params.view === "outbox" ? "outbox" : "inbox",
  }} />;
}
