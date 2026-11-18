import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * The demo club and everything around it is invented (HC Tannengrün, TSV Nachtwind …). The
 * names of the earlier demo (real places on Lake Zurich) must not come back: not in the files the
 * website serves (public/, text and file names), not in its texts (src/messages, content). A
 * picture cannot be read here, so pictures with words in them are made by scripts
 * (scripts/product-shots, e.g. share-preview.mjs for the chat preview) and made again on a change.
 */
const OLD = ["Zürichsee", "Zurichsee", "Seewald", "Moosbach", "Bergtal", "Rebhalden", "Lindmatt", "Uferweg", "Seeblick", "Thalwil", "Horgen"];
const PATTERN = new RegExp(OLD.join("|"), "i");
/** files whose bytes are not text (their names are still checked) */
const BINARY = /\.(webp|png|jpe?g|gif|avif|ico|woff2?|ttf|otf|mp4|webm|m4s|pdf)$/i;

const site = join(__dirname, "..", "..");

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? files(path) : [path];
  });
}

describe("no names of the earlier demo", () => {
  it("in the names of the files in public/", () => {
    const hits = files(join(site, "public"))
      .map((f) => relative(site, f))
      .filter((f) => PATTERN.test(f));
    expect(hits).toEqual([]);
  });

  it("in the text files in public/, the messages and the content", () => {
    const hits = ["public", "src/messages", "content"]
      .flatMap((d) => files(join(site, d)))
      .filter((f) => !BINARY.test(f))
      .filter((f) => PATTERN.test(readFileSync(f, "utf8")))
      .map((f) => `${relative(site, f)}: ${readFileSync(f, "utf8").match(PATTERN)?.[0]}`);
    expect(hits).toEqual([]);
  });

  it("finds an old name where there is one", () => {
    expect(PATTERN.test("HC Zürichsee Herren 1")).toBe(true);
    expect(PATTERN.test("teilen-vorschau-thalwil.webp")).toBe(true);
    expect(PATTERN.test("HC Tannengrün Herren 1")).toBe(false);
  });
});
