/**
 * Design rules (docs/DESIGN.md, SPEC.md section 12) checked on every test run, so the redesign does not erode:
 * no browser dialogs, no symbol characters as controls, no long dashes in UI text, colours only
 * from tokens (files that draw courts, kits or video overlays may name colours), and the main
 * navigation never grows past four destinations (see nav-model.test.ts).
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const SRC = join(__dirname, "..");
const MESSAGES = join(__dirname, "..", "..", "messages");

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) return files(p);
    return /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name) ? [p] : [];
  });
}

const sources = files(SRC).map((p) => ({ path: relative(SRC, p), text: readFileSync(p, "utf8") }));

// drawings, courts, kits and third-party brand buttons legitimately use literal colours
const COLOUR_FILES = new Set([
  "app/app/[orgId]/matches/[matchId]/workspace.tsx",
  "app/app/[orgId]/teams/[teamId]/matches/new-match-form.tsx",
  "app/app/[orgId]/presentations/[presId]/remote/remote.tsx",
  "app/(einstieg)/onboarding/wizard.tsx",
  "app/layout.tsx",
  "app/manifest.ts",
  "components/video/mini-court.tsx",
  "components/anlauf/tactics-camera.tsx",
  "app/app/[orgId]/matches/[matchId]/video-stage.tsx",
  // the big screen of a collection: the dark camera bar colours
  "app/app/[orgId]/collections/[collectionId]/present/present-view.tsx",
  "app/app/[orgId]/matches/[matchId]/check/check-view.tsx",
  "app/app/[orgId]/collections/[collectionId]/page.tsx",
  "components/video/spotlight.tsx",
  "components/video/draw-layer.tsx",
  "components/video/shapes.ts",
  "components/tactics/board.tsx",
  "components/analysis/court-half.tsx",
  "components/analysis/court-calibration.tsx",
  "components/analysis/court-full.tsx",
  "components/analysis/goal-grid.tsx",
  "components/oauth-buttons.tsx",
  "components/presentation/slide-view.tsx",
  "lib/color.ts",
  "lib/kit.ts",
]);

// club-coloured areas of screens that are rebuilt in the following steps of SPEC.md section 13
const CLUB_AREA_LEGACY = ["components/domain/stage.tsx"];

describe("design rules", () => {
  it("uses the confirm dialog instead of window.confirm / alert / prompt", () => {
    const bad = sources.filter((f) => /window\.(confirm|alert|prompt)\(/.test(f.text) && !f.path.endsWith("ui/confirm.tsx"));
    expect(bad.map((f) => f.path)).toEqual([]);
  });

  it("uses icons, not symbol characters, for controls", () => {
    const glyphs = /[▶◀►◄⏸⏵⏯⏮⏭✓✔✕✖↑↓⬇⬆★☆⚑⚠✎✏🗑⟲↺↻➜➔▲▼❚⛶🔇🔊]/u;
    const bad = sources.filter((f) => glyphs.test(f.text.replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, "")));
    expect(bad.map((f) => f.path)).toEqual([]);
  });

  it("sets nothing that is read under 14 px; only mono labels may be 13 px (UX test H08)", () => {
    const css = readFileSync(join(SRC, "app", "globals.css"), "utf8");
    // text-xs is 14 px in this app (the token), not Tailwind's 12 px
    expect(css).toMatch(/--text-xs:\s*0\.875rem/);
    const tiny = /text-\[(?:\d|1[0-2])px\]|text-\[0\.(?:[0-6]\d*|7[0-4]\d*)rem\]|text-\[0\.75rem\]|text-\[0\.6875rem\]/;
    const thirteen = /text-\[13px\]|text-\[0\.8125rem\]/;
    const bad: string[] = [];
    for (const f of sources) {
      for (const m of f.text.matchAll(/(["'`])([^"'`\n]*?text-\[[^"'`\n]*?)\1/g)) {
        const cls = m[2]!;
        if (tiny.test(cls) || (thirteen.test(cls) && !cls.includes("font-mono"))) bad.push(`${f.path}: ${cls.slice(0, 80)}`);
      }
    }
    expect(bad).toEqual([]);
  });

  it("takes colours from tokens", () => {
    const hex = /["'`]#[0-9a-f]{3}(?:[0-9a-f]{3})?["'`]|#[0-9a-f]{6}\b/i;
    const bad = sources.filter((f) => hex.test(f.text) && !COLOUR_FILES.has(f.path.replaceAll("\\", "/")));
    expect(bad.map((f) => f.path)).toEqual([]);
  });

  // ---- SPEC.md section 12 (docs/design/ux-reset): the Anlauf rules ------------------------------

  it("has no rounded corners and no soft shadows", () => {
    // circles (rounded-full) are drawing marks: dots, avatars of the camera key, spinners
    const rounded = /(?<![\w-])rounded(?:-(?!full\b|none\b)[\w[\]-]+)?(?![\w-])/;
    const shadow = /(?<![\w-])shadow(?:-(?:sm|md|lg|xl|2xl))?(?![\w[-])/;
    const classes = (t: string) => (t.match(/"[^"\n]*"|`[^`]*`/g) ?? []).join(" ");
    const bad = sources.filter((f) => rounded.test(classes(f.text)) || shadow.test(classes(f.text)));
    expect(bad.map((f) => f.path)).toEqual([]);
  });

  it("writes no capitals and no letter-spacing", () => {
    const bad = sources.filter((f) => /(?<![\w-])(uppercase|tracking-(wide|wider|widest|\[\d))/.test(f.text));
    expect(bad.map((f) => f.path)).toEqual([]);
  });

  it("puts the club colour as an area only in the heads, the crest, the marker, the key and the share card", () => {
    const allowed = new Set([
      "components/anlauf/heads.tsx",
      "components/anlauf/blocks.tsx",
      "components/ui/page-header.tsx",
      "components/shell/club-mark.tsx",
      // the Keil beside the sign-in form
      "app/(site)/(auth)/layout.tsx",
      // the share card (how a shared collection arrives in a chat)
      "app/app/[orgId]/collections/[collectionId]/page.tsx",
      // the key "Tor wir" of the Spieltag
      "app/app/[orgId]/matches/[matchId]/live/live-view.tsx",
      "app/app/[orgId]/matches/[matchId]/marks/marks-view.tsx",
      ...CLUB_AREA_LEGACY,
    ]);
    const bad = sources.filter((f) => /(?<![\w-])bg-club(?![\w-])/.test(f.text) && !allowed.has(f.path.replaceAll("\\", "/")));
    expect(bad.map((f) => f.path)).toEqual([]);
    // the legacy list only shrinks
    for (const p of CLUB_AREA_LEGACY) expect(sources.find((f) => f.path.replaceAll("\\", "/") === p)?.text ?? "", p).toMatch(/(?<![\w-])bg-club(?![\w-])/);
  });

  it("slants headings, numerals, names, navigation and tabs only, never cells, fields or button labels", () => {
    // numerals (font-num, font-score) may stand anywhere; the slanted text face only in headings,
    // names and navigation. Paragraphs are not checked: a line of names is a <p>.
    const tag = /<(td|input|textarea|button)\b[^>]*?className=(?:"([^"]*)"|\{([^}]*)\})/g;
    const bad: string[] = [];
    for (const f of sources) {
      for (const m of f.text.matchAll(tag)) {
        const cls = `${m[2] ?? ""}${m[3] ?? ""}`;
        if (/\bfont-(slant|display|wide|narrow)\b/.test(cls) && !/role="tab"/.test(m[0])) bad.push(`${f.path}: <${m[1]}>`);
      }
    }
    expect(bad).toEqual([]);
  });

  it("uses yellow only with a word", () => {
    // a yellow element that closes itself carries no text
    const bad = sources.filter((f) => /<\w+\b[^>]*?\bbg-(attn|signal|resin)\b[^>]*?\/>/.test(f.text));
    expect(bad.map((f) => f.path)).toEqual([]);
  });

  it("has one match head per screen", () => {
    // a match switches between the Wurf head (tab Spiel) and the Streifen (Video, Zahlen) in one
    // component (match-head.tsx); more than one of either in a file is two heads on a screen
    const n = (text: string, tag: string) => (text.match(new RegExp(`<${tag}\\b`, "g")) ?? []).length;
    const bad = sources.filter((f) => (n(f.text, "WurfHead") > 1 || n(f.text, "Strip") > 1) && !f.path.startsWith("app/dev/"));
    expect(bad.map((f) => f.path)).toEqual([]);
  });

  it("has no arrows in UI text", () => {
    for (const locale of ["de-CH", "fr", "en"]) {
      const text = readFileSync(join(MESSAGES, `${locale}.json`), "utf8");
      expect(text.includes("→"), `${locale}.json contains an arrow`).toBe(false);
    }
  });

  it("draws navigation and domain icons itself", () => {
    const shell = sources.filter((f) => ["components/shell/app-shell.tsx", "components/shell/icons.tsx"].includes(f.path.replaceAll("\\", "/")));
    for (const f of shell) expect(f.text.includes("Sparkles"), f.path).toBe(false);
    expect(sources.some((f) => /\bSparkles\b/.test(f.text)), "the sparkle symbol for AI").toBe(false);
  });

  it("has no long dashes in UI text", () => {
    for (const locale of ["de-CH", "fr", "en"]) {
      const text = readFileSync(join(MESSAGES, `${locale}.json`), "utf8");
      expect(text.includes("—"), `${locale}.json contains an em dash`).toBe(false);
    }
  });

  it("writes Swiss German without ß", () => {
    expect(readFileSync(join(MESSAGES, "de-CH.json"), "utf8").includes("ß")).toBe(false);
  });
});
