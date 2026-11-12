"use client";

import { track } from "@/lib/analytics";
import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import QRCode from "qrcode";
import { useCallback, useEffect, useRef, useState } from "react";
import { SlideView } from "@/components/presentation/slide-view";
import { Button } from "@/components/ui/button";
import type { Shape } from "@/components/video/shapes";
import { api } from "@/lib/client";

type Command = { action: string; slide?: number; shapes?: Shape[]; sent_at?: string };

/** Full-screen presentation with presenter view and phone remote (addendum 01, 4.1). */
export function Presenter({ orgId, presId }: { orgId: string; presId: string }) {
  const t = useTranslations("presentations");
  const ts = useTranslations("scouting");
  const path = { org_id: orgId, pres_id: presId };
  const q = useQuery({
    queryKey: ["presentation", presId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/presentations/{pres_id}", { params: { path } })).data ?? null,
  });
  const slides = q.data?.slide_list ?? [];
  const [i, setI] = useState(0);
  const [paused, setPaused] = useState(false);
  const [presenterView, setPresenterView] = useState(true);
  const [remoteShapes, setRemoteShapes] = useState<Shape[]>([]);
  const [qr, setQr] = useState<string | null>(null);
  const [remoteUrl, setRemoteUrl] = useState<string | null>(null);
  const [latency, setLatency] = useState<number | null>(null);
  const [started] = useState(() => Date.now());
  const [now, setNow] = useState(Date.now());
  const stage = useRef<HTMLDivElement>(null);
  useEffect(() => track("presentation_held"), []);
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const total = q.data?.slide_list.length ?? 0;
  const go = useCallback(
    (n: number) => {
      setI(Math.max(0, Math.min(n, total - 1)));
      setPaused(false);
      setRemoteShapes([]);
    },
    [total],
  );

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowRight" || e.key === "PageDown") go(i + 1);
      else if (e.key === "ArrowLeft" || e.key === "PageUp") go(i - 1);
      else if (e.key === " ") {
        e.preventDefault();
        setPaused((p) => !p);
      } else if (e.key.toLowerCase() === "p") setPresenterView((v) => !v);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [i, go]);

  const pair = useMutation({
    mutationFn: async () => (await api.POST("/v1/orgs/{org_id}/presentations/{pres_id}/remote", { params: { path } })).data,
    onSuccess: async (d) => {
      if (!d) return;
      const url = `${window.location.origin}/app/${orgId}/presentations/${presId}/remote?k=${d.key}`;
      setQr(await QRCode.toDataURL(url, { margin: 1, width: 220 }));
      setRemoteUrl(url);
      const es = new EventSource(`/v1/orgs/${orgId}/presentations/${presId}/remote/stream?key=${d.key}`);
      es.addEventListener("command", (e) => {
        const c = JSON.parse((e as MessageEvent).data) as Command;
        if (c.sent_at) setLatency(Date.now() - new Date(c.sent_at).getTime());
        if (c.action === "next") setI((n) => Math.min(n + 1, slides.length - 1));
        else if (c.action === "prev") setI((n) => Math.max(n - 1, 0));
        else if (c.action === "goto" && c.slide != null) setI(c.slide);
        else if (c.action === "pause") setPaused(true);
        else if (c.action === "play") setPaused(false);
        else if (c.action === "draw") setRemoteShapes((s) => [...s, ...(c.shapes ?? [])]);
        else if (c.action === "clear") setRemoteShapes([]);
      });
    },
  });

  const slide = slides[i];
  const next = slides[i + 1];
  const notes = (slide?.content as { notes?: string } | undefined)?.notes;
  const obsText = (o: Record<string, unknown>) => {
    const p = (o.params ?? {}) as Record<string, string | number>;
    const pct = (v: unknown) => (typeof v === "number" ? `${Math.round(v * 100)} %` : "-");
    return ts(`obs_${String(o.key)}` as "obs_top_shooter", { ...p, share: pct(p.share), pct: pct(p.pct) });
  };
  const mins = Math.floor((now - started) / 60000);

  if (!q.data) return <p className="text-muted">…</p>;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Link href={`/app/${orgId}/presentations/${presId}`} className="text-sm font-medium text-accent hover:underline">
          {t("back")}
        </Link>
        <span className="flex-1 font-semibold">{q.data.title}</span>
        <Button variant="secondary" onClick={() => void stage.current?.requestFullscreen?.()}>
          {t("fullscreen")}
        </Button>
        <Button variant="secondary" onClick={() => setPresenterView((v) => !v)} aria-pressed={presenterView}>
          {t("presenterView")}
        </Button>
        <Button variant="secondary" loading={pair.isPending} onClick={() => pair.mutate()}>
          {t("remote")}
        </Button>
      </div>
      <div className={presenterView ? "grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]" : ""}>
        <div ref={stage} className="relative bg-raised" data-testid="stage" aria-live="polite">
          {slide ? (
            <SlideView orgId={orgId} slide={slide} paused={paused} extraShapes={remoteShapes} observationText={obsText} />
          ) : (
            <p className="p-8 text-muted">{t("noSlides")}</p>
          )}
        </div>
        {presenterView && (
          <aside className="space-y-3 text-sm" aria-label={t("presenterView")}>
            <p className="tabular-nums" data-testid="slide-counter">
              {t("slideN", { n: i + 1, total: slides.length })} · {t("minutes", { n: mins })}
            </p>
            <div>
              <p className="font-medium">{t("notes")}</p>
              <p className="whitespace-pre-line text-muted">{notes || t("noNotes")}</p>
            </div>
            <div>
              <p className="font-medium">{t("nextSlide")}</p>
              <p className="text-muted">{next ? t(`type_${next.type}` as "type_clip") + ((next.content as { title?: string }).title ? `: ${(next.content as { title?: string }).title}` : "") : t("end")}</p>
            </div>
            {qr && (
              <div className="space-y-1">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={qr} alt={t("qrAlt")} width={160} height={160} />
                <p className="text-xs text-muted">{t("qrHint")}</p>
                {remoteUrl && (
                  <a href={remoteUrl} target="_blank" rel="noreferrer" className="text-xs font-medium text-accent hover:underline" data-testid="remote-link">
                    {t("remoteLink")}
                  </a>
                )}
                {latency != null && <p className="text-xs text-muted">{t("latency", { ms: latency })}</p>}
              </div>
            )}
          </aside>
        )}
      </div>
      <div className="flex justify-between">
        <Button variant="secondary" disabled={i === 0} onClick={() => go(i - 1)}>
          {t("prev")}
        </Button>
        <Button variant="secondary" onClick={() => setPaused((p) => !p)}>
          {paused ? t("play") : t("pause")}
        </Button>
        <Button variant="secondary" disabled={i >= slides.length - 1} onClick={() => go(i + 1)}>
          {t("next")}
        </Button>
      </div>
    </div>
  );
}
