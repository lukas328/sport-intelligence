import { describe, expect, it } from "vitest";
import { combine, defaultKickoff, formatDate, formatTime, isoDay, parseDate, parseTime } from "./date-input";

describe("date and time as written in Switzerland (L16)", () => {
  const today = new Date(2026, 10, 16);

  it("writes dd.mm.yyyy and 24 hours", () => {
    const d = new Date(2026, 10, 6, 14, 3);
    expect(formatDate(d)).toBe("06.11.2026");
    expect(formatTime(d)).toBe("14:03");
  });

  it("reads the usual ways of writing a date", () => {
    expect(parseDate("16.11.2026", today)).toEqual([2026, 11, 16]);
    expect(parseDate("6.1.27", today)).toEqual([2027, 1, 6]);
    expect(parseDate("16.11.", today)).toEqual([2026, 11, 16]);
    expect(parseDate("2026-11-16", today)).toEqual([2026, 11, 16]);
    expect(parseDate("31.02.2026", today)).toBeNull();
    expect(parseDate("11/16/2026", today)).toBeNull(); // no month first
    expect(parseDate("morgen", today)).toBeNull();
  });

  it("reads times without am and pm", () => {
    expect(parseTime("14:30")).toEqual([14, 30]);
    expect(parseTime("14.30")).toEqual([14, 30]);
    expect(parseTime("1430")).toEqual([14, 30]);
    expect(parseTime("9")).toEqual([9, 0]);
    expect(parseTime("18 Uhr")).toEqual([18, 0]);
    expect(parseTime("24:00")).toBeNull();
    expect(parseTime("2:30 PM")).toBeNull();
  });

  it("combines both into the local moment", () => {
    expect(combine("16.11.2026", "20:15", today)).toEqual(new Date(2026, 10, 16, 20, 15));
    expect(combine("16.11.2026", "", today)).toBeNull();
    expect(isoDay("6.1.2027")).toBe("2027-01-06");
    expect(isoDay("x")).toBe("");
  });
});

describe("defaultKickoff", () => {
  it("during the day: the last full hour, never the current minute", () => {
    expect(defaultKickoff(new Date(2026, 10, 17, 14, 23))).toEqual({ day: "17.11.2026", clock: "14:00" });
    expect(defaultKickoff(new Date(2026, 10, 17, 21, 40))).toEqual({ day: "17.11.2026", clock: "21:00" });
  });

  it("at night and early in the morning: last evening's match", () => {
    expect(defaultKickoff(new Date(2026, 10, 17, 8, 59))).toEqual({ day: "16.11.2026", clock: "18:00" });
    expect(defaultKickoff(new Date(2026, 10, 17, 0, 57))).toEqual({ day: "16.11.2026", clock: "18:00" });
    expect(defaultKickoff(new Date(2026, 11, 1, 3, 0))).toEqual({ day: "30.11.2026", clock: "18:00" });
  });
});
