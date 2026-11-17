import { describe, expect, it } from "vitest";
import { heldFiles } from "./early-files";

describe("heldFiles", () => {
  it("nothing without an input or without files", () => {
    expect(heldFiles(null)).toBeNull();
    expect(heldFiles({ files: null })).toBeNull();
    expect(heldFiles({ files: [] })).toBeNull();
  });

  it("copies the files, so clearing the input keeps them", () => {
    const a = new File(["x"], "spiel.mp4", { type: "video/mp4" });
    const list: File[] = [a];
    const held = heldFiles({ files: list });
    list.length = 0;
    expect(held).toEqual([a]);
  });
});
