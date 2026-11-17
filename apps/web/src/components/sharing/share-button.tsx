"use client";

import { Check, Copy, Download, Image as ImageIcon, MessageCircle, Share2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useFormatter, useTranslations } from "next-intl";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Button, buttonClass, type ButtonVariant } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { control } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey } from "@/lib/errors";
import { blockedReason, DEFAULT_DAYS, EXPIRY_DAYS, liveLink, reasonFromProblem, type ShareOptions, type ShareReason } from "@/lib/share/policy";
import { chatText, shareUrl, whatsappHref, type ShareInfo, type ShareKind, type T } from "@/lib/share/text";
import { cn } from "@/lib/utils";

interface Link {
  id: string;
  kind: string;
  target_id: string;
  expires_at: string;
  revoked_at?: string | null;
  views: number;
  token?: string | null;
}

/**
 * Teilen (K20, R2): one share action everywhere (scene, collection, playlist, highlights, play,
 * match report). It asks first what may be shared and explains the youth and consent rules
 * instead of failing; offers a link that still works instead of a second one; and then the
 * native share sheet with a prepared chat text, «In WhatsApp teilen», «Link kopieren», how long
 * the link lives, how often it was opened and «Link sperren». For a match it also offers the
 * Spielkarte as a picture.
 */
export function ShareButton({
  orgId,
  teamId,
  kind,
  targetId,
  matchId,
  label,
  variant = "secondary",
  open: controlled,
  onOpenChange,
  trigger,
  info,
}: {
  orgId: string;
  teamId: string;
  kind: ShareKind;
  targetId: string;
  /** what the page already knows (title, opponent, score): the chat text stands at once */
  info?: Omit<ShareInfo, "kind">;
  /** the match of a match report: offers the Spielkarte too */
  matchId?: string;
  label?: string;
  variant?: ButtonVariant;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  /** a trigger of its own; null: opened from outside only */
  trigger?: ReactNode | null;
}) {
  const t = useTranslations("share");
  const [own, setOwn] = useState(false);
  const open = controlled ?? own;
  const setOpen = (o: boolean) => (onOpenChange ? onOpenChange(o) : setOwn(o));
  return (
    <Dialog
      open={open}
      onOpenChange={setOpen}
      title={t("dialogTitle", { kind })}
      description={t("hintShort")}
      trigger={
        trigger === undefined ? (
          <Button variant={variant} data-testid="share-open">
            <Share2 aria-hidden />
            <span>{label ?? t("button")}</span>
          </Button>
        ) : (
          trigger
        )
      }
    >
      {open && <SharePanel orgId={orgId} teamId={teamId} kind={kind} targetId={targetId} matchId={matchId ?? (kind === "match" ? targetId : undefined)} info={info} />}
    </Dialog>
  );
}

