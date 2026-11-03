import { describe, expect, it } from "vitest";
import { resolveHref } from "./links";

describe("content links", () => {
  it("resolves help, blog and legal links against their folder", () => {
    expect(resolveHref("kader", "de", "hilfe")).toBe("/de/hilfe/kader/");
    expect(resolveHref("../preise", "fr", "hilfe")).toBe("/fr/preise/");
    expect(resolveHref("../hilfe/aufnahme", "en", "blog")).toBe("/en/hilfe/aufnahme/");
    // legal pages link like siblings of a folder: "../impressum" from /de/datenschutz/
    expect(resolveHref("../impressum", "de", "legal")).toBe("/de/impressum/");
    expect(resolveHref("https://example.org/x", "de", "hilfe")).toBe("https://example.org/x");
    expect(resolveHref("mailto:a@b.ch", "de", "hilfe")).toBe("mailto:a@b.ch");
  });
});
