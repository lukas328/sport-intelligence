"use client";

import type { Schemas } from "@handball/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";

type Video = Schemas["VideoOut"];

/** The camera switch (M5) under the picture, with the sync offset of the other cameras. */
export function CameraSwitch({
  orgId,
  cams,
  active,
  staff,
  onSwitch,
}: {
  orgId: string;
  cams: Video[];
  active: Video;
  staff: boolean;
  onSwitch: (id: string) => void;
}) {
  const t = useTranslations("camera");
  const qc = useQueryClient();
  const sync = active.sync;
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm" data-testid="camera-switch">
      <span className="font-medium">{t("label")}:</span>
      <div role="group" aria-label={t("label")} className="flex flex-wrap gap-1">
        {cams.map((c) => (
          <button
            key={c.id}
            aria-pressed={c.id === active.id}
            onClick={() => onSwitch(c.id)}
            className={cn("border px-2 py-1", c.id === active.id ? "border-foreground bg-foreground text-background" : "border-border bg-raised hover:bg-surface")}
          >
            {t(c.role)}
          </button>
        ))}
      </div>
      {active.role !== "main" && sync?.source === "audio" && sync.applied && (
        <span className="text-xs text-muted">{t("synced", { confidence: Math.round((sync.confidence ?? 0) * 100) })}</span>
      )}
      {active.role !== "main" && sync?.source === "user_correction" && <span className="text-xs text-muted">{t("manual")}</span>}
      {active.role !== "main" && (!sync || (sync.source === "audio" && !sync.applied)) && (
        <span className="text-xs text-accent">{t("syncLow")}</span>
      )}
      {staff && active.role !== "main" && (
        <form
          className="flex items-end gap-1"
          onSubmit={async (e) => {
            e.preventDefault();
            const form = e.currentTarget;
            const value = Number(new FormData(form).get("offset"));
            await api.PATCH("/v1/orgs/{org_id}/videos/{video_id}", {
              params: { path: { org_id: orgId, video_id: active.id } },
              body: { time_offset_ms: value },
            });
            void qc.invalidateQueries({ queryKey: ["match"] });
          }}
        >
          <label className="flex flex-col text-xs">
            {t("offset")}
            <input
              name="offset"
              type="number"
              step={10}
              defaultValue={active.time_offset_ms}
              key={active.id}
              className="min-h-11 w-28 bg-raised px-2 text-base ring-1 ring-inset ring-border"
            />
          </label>
          <Button type="submit" variant="secondary" className="min-h-9 px-2 text-xs">
            {t("save")}
          </Button>
        </form>
      )}
    </div>
  );
}
