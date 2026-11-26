import { describe, expect, it } from "vitest";
import { stickyRoom } from "./sticky-focus";

describe("stickyRoom", () => {
  it("is the tallest sticky player, 0 without any", () => {
    expect(stickyRoom([])).toBe(0);
    expect(stickyRoom([425, 180])).toBe(425);
    expect(stickyRoom([0, 0])).toBe(0);
  });
});