function SharePanel({ orgId, teamId, kind, targetId, matchId, info }: { orgId: string; teamId: string; kind: ShareKind; targetId: string; matchId?: string | undefined; info?: Omit<ShareInfo, "kind"> | undefined }) {
  const t = useTranslations("share");
  const te = useTranslations("errors");
  const router = useRouter();
  const [state, setState] = useState<"loading" | "choose" | "ready" | "blocked">("loading");
  const [options, setOptions] = useState<ShareOptions | null>(null);
  const [link, setLink] = useState<Link | null>(null);
  const [reused, setReused] = useState(false);
  const [reason, setReason] = useState<ShareReason | null>(null);
  const [days, setDays] = useState(DEFAULT_DAYS);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [said, setSaid] = useState<string | null>(null);
  const path = { org_id: orgId, team_id: teamId };

  useEffect(() => {
    let live = true;
    void (async () => {
      const [opts, links] = await Promise.all([
        api.GET("/v1/orgs/{org_id}/teams/{team_id}/share-options", { params: { path } }),
        api.GET("/v1/orgs/{org_id}/teams/{team_id}/share-links", { params: { path } }),
      ]);
      if (!live) return;
      const o = (opts.data as ShareOptions | undefined) ?? null;
      setOptions(o);
      setDays(o?.default_days ?? DEFAULT_DAYS);
      const existing = liveLink((links.data ?? []) as Link[], kind, targetId);
      const blocked = blockedReason(o, kind);
      if (existing && !blocked) {
        setLink(existing);
        setReused(true);
        setState("ready");
      } else if (blocked) {
        setReason(blocked);
        setState("blocked");
      } else setState("choose");
    })();
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once per opening
  }, []);

  async function create() {
    setBusy(true);
    setError(null);
    const { data, error: err } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/share-links", { params: { path }, body: { kind, target_id: targetId, days } });
    setBusy(false);
    if (err || !data) {
      const r = reasonFromProblem(err);
      if (r) {
        setReason(r);
        setState("blocked");
      } else setError(te(errorKey(err)));
      return;
    }
    setLink(data as Link);
    setReused(false);
    setSaid(null);
    setState("ready");
    // the page's own «Teilen» side shows the new link at once (UX test B17)
    router.refresh();
  }

  async function revoke() {
    if (!link) return;
    setBusy(true);
    await api.DELETE("/v1/orgs/{org_id}/share-links/{link_id}", { params: { path: { org_id: orgId, link_id: link.id } } });
    setBusy(false);
    setLink(null);
    setSaid(t("revoked"));
    setState("choose");
    router.refresh();
  }

  return (
    <div className="space-y-5" data-testid="share-panel">
      {state === "loading" && (
        <p className="text-[15px] text-ink-2" role="status">
          {t("loading")}
        </p>
      )}
      {state === "blocked" && reason && (
        <Alert kind="info" data-testid="share-blocked">
          {t(`reason.${reason}`)}
          {reason === "youth-protection" && matchId && <span className="mt-1 block">{t("reason.youthCard")}</span>}
          {/* the way to the confirmation, not only that it is missing (review R21) */}
          {reason === "unverified" && (
            <a href={`/app/${orgId}/club/federation`} className="mt-1 block font-bold text-ink underline underline-offset-4" data-testid="share-verify">
              {t("reason.unverifiedLink")}
            </a>
          )}
        </Alert>
      )}
      {state === "choose" && (
        <div className="space-y-4">
          <fieldset>
            <legend className="mb-2 text-[0.9375rem] font-semibold">{t("validFor")}</legend>
            <div className="flex flex-wrap gap-2">
              {EXPIRY_DAYS.map((d) => (
                <label key={d} className={cn("inline-flex min-h-11 cursor-pointer items-center border-2 px-3.5 text-[15px] font-bold has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-ink", days === d ? "border-ink bg-ink text-ground" : "border-ink text-ink hover:bg-ink/5")}>
                  <input type="radio" name="share-days" value={d} checked={days === d} onChange={() => setDays(d)} className="sr-only" />
                  {t("days", { count: d })}
                </label>
              ))}
            </div>
          </fieldset>
          <Button onClick={() => void create()} loading={busy} data-testid="share-create-link">
            {t("create")}
          </Button>
        </div>
      )}
      {state === "ready" && link?.token && (
        <ReadyLink link={link} kind={kind} info={info} reused={reused} busy={busy} onRevoke={() => void revoke()} />
      )}
      {said && (
        <p role="status" className="text-[15px] text-ink-2">
          {said}
        </p>
      )}
      {error && <Alert>{error}</Alert>}
      {matchId && options !== null && <MatchCardShare orgId={orgId} matchId={matchId} />}
      {state !== "loading" && state !== "blocked" && <p className="text-[15px] text-ink-2">{t("tip", { kind })}</p>}
    </div>
  );
}

function ReadyLink({ link, kind, info, reused, busy, onRevoke }: { link: Link; kind: ShareKind; info?: Omit<ShareInfo, "kind"> | undefined; reused: boolean; busy: boolean; onRevoke: () => void }) {
  const t = useTranslations("share");
  const root = useTranslations() as unknown as T;
  const format = useFormatter();
  const url = shareUrl(window.location.origin, link.token!);
  // at once from what the page knows; the preview of the link (what the chat will show) refines
  // it, unless the coach has started to write
  const [text, setText] = useState<string>(() => (info?.title || info?.opponent ? chatText(root, { kind, ...info }) : ""));
  const edited = useRef(false);
  useEffect(() => {
    let live = true;
    void api.GET("/v1/share/{token}/preview", { params: { path: { token: link.token! } } }).then(({ data }) => {
      if (!live || edited.current || !data) return;
      setText(
        chatText(root, {
          kind,
          title: data?.title ?? "",
          team: data ? [data.club, data.team].filter((x, i, a) => x && a.indexOf(x) === i).join(" ") : null,
          opponent: data?.opponent ?? null,
          score: data?.score ?? null,
          scenes: data?.scenes ?? null,
        }),
      );
    });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once per link
  }, [link.token]);
  return (
    <div className="space-y-4">
      {reused && <p className="text-[15px] text-ink-2">{t("already")}</p>}
      <label className="flex flex-col gap-1 text-[0.9375rem] font-semibold">
        {t("linkLabel")}
        <input readOnly value={url} onFocus={(e) => e.currentTarget.select()} className={cn(control, "font-mono text-xs")} data-testid="share-url" />
      </label>
      <label className="flex flex-col gap-1 text-[0.9375rem] font-semibold">
        {t("textLabel")}
        <textarea value={text} onChange={(e) => ((edited.current = true), setText(e.target.value))} rows={2} className={cn(control, "min-h-[4.5rem] resize-y py-2 font-normal")} data-testid="share-text" />
      </label>
      <ShareActions url={url} text={text} />
      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[15px] text-ink-2" data-testid="share-status">
        <span>{t("status", { date: format.dateTime(new Date(link.expires_at), { day: "numeric", month: "long" }), views: link.views })}</span>
        <Button size="sm" variant="quiet" loading={busy} onClick={onRevoke} data-testid="share-revoke-link">
          {t("revoke")}
        </Button>
      </p>
    </div>
  );
}

