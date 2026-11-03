import { describe, expect, it } from "vitest";
import de from "@/messages/de";
import en from "@/messages/en";
import fr from "@/messages/fr";

function leaves(value: unknown, path = ""): [string, string][] {
  if (typeof value === "string") return [[path, value]];
  if (Array.isArray(value)) return value.flatMap((v, i) => leaves(v, `${path}[${i}]`));
  return Object.entries(value as Record<string, unknown>).flatMap(([k, v]) => leaves(v, path ? `${path}.${k}` : k));
}

describe("site messages", () => {
  const ref = leaves(de);
  it.each([["fr", fr], ["en", en]])("%s has the same keys and placeholders as de", (_, other) => {
    const map = new Map(leaves(other));
    expect([...map.keys()]).toEqual(ref.map(([k]) => k));
    for (const [k, v] of ref) {
      const ph = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
      expect(ph(map.get(k) ?? ""), k).toEqual(ph(v));
    }
  });

  it("uses no long dashes and no sharp s", () => {
    for (const msgs of [de, fr, en]) for (const [k, v] of leaves(msgs)) expect(v, k).not.toMatch(/[–—]/);
    for (const [k, v] of ref) expect(v, k).not.toContain("ß");
  });
});
