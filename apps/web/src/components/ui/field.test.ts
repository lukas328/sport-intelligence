import { describe, expect, it } from "vitest";
import { control } from "./field";

describe("control (the look of every text field)", () => {
  const classes = control.split(/\s+/).filter(Boolean);

  it("is 16 px and a finger high, so iPhone Safari does not zoom in on focus", () => {
    expect(classes).toContain("text-base");
    expect(classes).toContain("min-h-11");
    expect(classes.some((c) => /^text-\[(0\.9375rem|1[0-5]px)\]$|^text-(xs|sm)$/.test(c))).toBe(false);
  });

  it("has no two classes glued together", () => {
    // «ring-foreground/20placeholder:…» once swallowed the placeholder, hover and focus styles
    expect(classes).toContain("ring-foreground/20");
    expect(classes).toContain("placeholder:text-muted/70");
    expect(classes).toContain("hover:ring-muted/40");
    expect(classes).toContain("focus-visible:outline-none");
  });
});
