import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { goalDistance, halfSpot, SHOT_MIN } from "@/lib/demo";
import { MATCH } from "@/lib/things";
import de from "@/messages/de";
import en from "@/messages/en";
import fr from "@/messages/fr";
import { saturday, sundayAnswer, threeMatchesLater } from "./story";

describe("the start page's week", () => {
  it("starts with the demo match: lost 27:29, 11 of 29 over the right wing", () => {
    const s = saturday();
    expect(s.score).toBe("27:29");
    expect([s.n, s.of, s.zone]).toEqual([11, 29, "ra"]);
    expect(s.dots).toHaveLength(29);
    expect(s.dots.filter((d) => d.ra)).toHaveLength(11);
  });

  it("ends three matches later with 3 of 26, the three on the right wing", () => {
    const l = threeMatchesLater();
    expect([l.n, l.of]).toEqual([3, 26]);
    for (const d of l.dots.filter((x) => x.ra)) expect(d.at[0]).toBeGreaterThan(16);
    for (const d of l.dots) {
      expect(goalDistance(d.at)).toBeGreaterThanOrEqual(SHOT_MIN - 1e-9);
      expect(d.at[0]).toBeGreaterThanOrEqual(0);
      expect(d.at[0]).toBeLessThanOrEqual(20);
    }
  });
});

describe("Sunday's question to the assistant (U6)", () => {
  it("answers from the demo match: 11 of 29, 5 before and 6 after the break, number 7 seven, number 22 four", () => {
    const a = sundayAnswer();
    expect([a.n, a.of, a.first, a.second]).toEqual([11, 29, 5, 6]);
    expect(a.shooters).toEqual([
      { number: 7, n: 7 },
      { number: 22, n: 4 },
    ]);
    expect(a.fast).toBe(5);
  });

  it("names the drill of the app's library for the fast breaks against, in every language", () => {
    const drills = JSON.parse(readFileSync(join(__dirname, "..", "..", "..", "api", "src", "handball_api", "services", "drills.json"), "utf8")) as { id: string; name: Record<string, string> }[];
    const name = drills.find((d) => d.id === "transition_3v2_back")!.name;
    expect(de.home.shareText).toContain(`«${name["de-CH"]}»`);
    expect(fr.home.shareText).toContain(`« ${name.fr} »`);
    expect(en.home.shareText).toContain(`"${name.en}"`);
  });
});

describe("the app's demo club tells the same story (scripts/seed.py)", () => {
  const seed = readFileSync(join(__dirname, "..", "..", "..", "..", "scripts", "seed.py"), "utf8");

  it("seeds the website's match, club, opponent and collection", () => {
    expect(seed).toContain('.parents[1] / "apps" / "site" / "public" / "demo" / "match.json"');
    expect(seed.match(/^CLUB = "(.+)"$/m)?.[1]).toBe(MATCH.own);
    expect(seed).toContain(`opponent="${MATCH.opponent}"`);
    const collection = seed.match(/^COLLECTION = "(.+)"$/m)?.[1];
    expect(de.home.chat.previewTitle).toBe(`${collection}: 4 Szenen`);
    expect(de.home.chat.previewText.startsWith(`${MATCH.own} Herren 1 · `)).toBe(true);
  });

  it("puts our pivot's shots in the circle band, so the app counts them «vom Kreis» from the spot", () => {
    // packages/court/spec/zones.json: circle_max_m 6.5; the app takes the zone from the spot
    const pivot = MATCH.events.filter((e) => e.shot_type === "pivot");
    expect(pivot.length).toBeGreaterThan(9);
    for (const e of pivot) expect(goalDistance(halfSpot(e.x!, e.y!)), e.id).toBeLessThanOrEqual(6.5);
  });

  it("takes our shooters from the seeded squad, only players with a consent", () => {
    const squad = new Set([...seed.matchAll(/^\s+\((\d+), "[^"]+", "[^"]+", "(?:LA|RL|RM|RR|RA|KM)"/gm)].map((m) => Number(m[1])));
    const noConsent = seed.match(/^NO_CONSENT = \{(.+)\}$/m)![1]!.split(",").map((x) => Number(x.trim()));
    for (const e of MATCH.events.filter((x) => x.side === "own")) {
      expect(squad.has(e.number!), String(e.number)).toBe(true);
      expect(noConsent).not.toContain(e.number);
    }
  });
});
