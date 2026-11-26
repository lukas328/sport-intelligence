import type { Schemas } from "@handball/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { createElement, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import deCH from "../../../messages/de-CH.json";
import en from "../../../messages/en.json";
import fr from "../../../messages/fr.json";
import { ProgressPanel } from "./progress-panel";

// Marking the court while the analysis runs (#141): once the hall image is there the progress
// block of the match asks for it, prominently, with the button that opens the marking; once
// marked it says the run takes it. Invented match, no real club.
function progress(court: "mark" | "taken" | null, extra: Record<string, unknown> = {}): Schemas["MatchProgressOut"] {
  return {
    match_id: "m1",
    team_id: "t1",
    kind: "match",
    opponent_name: "TV Seewald",
    kickoff_at: "2026-11-21T17:00:00Z",
    is_home: true,
    stage: "analysis",
    state: "running",
    overall: 0.42,
    eta_s: 1200,
    files: [
      {
        video_id: "v1",
        filename: "spiel.mp4",
        role: "main",
        stage: "analysis",
        state: "running",
        step: "observe",
        fraction: 0.2,
        overall: 0.42,
        eta_s: 1200,
        court,
        restarted: false,
        retry: true,
      },
    ],
    ...extra,
  } as unknown as Schemas["MatchProgressOut"];
}

function render(p: Schemas["MatchProgressOut"], { staff = true, canOpen = true, messages = deCH as Record<string, unknown>, locale = "de-CH" } = {}): string {
  return renderToStaticMarkup(
    createElement(
      QueryClientProvider,
      { client: new QueryClient() },
      createElement(
        NextIntlClientProvider,
        { locale, messages, timeZone: "Europe/Zurich", now: new Date("2026-11-21T19:00:00Z") } as ComponentProps<typeof NextIntlClientProvider>,
        createElement(ProgressPanel, { orgId: "o", progress: p, staff, onMarkCourt: canOpen ? vi.fn() : undefined }),
      ),
    ),
  );
}

const text = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");

describe("progress: mark the court while the analysis runs", () => {
  it("asks for it prominently once the hall image is there, with the button", () => {
    const html = render(progress("mark"));
    expect(html).toContain('data-testid="progress-court"');
    expect(html).toContain('data-testid="progress-mark-court"');
    expect(text(html)).toContain("Markiere jetzt das Spielfeld");
    expect(text(html)).toContain("in einem Durchgang vollständig");
    // the progress stays beside it: how far and the bar
    expect(text(html)).toContain("42");
    expect(html).toContain('role="progressbar"');
  });

  it("says the marked court is taken, and asks nothing before the hall image", () => {
    const taken = render(progress("taken"));
    expect(taken).not.toContain('data-testid="progress-mark-court"');
    expect(text(taken)).toContain("Dein Spielfeld ist markiert. Die laufende Analyse übernimmt es.");
    const before = render(progress(null));
    expect(before).not.toContain("progress-court");
  });

  it("asks only whoever works with the video, and only where the page can open the marking", () => {
    expect(render(progress("mark"), { staff: false })).not.toContain("progress-court");
    expect(render(progress("mark"), { canOpen: false })).not.toContain('data-testid="progress-court"');
  });

  it("is a finger wide on a phone", () => {
    const button = render(progress("mark")).match(/<button[^>]*data-testid="progress-mark-court"[^>]*>/)?.[0] ?? "";
    expect(button).toContain("max-sm:w-full");
  });

  it("has the words in French and English", () => {
    expect(text(render(progress("mark"), { messages: fr, locale: "fr" }))).toContain("Marque le terrain maintenant");
    expect(text(render(progress("taken"), { messages: en, locale: "en" }))).toContain("The running analysis takes it.");
  });
});

vi.mock("next/navigation", () => ({ usePathname: () => "/app/o/teams/t1" }));

describe("strip: the link to mark the court", () => {
  async function strip(p: Schemas["MatchProgressOut"]): Promise<string> {
    const { ProgressStrip } = await import("./progress-strip");
    const { progressKey } = await import("@/lib/progress");
    const client = new QueryClient();
    client.setQueryData(progressKey("o"), [p]);
    return renderToStaticMarkup(
      createElement(
        QueryClientProvider,
        { client },
        createElement(
          NextIntlClientProvider,
          { locale: "de-CH", messages: deCH as Record<string, unknown>, timeZone: "Europe/Zurich", now: new Date("2026-11-21T19:00:00Z") } as ComponentProps<typeof NextIntlClientProvider>,
          createElement(ProgressStrip, { orgId: "o" }),
        ),
      ),
    );
  }

  it("opens the marking on the match from every page", async () => {
    const html = await strip(progress("mark"));
    const link = html.match(/<a[^>]*data-testid="strip-court"[^>]*>/)?.[0] ?? "";
    expect(link).toContain('href="/app/o/matches/m1?tab=video&amp;mark=court"');
    expect(text(html)).toContain("Spielfeld markieren");
  });

  it("keeps the usual line otherwise", async () => {
    for (const court of [null, "taken"] as const) {
      const html = await strip(progress(court));
      expect(html).toContain('data-testid="progress-strip"');
      expect(html).not.toContain("strip-court");
    }
  });
});
