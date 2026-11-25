import type { Schemas } from "@handball/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { createElement, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import deCH from "../../../../../../messages/de-CH.json";
import en from "../../../../../../messages/en.json";
import fr from "../../../../../../messages/fr.json";
import { AnalysisPanel } from "./analysis-panel";

// The court step as the server renders it: a court carried over from an earlier match of the hall
// says so, with the realign button beside it; a court clicked on this video says nothing of it.
const H = [
  [2, 0, 10],
  [0, 2, 20],
  [0, 0, 1],
];

function analysis(extra: Record<string, unknown>): Schemas["AnalysisOut"] {
  return {
    status: "ready",
    calibration: { homography: H, image_size: [1280, 720], confidence: 1, reprojection_px: 0.5, source: "heuristic", created_at: "2026-11-14T18:00:00Z" },
    calibration_info: { method: "hall", reference_video_id: "v0", floor_inliers: 140, error_px: 1.5, sure: true },
    calibration_state: "confirmed",
    calibration_origin: {
      source: "hall",
      hall: "Sporthalle Kieselgrund",
      reference_video_id: "v0",
      reference_match_id: "m0",
      reference_kickoff_at: "2026-11-07T16:00:00Z",
    },
    camera: "fixed",
    panorama: { width: 1280, height: 720 },
    hall: { name: "Sporthalle Kieselgrund", source: "match", calibrated_videos: 1 },
    needs_calibration: false,
    tracks: [],
    formations: [],
    chunks: null,
    chunk_ms: null,
    ...extra,
  } as unknown as Schemas["AnalysisOut"];
}

function render(a: Schemas["AnalysisOut"], { messages = deCH as Record<string, unknown>, locale = "de-CH", canCalibrate = true } = {}): string {
  return renderToStaticMarkup(
    createElement(
      QueryClientProvider,
      { client: new QueryClient() },
      createElement(
        NextIntlClientProvider,
        { locale, messages, timeZone: "Europe/Zurich" } as ComponentProps<typeof NextIntlClientProvider>,
        createElement(AnalysisPanel, { analysis: a, orgId: "o", videoId: "v", colours: {}, getTime: () => 0, canCalibrate }),
      ),
    ),
  );
}

const text = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
const origin = (html: string) => html.match(/<div[^>]*data-testid="court-origin"[^>]*>.*?<\/div>/)?.[0] ?? "";

describe("court step: where the court came from", () => {
  it("names the hall and the match the court was carried over from, with the realign button beside it", () => {
    const html = render(analysis({}));
    const note = origin(html);
    expect(text(note)).toContain("Spielfeld aus der Sporthalle Kieselgrund übernommen ( Spiel vom 7. Nov. ). Passt es nicht, richte es neu aus.");
    expect(note).toContain('href="/app/o/matches/m0"');
    expect(note).toContain('data-testid="mark-court"');
    expect(text(note)).toContain("Spielfeld neu ausrichten");
    // one realign button, no second sentence about the hall
    expect(html.match(/data-testid="mark-court"/g)).toHaveLength(1);
    expect(text(html)).not.toContain("du musst nichts prüfen");
  });

  it("says an earlier match of this hall without a hall name", () => {
    const html = render(analysis({ calibration_origin: { source: "hall", hall: null, reference_video_id: "v0", reference_match_id: "m0", reference_kickoff_at: "2026-11-07T16:00:00Z" } }));
    expect(text(origin(html))).toContain("Spielfeld aus einem früheren Spiel in dieser Halle übernommen ( Spiel vom 7. Nov. ).");
  });

  it("does not ask to realign whoever cannot set the court", () => {
    const html = render(analysis({}), { canCalibrate: false });
    expect(text(origin(html))).toContain("Spielfeld aus der Sporthalle Kieselgrund übernommen");
    expect(html).not.toContain("Passt es nicht");
    expect(html).not.toContain('data-testid="mark-court"');
  });

  it("has the note in French and English", () => {
    expect(text(origin(render(analysis({}), { messages: fr, locale: "fr" })))).toContain("Terrain repris de la salle Sporthalle Kieselgrund");
    expect(text(origin(render(analysis({}), { messages: en, locale: "en" })))).toContain("Court carried over from Sporthalle Kieselgrund");
  });

  it("shows nothing of it for a court clicked on this video", () => {
    const html = render(
      analysis({
        calibration: { homography: H, image_size: [1280, 720], confidence: 1, reprojection_px: 0.5, source: "user_correction", created_at: "2026-11-14T18:00:00Z" },
        calibration_info: { method: "lines" },
        calibration_origin: null,
      }),
    );
    expect(html).not.toContain('data-testid="court-origin"');
    expect(text(html)).not.toContain("übernommen");
    expect(text(html)).toContain("Das Spielfeld passt.");
    expect(html).toContain('data-testid="mark-court"');
  });
});
