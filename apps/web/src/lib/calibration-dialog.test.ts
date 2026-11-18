import type { Schemas } from "@handball/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { createElement, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import deCH from "../../messages/de-CH.json";
import fr from "../../messages/fr.json";
import { CourtCalibration } from "@/components/analysis/court-calibration";
import { HALL_H, HALL_H_OFF } from "./synthetic-hall";

// The dialog as the server renders it first: what the coach sees before any click, in each state
// of the court; labels and touch targets as the design asks.
function analysis(extra: Record<string, unknown>): Schemas["AnalysisOut"] {
  return {
    status: "ready",
    calibration: { homography: HALL_H, image_size: [1280, 720], confidence: 0.7, reprojection_px: 2, source: "heuristic", created_at: "2026-11-14T18:00:00Z" },
    calibration_info: { method: "hall", reference_video_id: "earlier" },
    camera: "moving",
    panorama: { width: 1280, height: 720 },
    hall: { name: "Sporthalle Kieselgrund", source: "match", calibrated_videos: 1 },
    needs_calibration: false,
    tracks: [],
    ...extra,
  } as unknown as Schemas["AnalysisOut"];
}

function render(a: Schemas["AnalysisOut"], messages: Record<string, unknown> = deCH, locale = "de-CH"): string {
  return renderToStaticMarkup(
    createElement(
      QueryClientProvider,
      { client: new QueryClient() },
      createElement(NextIntlClientProvider, { locale, messages, timeZone: "Europe/Zurich" } as ComponentProps<typeof NextIntlClientProvider>, createElement(CourtCalibration, { orgId: "o", videoId: "v", analysis: a, onClose: () => {}, imageSrc: "data:image/png;base64," })),
    ),
  );
}

const text = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");

describe("calibration dialog", () => {
  it("asks first whether the court from this hall fits, with one tap to confirm", () => {
    const html = render(analysis({ calibration_state: "suggested", calibration_suggestion: { source: "hall", homography: HALL_H, image_size: [1280, 720], space: "panorama", from_video_id: "v0", from_kickoff_at: "2026-11-14T18:00:00Z" } }));
    expect(text(html)).toContain("Passt das Spielfeld?");
    expect(text(html)).toContain("Feld aus dieser Halle, Spiel vom 14. Nov.");
    expect(html).toContain('data-testid="calibration-confirm"');
    expect(html).toContain('data-testid="calibration-correct"');
    expect(html).toContain('data-testid="overlay-suggest"');
    // the picture takes no clicks before «Korrigieren»
    expect(html).not.toContain('data-testid="line-chips"');
  });

  it("names an automatic suggestion as such", () => {
    const html = render(analysis({ calibration_info: { method: "goals" }, calibration: { homography: HALL_H_OFF, image_size: [1280, 720], confidence: 0.4, reprojection_px: 6, source: "heuristic", created_at: "2026-11-14T18:00:00Z" } }));
    expect(text(html)).toContain("Automatischer Vorschlag");
  });

  it("goes straight to the lines without a court, «Speichern» waits for the clicks", () => {
    const html = render(analysis({ calibration: null, needs_calibration: true, calibration_info: { reason: "no_floor" } }));
    expect(text(html)).toContain("Seitenlinie Kameraseite: tippe 2 bis 3 Stellen auf dieser Linie an.");
    expect((html.match(/data-testid="line-(?!chips)[a-z_]+"/g) ?? []).length).toBe(9);
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*data-testid="calibration-save"/);
    // every chip a labelled button of at least 44 px
    for (const m of html.matchAll(/<button[^>]*data-testid="line-[a-z_]+"[^>]*>/g)) {
      expect(m[0]).toContain("aria-label=");
      expect(m[0]).toContain("min-h-11");
    }
    // the tools are labelled icons
    for (const id of ["calibration-undo", "calibration-clear-line", "calibration-snap", "calibration-zoom-in"]) expect(html).toMatch(new RegExp(`aria-label="[^"]+"[^>]*data-testid="${id}"|data-testid="${id}"[^>]*aria-label="[^"]+"`));
    expect(html).toContain('aria-label="Schliessen"');
  });

  it("opens the coach's last clicks again and says when the court is being applied", () => {
    const html = render(analysis({ calibration_state: "updating", court_clicks: { space: "panorama", frame_ms: 0, lines: { side_near: [[100, 600], [600, 610]] }, points: {} } }));
    expect(text(html)).toContain("Seitenlinie gegenüber: tippe");
    expect(html).toContain('data-testid="calibration-state-note"');
    expect(html).toMatch(/aria-label="Seitenlinie Kameraseite, Taste 1, 2 Klicks"/);
  });

  it("speaks French too", () => {
    const html = render(analysis({ calibration: null, needs_calibration: true }), fr, "fr");
    expect(text(html)).toContain("Ligne de touche côté caméra : touche 2 à 3 endroits sur cette ligne.");
  });
});
