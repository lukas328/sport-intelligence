import type { Schemas } from "@handball/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { createElement, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import deCH from "../../../../../../messages/de-CH.json";
import en from "../../../../../../messages/en.json";
import fr from "../../../../../../messages/fr.json";
import type { Geometry } from "@/lib/moving-camera";
import { IdentityPanel } from "./identity-panel";

// Naming the people of the analysis (M5): each row shows the person as a still from the video
// and plays them right here, so nobody leaves the step to look. Invented players.
const match = { id: "m1", team_id: "t1", season_id: "s1", kind: "match", observed_team_id: null } as unknown as Schemas["MatchOut"];
const track = (n: number, first: number, extra: Record<string, unknown> = {}) =>
  ({ track_no: n, team: "home", team_confidence: 0.9, first_ms: first, last_ms: first + 20_000, observed_share: 0.8, player_id: null, player_confidence: null, number: null, identity_source: null, physical: null, source: "heuristic", ...extra }) as Schemas["TrackOut"];
const geometry: Geometry = { homography: [[32, 0, 0], [0, 36, 0], [0, 0, 1]], imageSize: [1280, 720] };

function render(props: Partial<ComponentProps<typeof IdentityPanel>> = {}, messages: Record<string, unknown> = deCH, locale = "de-CH"): string {
  return renderToStaticMarkup(
    createElement(
      QueryClientProvider,
      { client: new QueryClient() },
      createElement(
        NextIntlClientProvider,
        { locale, messages, timeZone: "Europe/Zurich" } as ComponentProps<typeof NextIntlClientProvider>,
        createElement(IdentityPanel, { orgId: "o", match, videoId: "v1", tracks: [track(3, 4000), track(7, 9000, { number: 11 })], at: (ms: number) => `${Math.round(ms / 1000)} s`, geometry, chunkMs: 30_000, ...props }),
      ),
    ),
  );
}

describe("identity: who is who, with the video in the step", () => {
  it("shows each person as a still, labelled for screen readers", () => {
    const html = render();
    expect(html.match(/data-testid="person-still"/g)).toHaveLength(2);
    expect(html).toContain('aria-label="Nr. 11"');
    expect(html).toContain('aria-label="Person 3"');
    // the play buttons play the person here, not in the main player far away
    expect(html).toContain("Person hier abspielen: Nr. 11, 9 s");
    expect(html).not.toContain('data-testid="identity-player"'); // until one is played
  });

  it("without a court (no position on the picture) only the play button, no empty pictures", () => {
    const html = render({ geometry: null });
    expect(html).not.toContain("person-still");
    expect(html.match(/data-testid="identity-row"/g)).toHaveLength(2);
  });

  it("speaks French and English", () => {
    expect(render({}, fr, "fr")).toContain("Lire la personne ici");
    expect(render({}, en, "en")).toContain("Play this person here");
  });
});
