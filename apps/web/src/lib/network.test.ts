import { describe, expect, it } from "vitest";
import { connectionHint } from "./network";

describe("connection hint", () => {
  it("detects mobile data and slow links", () => {
    expect(connectionHint({ connection: { type: "cellular" } })).toBe("mobile");
    expect(connectionHint({ connection: { saveData: true } })).toBe("mobile");
    expect(connectionHint({ connection: { effectiveType: "3g" } })).toBe("slow");
    expect(connectionHint({ connection: { type: "wifi", effectiveType: "4g" } })).toBeNull();
    expect(connectionHint({})).toBeNull();
  });
});
