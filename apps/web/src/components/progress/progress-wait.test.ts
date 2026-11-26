import type { Schemas } from "@handball/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { createElement, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import deCH from "../../../messages/de-CH.json";
import en from "../../../messages/en.json";
import fr from "../../../messages/fr.json";
import { ShellContext } from "@/components/shell/context";
import { ProgressPanel } from "./progress-panel";

// Waiting for a long analysis, honestly: the time left as a range measured from the running
// step's pace, said as such; none where nothing was measured. Invented match, no real club.
function progress(extra: Record<string, unknown> = {}, file: Record<string, unknown> = {}): Schemas["MatchProgressOut"] {
  return {
    match_id: "m1",
    team_id: "t1",
    kind: "match",
    opponent_name: "TV Seewald",
    kickoff_at: "2026-11-21T17:00:00Z",
    is_home: true,
    stage: "analysis",
    state: "running",
    overall: 0.3,
    eta_s: 10512,
    eta_range_s: [9612, 11412],
    files: [
      {
        video_id: "v1",
        filename: "spiel.mp4",
        role: "main",
        stage: "analysis",
        state: "running",
        step: "observe",
        fraction: 0.3,
        overall: 0.3,
        eta_s: 10512,
        eta_range_s: [9612, 11412],
        eta_basis: "measured",
        restarted: false,
        retry: true,
        ...file,
      },
    ],
    ...extra,
  } as unknown as Schemas["MatchProgressOut"];
}

function render(
  p: Schemas["MatchProgressOut"],
  { messages = deCH as Record<string, unknown>, locale = "de-CH", role = null as string | null, mail = null as boolean | null } = {},
): string {
  const client = new QueryClient();
  if (mail != null) client.setQueryData(["public-config"], { mail_enabled: mail });
  const shell = { teams: [{ id: "t1", my_role: role }] } as unknown as ComponentProps<typeof ShellContext.Provider>["value"];
  return renderToStaticMarkup(
    createElement(
      QueryClientProvider,
      { client },
      createElement(
        ShellContext.Provider,
        { value: shell },
        createElement(
          NextIntlClientProvider,
          // 20:00 in Zurich
          { locale, messages, timeZone: "Europe/Zurich", now: new Date("2026-11-21T19:00:00Z") } as ComponentProps<typeof NextIntlClientProvider>,
          createElement(ProgressPanel, { orgId: "o", progress: p, staff: true }),
        ),
      ),
    ),
  );
}

const text = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");

describe("progress: the time left of a long analysis", () => {
  it("is a measured range: «etwa … bis …», the finish between two times, and how it was measured", () => {
    const t = text(render(progress()));
    expect(t).toContain("fertig etwa zwischen 22:45 und 23:15");
    expect(t).toContain("noch etwa 2½ bis 3½ Std.");
    expect(t).toContain("Gemessen am Tempo dieser Analyse");
  });

  it("stays one time without a measured range, and says no time where none is known", () => {
    const one = text(render(progress({ eta_range_s: null }, { eta_range_s: null })));
    expect(one).toContain("fertig etwa um");
    expect(one).not.toContain("zwischen");
    const none = text(render(progress({ eta_s: null, eta_range_s: null }, { eta_s: null, eta_range_s: null, eta_basis: null })));
    expect(none).toContain("Wie lange es dauert, steht hier, sobald dieser Schritt ein Stück weit ist.");
    expect(none).not.toContain("etwa um");
  });

  it("has the words in French and English", () => {
    expect(text(render(progress(), { messages: fr, locale: "fr" }))).toContain("encore environ 2½ à 3½ h");
    expect(text(render(progress(), { messages: en, locale: "en" }))).toContain("about 2½ to 3½ h left");
  });
});

describe("progress: whoever may close the page hears when it is done", () => {
  it("promises the mail to the team's coaches and analysts when mails go out", () => {
    expect(text(render(progress(), { role: "coach", mail: true }))).toContain("Wir schicken dir eine Mail, sobald die Analyse fertig ist");
    expect(text(render(progress(), { role: "analyst", mail: true }))).toContain("Wir schicken dir eine Mail");
  });

  it("names the bell when no mails go out, and promises nothing to whoever gets neither", () => {
    const bell = text(render(progress(), { role: "coach", mail: false }));
    expect(bell).toContain("steht es in der Glocke oben");
    expect(bell).not.toContain("Mail");
    const player = text(render(progress(), { role: "player", mail: true }));
    expect(player).toContain("Es läuft von selbst weiter");
    expect(player).not.toContain("Mail");
    expect(player).not.toContain("Glocke");
  });

  it("has the words in French and English", () => {
    expect(text(render(progress(), { role: "coach", mail: true, messages: fr, locale: "fr" }))).toContain("envoyons un e-mail dès que");
    expect(text(render(progress(), { role: "coach", mail: true, messages: en, locale: "en" }))).toContain("e-mail you as soon as");
  });
});
