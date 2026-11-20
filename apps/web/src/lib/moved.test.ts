import { describe, expect, it } from "vitest";
import { movedAddress } from "./moved";

const team = "/app/o1/teams/t1";
const moved = (path: string, query = "") => movedAddress(path, new URLSearchParams(query));

describe("movedAddress", () => {
  it("hands the old assistant's question to Szenen, else puts the cursor in the field", () => {
    expect(moved(`${team}/assistant`, "q=Gegentore rechts")).toBe(`${team}/scenes?q=Gegentore%20rechts`);
    expect(moved(`${team}/assistant`)).toBe(`${team}/scenes?focus=1`);
  });
  it("keeps the filters of the old search", () => {
    expect(moved(`${team}/search`, "chips=conceded&observed=1")).toBe(`${team}/scenes?chips=conceded&observed=1`);
    expect(moved(`${team}/search`)).toBe(`${team}/scenes`);
  });
  it("leads the other old addresses to their new place", () => {
    expect(moved(`${team}/library`)).toBe(`${team}/collections`);
    expect(moved(`${team}/paper`)).toBe(`${team}/matches`);
    expect(moved(`${team}/matrix`)).toBe(`${team}/scenes?view=table`);
    expect(moved("/app/o1/matches/m1/marks")).toBe("/app/o1/matches/m1/matchday?mode=marks");
    expect(moved("/app/o1/matches/m1/live")).toBe("/app/o1/matches/m1/matchday?mode=detail");
    expect(moved("/app/o1/profile")).toBe("/app/o1/me");
    expect(moved("/app/o1/settings/access-requests")).toBe("/app/o1/club/federation");
  });
  it("leaves the pivot, the new addresses and deeper paths alone", () => {
    expect(moved(`${team}/matrix`, "pivot=1")).toBeNull();
    expect(moved(`${team}/scenes`, "focus=1")).toBeNull();
    expect(moved("/app/o1/matches/m1/matchday")).toBeNull();
    expect(moved(`${team}/paper/x`)).toBeNull();
    expect(moved("/app/o1/settings")).toBeNull();
  });
});
