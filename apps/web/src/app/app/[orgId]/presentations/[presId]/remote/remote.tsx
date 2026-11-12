"use client";

import { useTranslations } from "next-intl";
import { useRef, useState, type PointerEvent } from "react";
import { Alert } from "@/components/ui/card";
import type { Shape } from "@/components/video/shapes";
import { api } from "@/lib/client";

/** Phone remote: next, back, pause and drawing on the phone (addendum 01, 4.1). */
export function Remote({ orgId, presId, pairKey }: { orgId: string; presId: string; pairKey: string }) {
  const t = useTranslations("presentations");
  const [sent, setSent] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const pad = useRef<SVGSVGElement>(null);
  const [stroke, setStroke] = useState<[number, number][]>([]);
  async function send(action: "next" | "prev" | "play" | "pause" | "draw" | "clear", shapes?: Shape[]) {
    const r = await api.POST("/v1/orgs/{org_id}/presentations/{pres_id}/remote/command", {
      params: { path: { org_id: orgId, pres_id: presId } },
      body: { key: pairKey, action, ...(shapes ? { shapes: shapes as never } : {}) },
    });
    setFailed(Boolean(r.error));
    setSent(action);
  }
  function point(e: PointerEvent<SVGSVGElement>): [number, number] {
    const r = pad.current!.getBoundingClientRect();
    return [Math.round(((e.clientX - r.left) / r.width) * 1000) / 1000, Math.round(((e.clientY - r.top) / r.height) * 1000) / 1000];
  }
  if (!pairKey) return <Alert>{t("remoteMissing")}</Alert>;
  const big = "min-h-20 border border-border text-xl font-semibold active:bg-surface";
  return (
    <div className="mx-auto max-w-md space-y-4">
      <h1 className="text-xl font-semibold">{t("remote")}</h1>
      {failed && <Alert>{t("remoteFailed")}</Alert>}
      <div className="grid grid-cols-2 gap-3">
        <button type="button" className={big} onClick={() => void send("prev")}>
          {t("prev")}
        </button>
        <button type="button" className={big} onClick={() => void send("next")}>
          {t("next")}
        </button>
        <button type="button" className={big} onClick={() => void send("pause")}>
          {t("pause")}
        </button>
        <button type="button" className={big} onClick={() => void send("play")}>
          {t("play")}
        </button>
      </div>
      <p className="text-sm font-medium">{t("drawHere")}</p>
      <svg
        ref={pad}
        viewBox="0 0 1000 562"
        className="aspect-video w-full touch-none bg-raised border border-border bg-surface"
        role="img"
        aria-label={t("drawHere")}
        onPointerDown={(e) => setStroke([point(e)])}
        onPointerMove={(e) => stroke.length && setStroke((s) => [...s, point(e)])}
        onPointerUp={() => {
          if (stroke.length > 1) void send("draw", [{ kind: "freehand", points: stroke, color: "#facc15", width: 6 }]);
          setStroke([]);
        }}
      >
        <polyline points={stroke.map(([x, y]) => `${x * 1000},${y * 562}`).join(" ")} fill="none" stroke="#facc15" strokeWidth={6} />
      </svg>
      <button type="button" className="w-full ring-1 ring-inset ring-border py-2" onClick={() => void send("clear")}>
        {t("clear")}
      </button>
      {sent && (
        <p role="status" className="text-sm text-muted" data-testid="remote-sent">
          {t("sent", { action: t(sent as "next") })}
        </p>
      )}
    </div>
  );
}
