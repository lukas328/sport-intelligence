import { describe, expect, it } from "vitest";
import { looksLikeVideo } from "./video-file";

describe("video file", () => {
  it("takes camera and phone files and refuses a text file before uploading", () => {
    expect(looksLikeVideo({ name: "GX010042.MP4", type: "" })).toBe(true);
    expect(looksLikeVideo({ name: "spiel", type: "video/quicktime" })).toBe(true);
    expect(looksLikeVideo({ name: "notizen.txt", type: "text/plain" })).toBe(false);
  });
});
