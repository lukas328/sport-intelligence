import { describe, expect, it } from "vitest";
import { easter, holidaysBetween } from "./holidays";

describe("holidays", () => {
  it("finds Easter", () => {
    expect(easter(2026).toISOString().slice(0, 10)).toBe("2026-04-05");
    expect(easter(2027).toISOString().slice(0, 10)).toBe("2027-03-28");
  });

  it("lists the holidays of a season in order", () => {
    const h = holidaysBetween("2026-08-01", "2027-06-30");
    expect(h.map((x) => `${x.date} ${x.key}`)).toEqual([
      "2026-08-01 national",
      "2026-12-25 christmas",
      "2026-12-26 stephen",
      "2027-01-01 newYear",
      "2027-01-02 berchtold",
      "2027-03-26 goodFriday",
      "2027-03-29 easterMonday",
      "2027-05-06 ascension",
      "2027-05-17 whitMonday",
    ]);
  });
});
