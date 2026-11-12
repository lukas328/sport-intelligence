/**
 * Design rules (docs/DESIGN.md) checked on every test run, so the redesign does not erode:
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
  "app/(site)/onboarding/wizard.tsx",
  "app/layout.tsx",
  "app/manifest.ts",
  "components/video/mini-court.tsx",
  "components/anlauf/tactics-camera.tsx",
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

  it("takes colours from tokens", () => {
    const hex = /["'`]#[0-9a-f]{3}(?:[0-9a-f]{3})?["'`]|#[0-9a-f]{6}\b/i;
    const bad = sources.filter((f) => hex.test(f.text) && !COLOUR_FILES.has(f.path.replaceAll("\\", "/")));
    expect(bad.map((f) => f.path)).toEqual([]);
  });

  it("keeps the angular form: no soft panels or pills, no coloured side borders", () => {
    // 2xl/3xl radii were the soft-panel look; padded rounded-full elements were pills; a thick
    // coloured left border on a rounded box is the best-known sign of generated UI
    const soft = /\brounded-(2xl|3xl)\b/;
    const pill = /className="[^"]*\brounded-full\b[^"]*\bpx-\d/;
    const sideBorder = /\bborder-l-(4|8|\[)/;
    const bad = sources.filter((f) => soft.test(f.text) || pill.test(f.text) || sideBorder.test(f.text));
    expect(bad.map((f) => f.path)).toEqual([]);
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
