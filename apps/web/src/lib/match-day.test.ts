import { describe, expect, it } from "vitest";
import { isMatchDay } from "./match-day";

describe("isMatchDay", () => {
  const kickoff = "2026-11-21T18:00:00+01:00";
  const at = (iso: string) => Date.parse(iso);

  it("not days before the match", () => {
    expect(isMatchDay(kickoff, at("2026-11-18T20:00:00+01:00"))).toBe(false);
    expect(isMatchDay(kickoff, at("2026-11-21T14:59:00+01:00"))).toBe(false);
  });

  it("from three hours before until three hours after the kick-off", () => {
    expect(isMatchDay(kickoff, at("2026-11-21T15:00:00+01:00"))).toBe(true);
    expect(isMatchDay(kickoff, at("2026-11-21T19:30:00+01:00"))).toBe(true);
    expect(isMatchDay(new Date(kickoff), at("2026-11-21T21:00:00+01:00"))).toBe(true);
    expect(isMatchDay(kickoff, at("2026-11-21T21:01:00+01:00"))).toBe(false);
  });
});
