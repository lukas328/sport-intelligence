import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import deCH from "../../messages/de-CH.json";

const SRC = fileURLToPath(new URL("..", import.meta.url));

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) return files(p);
    return /\.tsx?$/.test(name) && !name.endsWith(".test.ts") ? [p] : [];
  });
}

function has(path: string): boolean {
  let node: unknown = deCH;
  for (const part of path.split(".")) {
    if (typeof node !== "object" || node === null || !(part in node)) return false;
    node = (node as Record<string, unknown>)[part];
  }
  return typeof node === "string";
}

describe("translation keys used in code", () => {
  it("exist in de-CH", () => {
    const missing: string[] = [];
    for (const file of files(SRC)) {
      const code = readFileSync(file, "utf8");
      const namespaces = [...code.matchAll(/(?:useTranslations|getTranslations)\("([\w.]+)"\)/g)].map((m) => m[1]!);
      for (const m of code.matchAll(/\bt\("([\w.-]+)"/g)) {
        const key = m[1]!;
        if (!has(key) && !namespaces.some((ns) => has(`${ns}.${key}`))) missing.push(`${file.replace(SRC, "")}: ${key}`);
      }
    }
    expect(missing).toEqual([]);
  });
});
