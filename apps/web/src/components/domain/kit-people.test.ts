import type { Schemas } from "@handball/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { createElement, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import deCH from "../../../messages/de-CH.json";
import en from "../../../messages/en.json";
import fr from "../../../messages/fr.json";
import { KitFields } from "./kit-fields";
import { peopleOf } from "./kit-people";

// The kit colours after the analysis: under each colour the people the analysis put in it, so a
// wrong colour shows at once and a tap plays the person right there. Invented people.
const tr = (n: number, team: string, secs: number, share = 0.8) =>
  ({ track_no: n, team, team_confidence: 0.9, first_ms: 1000 * n, last_ms: 1000 * n + secs * 1000, observed_share: share, player_id: null, player_confidence: null, number: null, identity_source: null, physical: null, source: "heuristic" }) as Schemas["TrackOut"];
const tracks = [tr(1, "home", 40), tr(2, "home", 90), tr(3, "home", 10), tr(4, "home", 60), tr(5, "away", 30), tr(6, "referee", 50), tr(7, "home_gk", 20)];
const analysis = {
  status: "ready",
  camera: "fixed",
  calibration: { homography: [[32, 0, 0], [0, 36, 0], [0, 0, 1]], image_size: [1280, 720], confidence: 1, reprojection_px: 1, source: "heuristic", created_at: "2026-11-21T18:00:00Z" },
  chunk_ms: 30_000,
  chunks: 4,
  tracks,
} as unknown as Schemas["AnalysisOut"];
const kits = { own: "#c81e1e", own_gk: "#111111", opponent: "#1e40af", opponent_gk: "#16a34a", referee: "#facc15" };

function render(withVideo = true, messages: Record<string, unknown> = deCH, locale = "de-CH", ready = true): string {
  const client = new QueryClient();
  client.setQueryData(["analysis", "v1"], ready ? analysis : { ...analysis, status: "running" });
  return renderToStaticMarkup(
    createElement(
      QueryClientProvider,
      { client },
      createElement(
        NextIntlClientProvider,
        { locale, messages, timeZone: "Europe/Zurich" } as ComponentProps<typeof NextIntlClientProvider>,
        createElement(KitFields, { kits, onChange: () => {}, pictures: withVideo ? { orgId: "o", videoId: "v1" } : null }),
      ),
    ),
  );
}

describe("peopleOf: who stands for a colour", () => {
  it("the three seen most of that colour", () => {
    expect(peopleOf(tracks, "own").map((t) => t.track_no)).toEqual([2, 4, 1]);
    expect(peopleOf(tracks, "referee").map((t) => t.track_no)).toEqual([6]);
    expect(peopleOf(tracks, "opponent_gk")).toEqual([]);
  });
});

describe("kit fields with the people of each colour", () => {
  it("shows the people under their colour, the referee too", () => {
    const html = render();
    const own = html.slice(html.indexOf('data-testid="kit-people-own"'), html.indexOf('data-testid="kit-own_gk"'));
    expect(own.match(/data-testid="person-still"/g)).toHaveLength(3);
    expect(html).toContain('data-testid="kit-people-referee"');
    expect(html).toContain('data-testid="kit-people-own_gk"');
    expect(html).toContain("Person 2 in dieser Farbe abspielen");
    expect(html).toContain("wen die Analyse in dieser Farbe sieht");
  });

  it("says when nobody was seen in a colour: a hint the colour may be wrong", () => {
    expect(render()).toContain('data-testid="kit-nobody-opponent_gk"');
  });

  it("plain colours without a video or before the analysis is ready", () => {
    for (const html of [render(false), render(true, deCH, "de-CH", false)]) {
      expect(html).toContain('data-testid="kit-own"');
      expect(html).not.toContain("person-still");
      expect(html).not.toContain("kit-nobody");
    }
  });

  it("speaks French and English", () => {
    expect(render(true, fr, "fr")).toContain("Personne reconnu dans cette couleur.");
    expect(render(true, en, "en")).toContain("Play Person 2 in this colour");
  });
});
