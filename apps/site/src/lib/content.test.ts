import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { HELP } from "../../content/help";
import { BLOG } from "../../content/blog";
import { LOCALES } from "./i18n";

const root = join(__dirname, "..", "..");
const web = join(root, "..", "web", "src", "components", "support", "help-map.ts");

describe("content", () => {
  it("has at least 15 help articles, each in every language", () => {
    expect(HELP.length).toBeGreaterThanOrEqual(15);
    for (const locale of LOCALES) {
      const files = readdirSync(join(root, "content", "help", locale)).filter((f) => f.endsWith(".mdx"));
      expect(files.sort()).toEqual(HELP.map((h) => `${h.slug}.mdx`).sort());
    }
  });

  it("covers every slug the app links to as context help", () => {
    const slugs = [...readFileSync(web, "utf8").matchAll(/"([a-z-]+)"\]/g)].map((m) => m[1]);
    expect(slugs.length).toBeGreaterThan(5);
    for (const slug of [...slugs, "erste-schritte"]) expect(HELP.map((h) => h.slug)).toContain(slug);
  });

  it("has every blog post and legal page in every language", () => {
    for (const locale of LOCALES) {
      for (const post of BLOG) expect(existsSync(join(root, "content", "blog", locale, `${post.slug}.mdx`))).toBe(true);
      for (const page of ["agb", "datenschutz", "impressum"])
        expect(existsSync(join(root, "content", "legal", locale, `${page}.mdx`))).toBe(true);
    }
  });

  it("uses no long dashes and no sharp s in Swiss German texts", () => {
    const dirs = ["help", "blog", "legal"].flatMap((d) => LOCALES.map((l) => join(root, "content", d, l)));
    for (const dir of dirs.filter(existsSync)) {
      for (const f of readdirSync(dir)) {
        const text = readFileSync(join(dir, f), "utf8");
        expect(text, f).not.toMatch(/[–—]/);
        if (dir.endsWith("/de")) expect(text, f).not.toContain("ß");
      }
    }
  });
});
