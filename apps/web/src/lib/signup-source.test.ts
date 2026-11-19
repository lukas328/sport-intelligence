import { describe, expect, it } from "vitest";
import { signupSource, sourceFrom } from "./signup-source";

describe("signup source", () => {
  it("keeps a short place from the website and nothing else", () => {
    expect(sourceFrom("?src=hero")).toBe("hero");
    expect(sourceFrom("?lang=fr&src=Pricing")).toBe("pricing");
    expect(sourceFrom("?src=shared-scene_2")).toBe("shared-scene_2");
    expect(sourceFrom("?src=")).toBeNull();
    expect(sourceFrom("?src=%3Cb%3E")).toBeNull();
    expect(sourceFrom(`?src=${"a".repeat(41)}`)).toBeNull();
    expect(sourceFrom("")).toBeNull();
  });

  it("never throws without a browser storage", () => {
    expect(signupSource()).toBeNull();
  });
});