/**
 * The three ways into the chat: the phone's share sheet (where there is one), WhatsApp with the
 * text filled in, and the link on the clipboard.
 */
export function ShareActions({ url, text, compact = false }: { url: string; text: string; compact?: boolean }) {
  const t = useTranslations("share");
  const [copied, setCopied] = useState<"ok" | "failed" | null>(null);
  const [native, setNative] = useState(false);
  useEffect(() => setNative(typeof navigator !== "undefined" && typeof navigator.share === "function"), []);
  const message = text.trim() ? `${text.trim()}\n${url}` : url;
  const size = compact ? "sm" : "md";
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2.5">
        {native && (
          <Button
            size={size}
            onClick={async () => {
              try {
                await navigator.share({ text: text.trim() || undefined, url });
              } catch {
                /* closed without sharing */
              }
            }}
            data-testid="share-native"
          >
            <Share2 aria-hidden />
            {t("native")}
          </Button>
        )}
        <a href={whatsappHref(message)} target="_blank" rel="noopener noreferrer" className={buttonClass(native ? "secondary" : "primary", size)} data-testid="share-whatsapp">
          <MessageCircle aria-hidden />
          {t("whatsapp")}
        </a>
        <Button
          size={size}
          variant="secondary"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(url);
              setCopied("ok");
            } catch {
              setCopied("failed");
            }
          }}
          data-testid="share-copy-link"
        >
          {copied === "ok" ? <Check aria-hidden /> : <Copy aria-hidden />}
          {copied === "ok" ? t("copiedLink") : t("copyLink")}
        </Button>
      </div>
      <p role="status" className={cn("text-[15px] text-ink-2", !copied && "sr-only")}>
        {copied === "ok" ? t("copiedLink") : copied === "failed" ? t("copyFailed") : ""}
      </p>
    </div>
  );
}

/** Shares a picture through the share sheet (straight into the chat), else saves it. */
export async function shareImage(src: string, fileName: string, text?: string): Promise<"shared" | "saved" | "failed"> {
  try {
    const res = await fetch(src, { credentials: "same-origin" });
    if (!res.ok) return "failed";
    const blob = await res.blob();
    const file = new File([blob], fileName, { type: "image/png" });
    if (typeof navigator.canShare === "function" && navigator.canShare({ files: [file] })) {
      try {
        await navigator.share({ files: [file], ...(text ? { text } : {}) });
        return "shared";
      } catch (e) {
        if ((e as Error).name === "AbortError") return "shared";
      }
    }
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = fileName;
    a.click();
    window.setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    return "saved";
  } catch {
    return "failed";
  }
}

/** The Spielkarte in the share dialog: a small look at it, «Bild teilen», «Bild speichern». */
export function MatchCardShare({ orgId, matchId }: { orgId: string; matchId: string }) {
  const t = useTranslations("share");
  const src = matchCardSrc(orgId, matchId);
  const [state, setState] = useState<"loading" | "ok" | "none">("loading");
  const [busy, setBusy] = useState(false);
  const [canShare, setCanShare] = useState(false);
  useEffect(() => setCanShare(typeof navigator !== "undefined" && typeof navigator.canShare === "function"), []);
  if (state === "none") return null;
  return (
    <section className="border-t border-rule pt-4" aria-labelledby="card-title" data-testid="match-card-share">
      <h3 id="card-title" className="font-slant text-xl">
        {t("card.title")}
      </h3>
      <div className="mt-2 flex flex-wrap items-start gap-4">
        {/* eslint-disable-next-line @next/next/no-img-element -- a picture made on the server for this match */}
        <img src={src} alt={t("card.title")} width={128} height={128} className={cn("size-32 border border-rule bg-surface", state === "loading" && "animate-pulse")} onLoad={() => setState("ok")} onError={() => setState("none")} />
        <div className="min-w-0 flex-1 space-y-2">
          <p className="text-[15px] text-ink-2">{t("card.hint")}</p>
          <div className="flex flex-wrap gap-2">
            {canShare && (
              <Button size="sm" loading={busy} onClick={async () => (setBusy(true), await shareImage(src, `${t("card.file")}.png`), setBusy(false))} data-testid="card-share">
                <ImageIcon aria-hidden />
                {t("card.share")}
              </Button>
            )}
            <a href={`${src}?download=1`} download className={buttonClass("secondary", "sm")} data-testid="card-save">
              <Download aria-hidden />
              {t("card.save")}
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

export function matchCardSrc(orgId: string, matchId: string): string {
  return `/app/${orgId}/matches/${matchId}/spielkarte`;
}

/** Shares the Spielkarte of a match straight away (the «Als Bild für den Chat» action). */
export function shareMatchCard(orgId: string, matchId: string, fileName: string): Promise<"shared" | "saved" | "failed"> {
  return shareImage(matchCardSrc(orgId, matchId), fileName);
}
