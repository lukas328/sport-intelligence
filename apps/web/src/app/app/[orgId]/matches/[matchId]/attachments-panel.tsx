"use client";

import { problemCode, type Schemas } from "@handball/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileText, Paperclip, Trash2 } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { useId, useRef, useState, type FormEvent } from "react";
import { SectionHead } from "@/components/anlauf/blocks";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { useConfirm } from "@/components/ui/confirm";
import { control } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { formatBytes } from "@/lib/format";
import { xhrPutPart } from "@/lib/upload";
import { cn } from "@/lib/utils";

type Attachment = Schemas["AttachmentOut"];

const MAX = 25 * 1024 * 1024;
const BY_EXT: Record<string, string> = { pdf: "application/pdf", jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", webp: "image/webp", heic: "image/heic", heif: "image/heif" };

/** The type to send: the browser's, or from the ending (HEIC photos often come without one). */
export function attachmentType(file: { name: string; type: string }): string | null {
  if (Object.values(BY_EXT).includes(file.type)) return file.type;
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  return BY_EXT[ext] ?? null;
}

/**
 * «Dateien zum Spiel» (K19): the photo or PDF of the paper report, own notes, kept with the match
 * and found again here. Nothing is read out of them; the official report of handball.ch comes in
 * by itself after the game (said here when the team is linked).
 */
export function AttachmentsPanel({ orgId, matchId, staff, hasReport, linked }: { orgId: string; matchId: string; staff: boolean; hasReport: boolean; linked: boolean }) {
  const t = useTranslations("attachments");
  const tr = useTranslations();
  const format = useFormatter();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const key = ["attachments", matchId];
  const list = useQuery({
    queryKey: key,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/attachments", { params: { path: { org_id: orgId, match_id: matchId } } })).data ?? [],
  });
  const fileRef = useRef<HTMLInputElement>(null);
  const noteId = useId();
  const [file, setFile] = useState<File | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<ErrorKey | "type" | "size" | "upload" | "many" | null>(null);
  // the API's refusals in the words of this panel
  const said = (problem: unknown) => {
    const code = problemCode(problem);
    if (code === "unsupported-file") return setError("type");
    if (code === "file-too-large") return setError("size");
    if (code === "too-many-files") return setError("many");
    if (code === "incomplete-upload") return setError("upload");
    return setError(errorKey(problem));
  };
  const items = list.data ?? [];
  const url = (a: Attachment, download = false) => `/v1/orgs/${orgId}/attachments/${a.id}/file${download ? "?download=true" : ""}`;

  async function add(e: FormEvent) {
    e.preventDefault();
    if (!file) return fileRef.current?.click();
    const type = attachmentType(file);
    if (!type) return setError("type");
    if (file.size > MAX) return setError("size");
    setError(null);
    setBusy(0);
    const created = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/attachments", {
      params: { path: { org_id: orgId, match_id: matchId } },
      body: { filename: file.name, content_type: type, size_bytes: file.size, note: note.trim() || null },
    });
    if (created.error || !created.data) {
      setBusy(null);
      return said(created.error);
    }
    try {
      const etag = await xhrPutPart(created.data.upload_url, file, new AbortController().signal);
      setBusy(90);
      const done = await api.POST("/v1/orgs/{org_id}/attachments/{attachment_id}/complete", {
        params: { path: { org_id: orgId, attachment_id: created.data.attachment.id } },
        body: { etag },
      });
      if (done.error) {
        setBusy(null);
        return said(done.error);
      }
    } catch {
      setBusy(null);
      return setError("upload");
    }
    setBusy(null);
    setFile(null);
    setNote("");
    if (fileRef.current) fileRef.current.value = "";
    await qc.invalidateQueries({ queryKey: key });
  }

  async function remove(a: Attachment) {
    if (!(await confirm({ title: t("deleteTitle"), body: t("deleteBody", { name: a.filename }), confirm: tr("common.delete"), danger: true }))) return;
    await api.DELETE("/v1/orgs/{org_id}/attachments/{attachment_id}", { params: { path: { org_id: orgId, attachment_id: a.id } } });
    await qc.invalidateQueries({ queryKey: key });
  }

  // a player sees the files, if there are any; nothing to say otherwise
  if (!staff && items.length === 0) return null;
  return (
    <section id="attachments" className="scroll-mt-24" aria-labelledby="attachments-title" data-testid="attachments">
      <SectionHead title={<span id="attachments-title">{t("title")}</span>} note={items.length > 0 ? t("count", { n: items.length }) : undefined} />
      {/* the official report needs no file: it comes by itself (K19) */}
      {(hasReport || linked) && <p className="m-0 mb-3 max-w-[62ch] text-[15px] text-ink-2" data-testid="official-auto">{t(hasReport ? "officialThere" : "officialComes")}</p>}
      {items.length > 0 && (
        <ul className="m-0 mb-5 list-none border-t border-rule p-0">
          {items.map((a) => (
            <li key={a.id} className="grid grid-cols-[56px_minmax(0,1fr)] items-start gap-3 border-b border-rule py-3 sm:grid-cols-[56px_minmax(0,1fr)_auto]" data-testid="attachment">
              <a href={url(a)} target="_blank" rel="noreferrer" className="block size-14 overflow-hidden bg-surface" aria-label={t("open", { name: a.filename })}>
                {a.is_image ? (
                  // eslint-disable-next-line @next/next/no-img-element -- a private file of the API, not an optimisable asset
                  <img src={url(a)} alt="" className="size-full object-cover" loading="lazy" />
                ) : (
                  <span className="grid size-full place-items-center">
                    <FileText aria-hidden className="size-7" />
                  </span>
                )}
              </a>
              <div className="min-w-0">
                <a href={url(a)} target="_blank" rel="noreferrer" className="block truncate text-[17px] font-bold text-ink underline decoration-[1.5px] underline-offset-4">
                  {a.filename}
                </a>
                {a.note && <p className="m-0 mt-0.5 text-[15px] whitespace-pre-line">{a.note}</p>}
                <p className="m-0 mt-0.5 text-sm text-ink-2">
                  {[formatBytes(a.size_bytes), format.dateTime(new Date(a.created_at), { day: "numeric", month: "numeric", year: "numeric" }), a.created_by].filter(Boolean).join(" · ")}
                </p>
              </div>
              <div className="col-span-2 flex flex-wrap gap-2 sm:col-span-1">
                <a href={url(a, true)} className="inline-flex min-h-11 items-center gap-1.5 px-2 text-[15px] font-bold text-ink" download>
                  <Download aria-hidden className="size-4" />
                  {t("download")}
                </a>
                {staff && (
                  <button type="button" onClick={() => void remove(a)} className="inline-flex min-h-11 cursor-pointer items-center gap-1.5 border-0 bg-transparent px-2 text-[15px] font-bold text-loss" aria-label={t("deleteNamed", { name: a.filename })}>
                    <Trash2 aria-hidden className="size-4" />
                    {tr("common.delete")}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      {staff && (
        <form onSubmit={add} className="max-w-xl space-y-3" aria-label={t("add")}>
          {items.length === 0 && <p className="m-0 text-[15px]">{t("empty")}</p>}
          <label className={cn("flex min-h-14 cursor-pointer items-center gap-3 border-2 border-dashed border-ink px-4 py-3 text-[17px] font-bold", file && "border-solid")}>
            <Paperclip aria-hidden className="size-5 shrink-0" />
            <span className="min-w-0 truncate">{file ? `${file.name} (${formatBytes(file.size)})` : t("choose")}</span>
            <input
              ref={fileRef}
              type="file"
              accept="image/*,application/pdf,.heic,.heif,.pdf"
              className="sr-only"
              data-testid="attachment-file"
              onChange={(e) => {
                setError(null);
                setFile(e.target.files?.[0] ?? null);
              }}
            />
          </label>
          {file && (
            <div className="space-y-1">
              <label htmlFor={noteId} className="block text-sm font-semibold">
                {t("note")}
              </label>
              <textarea id={noteId} value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000} rows={2} className={control} placeholder={t("notePlaceholder")} />
            </div>
          )}
          <p className="m-0 text-sm text-ink-2">{t("limits")}</p>
          {error && <Alert>{error === "type" ? t("errorType") : error === "size" ? t("errorSize") : error === "upload" ? t("errorUpload") : error === "many" ? t("errorMany") : tr(`errors.${error}`)}</Alert>}
          {file && (
            <Button type="submit" loading={busy != null}>
              {t("add")}
            </Button>
          )}
        </form>
      )}
    </section>
  );
}
