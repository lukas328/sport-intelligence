import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
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

  it("says scène in French, like the app (one word per thing), never séquence", () => {
    const dir = join(__dirname, "..", "..", "content");
    const texts: [string, string][] = leaves(fr);
    for (const kind of ["ratgeber", "help", "blog"]) {
      for (const f of readdirSync(join(dir, kind, "fr"))) texts.push([`${kind}/fr/${f}`, readFileSync(join(dir, kind, "fr", f), "utf8")]);
      texts.push([`${kind}/index.ts`, readFileSync(join(dir, kind, "index.ts"), "utf8")]);
    }
    for (const [k, v] of texts) expect(v.normalize("NFC"), k).not.toMatch(/(?<!con)s\u00e9quence/i);
  });

  it("puts the filming page in five short rules, with panning allowed", () => {
    for (const msgs of [de, fr, en]) {
      expect(msgs.filming.rules).toHaveLength(5);
      for (const r of msgs.filming.rules) expect(r.text.length, r.title).toBeLessThanOrEqual(80);
    }
    expect(de.filming.rules.map((r) => r.title)).toEqual(["Handy oder Kamera", "Hoch an die Mittellinie", "Beide Tore im Bild", "Fest ist am besten", "Schwenken geht"]);
  });

  it("uses no long dashes and no sharp s", () => {
    for (const msgs of [de, fr, en]) for (const [k, v] of leaves(msgs)) expect(v, k).not.toMatch(/[–—]/);
    for (const [k, v] of ref) expect(v, k).not.toContain("ß");
  });
});
