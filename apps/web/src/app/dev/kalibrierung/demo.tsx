"use client";

import type { Schemas } from "@handball/api-client";
import { useEffect, useState } from "react";
import { CourtCalibration } from "@/components/analysis/court-calibration";
import { Button } from "@/components/ui/button";
import { HALL_H, HALL_H_OFF, HALL_SIZE, drawHall } from "@/lib/synthetic-hall";

type State = "hall" | "auto" | "missing" | "confirmed";

/** An analysis as the API sends it for each state of the court (demo values). */
function analysisOf(state: State): Schemas["AnalysisOut"] {
  const [w, h] = HALL_SIZE;
  const calibration =
    state === "missing"
      ? null
      : {
          homography: state === "auto" ? HALL_H_OFF : HALL_H,
          image_size: [w, h],
          confidence: 0.7,
          reprojection_px: 3,
          source: state === "confirmed" ? "user_correction" : "heuristic",
          created_at: "2026-11-14T18:00:00Z",
        };
  return {
    status: "ready",
    calibration,
    calibration_info: state === "hall" ? { method: "hall", reference_video_id: "demo-earlier" } : state === "auto" ? { method: "goals" } : { reason: "no_floor" },
    camera: "moving",
    panorama: { width: w, height: h },
    hall: { name: "Sporthalle Kieselgrund", source: "match", calibrated_videos: 1 },
    needs_calibration: state === "missing",
    tracks: [],
    chunk_ms: null,
    chunks: null,
    fps: 25,
    detector: "yolo",
    elapsed_s: 30,
    formations: [],
    auto_events: null,
    error: null,
  } as unknown as Schemas["AnalysisOut"];
}

export function CalibrationDemo({ state }: { state: State }) {
  const [src, setSrc] = useState<string | null>(null);
  const [open, setOpen] = useState(true);
  useEffect(() => {
    const c = document.createElement("canvas");
    [c.width, c.height] = HALL_SIZE;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    drawHall(ctx);
    setSrc(c.toDataURL("image/png"));
  }, []);
  return (
    <main className="mx-auto max-w-3xl space-y-4 p-6">
      <h1 className="text-[28px]">Spielfeld markieren: Bausteine</h1>
      <p className="text-[15px] text-ink-2">Gezeichnetes Hallenbild, Demo-Daten. Zustand: {state}</p>
      <Button onClick={() => setOpen(true)} data-testid="open-calibration">
        Dialog öffnen
      </Button>
      {open && src && <CourtCalibration orgId="demo" videoId="demo" analysis={analysisOf(state)} imageSrc={src} onClose={() => setOpen(false)} />}
    </main>
  );
}
