/* Handball Intelligence, the chosen direction "Taktik": a play drawn on the coach's board.
 *
 *   npm i opentype.js@1.3.4           (once, anywhere on NODE_PATH)
 *   node docs/design/brand2/taktik/build.js     writes varianten/, final/*.svg, index.html
 *   node docs/design/brand2/taktik/render.js    writes final/*.png and shots/
 *
 * One function draws every version of the mark from a few switches: the stroke (hand, geometric,
 * mixed), how much court is shown, which play is drawn, and the colours. Type is outlined from
 * the OFL fonts in ./fonts, so no SVG needs a font.
 */
"use strict";
const fs = require("fs"), path = require("path"), opentype = require("opentype.js");
const here = __dirname, F = {};
function font(n) { return F[n] || (F[n] = opentype.loadSync(path.join(here, "fonts", n + ".ttf"))); }
function text(fn, s, x, y, size, o = {}) {
  const f = font(fn), k = size / f.unitsPerEm, tr = (o.track || 0) * size, gl = f.stringToGlyphs(s);
  let w = 0; gl.forEach((g, i) => { w += g.advanceWidth * k + (i < gl.length - 1 ? f.getKerningValue(g, gl[i + 1]) * k + tr : 0); });
  let cx = o.anchor === "end" ? x - w : o.anchor === "middle" ? x - w / 2 : x; const parts = [];
  gl.forEach((g, i) => { parts.push(g.getPath(cx, y, size).toPathData(2)); cx += g.advanceWidth * k + (i < gl.length - 1 ? f.getKerningValue(g, gl[i + 1]) * k + tr : 0); });
  const bb = f.getPath(s, 0, 0, size).getBoundingBox();
  return { d: parts.join(""), w, top: bb.y1, bottom: bb.y2 };
}
const r2 = (v) => Math.round(v * 10) / 10;

/* ---------- colours ---------- */
const INK = "#111316", BLUE = "#1d47d1", RED = "#e1251b", BOARD = "#f7f8f6";
/* palette: court, own player and arrow, opponent */
function palette(c) {
  if (c === "two") return { court: INK, us: BLUE, arrow: BLUE, them: RED, goal: INK };
  if (c === "accent") return { court: INK, us: INK, arrow: BLUE, them: INK, goal: INK };
  if (c === "ink") return { court: INK, us: INK, arrow: INK, them: INK, goal: INK };
  return { court: c, us: c, arrow: c, them: c, goal: c }; /* any single colour, e.g. white */
}

/* ---------- hand: seeded wobble ---------- */
function rng(seed) { let s = seed >>> 0 || 1; return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; }; }
function cubicPts(p0, p1, p2, p3, n) {
  const out = [];
  for (let i = 0; i <= n; i++) { const t = i / n, u = 1 - t; out.push([u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0], u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1]]); }
  return out;
}
function smooth(p) {
  let d = "M" + r2(p[0][0]) + " " + r2(p[0][1]);
  for (let i = 1; i < p.length - 1; i++) { const mx = (p[i][0] + p[i + 1][0]) / 2, my = (p[i][1] + p[i + 1][1]) / 2; d += "Q" + r2(p[i][0]) + " " + r2(p[i][1]) + " " + r2(mx) + " " + r2(my); }
  const l = p[p.length - 1]; return d + "L" + r2(l[0]) + " " + r2(l[1]);
}
/* a hand-drawn version of a curve: small perpendicular drift, more in the middle than at the ends */
function wobble(pts, amp, seed) {
  const r = rng(seed), n = pts.length - 1; let drift = 0;
  return pts.map((p, i) => {
    if (i === 0 || i === n) return p;
    const a = pts[Math.max(0, i - 1)], b = pts[Math.min(n, i + 1)], dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1;
    drift = drift * 0.86 + (r() - 0.5) * amp; const k = Math.sin(Math.PI * i / n);
    return [p[0] - dy / l * drift * k, p[1] + dx / l * drift * k];
  });
}

/* ---------- the parts ---------- */
const S = 20, LINE = 64, GX0 = 256 - 1.5 * S, GX1 = 256 + 1.5 * S; /* 22 px per metre, end line at y 64 */
function court(kind, pal, st) {
  if (kind === "none") return "";
  const w = st.court;
  let s = `<path d="M24 ${LINE}H488" stroke="${pal.court}" stroke-width="${w}" stroke-linecap="round" fill="none"/>`;
  s += `<rect x="${GX0}" y="${LINE - 22}" width="${GX1 - GX0}" height="22" rx="3" fill="${pal.goal}"/>`;
  if (kind === "goal") return s;
  const R6 = 6 * S;
  s += `<path d="M${GX0 - R6} ${LINE}A${R6} ${R6} 0 0 0 ${GX0} ${LINE + R6}H${GX1}A${R6} ${R6} 0 0 0 ${GX1 + R6} ${LINE}" stroke="${pal.court}" stroke-width="${w}" fill="none" stroke-linecap="round"/>`;
  if (kind === "d9") {
    const R9 = 9 * S;
    s += `<path d="M${GX0 - R9} ${LINE}A${R9} ${R9} 0 0 0 ${GX0} ${LINE + R9}H${GX1}A${R9} ${R9} 0 0 0 ${GX1 + R9} ${LINE}" stroke="${pal.court}" stroke-width="${w}" fill="none" stroke-linecap="round" stroke-dasharray="0.1 ${w * 2.6}"/>`;
  }
  return s;
}
function circleO(cx, cy, r, col, w, hand, seed) {
  if (!hand) return `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${col}" stroke-width="${w}"/>`;
  const rr = rng(seed), p = [], a0 = -2.2 + rr() * 0.4, n = 18;
  for (let i = 0; i <= n; i++) { const a = a0 + (i / n) * Math.PI * 2.1, k = 1 + (rr() - 0.5) * 0.07 - i * 0.003; p.push([cx + Math.cos(a) * r * k, cy + Math.sin(a) * r * k]); }
  return `<path d="${smooth(p)}" fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;
}
function cross(cx, cy, h, col, w, hand, seed) {
  if (!hand) return `<path d="M${cx - h} ${cy - h}L${cx + h} ${cy + h}M${cx + h} ${cy - h}L${cx - h} ${cy + h}" stroke="${col}" stroke-width="${w}" stroke-linecap="round" fill="none"/>`;
  const r = rng(seed), j = () => (r() - 0.5) * h * 0.18;
  return `<path d="M${r2(cx - h + j())} ${r2(cy - h + j())}Q${r2(cx + j() * 2)} ${r2(cy + j() * 2)} ${r2(cx + h + j())} ${r2(cy + h + j())}M${r2(cx + h + j())} ${r2(cy - h * 1.05)}Q${r2(cx + j() * 2)} ${r2(cy + j() * 2)} ${r2(cx - h * 0.95)} ${r2(cy + h + j())}" stroke="${col}" stroke-width="${w}" stroke-linecap="round" fill="none"/>`;
}
function arrow(c, col, w, hand, seed, dashed) {
  let pts = cubicPts(c[0], c[1], c[2], c[3], 14);
  if (hand) pts = wobble(pts, 3.2, seed);
  const e = pts[pts.length - 1], b = pts[pts.length - 4], ang = Math.atan2(e[1] - b[1], e[0] - b[0]), L = w * 1.7, sp = hand ? 0.66 : 0.62;
  const h1 = [e[0] - Math.cos(ang - sp) * L, e[1] - Math.sin(ang - sp) * L], h2 = [e[0] - Math.cos(ang + sp * (hand ? 1.12 : 1)) * L * (hand ? 1.08 : 1), e[1] - Math.sin(ang + sp * (hand ? 1.12 : 1)) * L * (hand ? 1.08 : 1)];
  const body = hand ? smooth(pts) : `M${c[0][0]} ${c[0][1]}C${c[1][0]} ${c[1][1]} ${c[2][0]} ${c[2][1]} ${c[3][0]} ${c[3][1]}`;
  return `<path d="${body}" fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"${dashed ? ` stroke-dasharray="${w * 0.7} ${w * 1.1}"` : ""}/>`
    + `<path d="M${r2(h1[0])} ${r2(h1[1])}L${r2(e[0])} ${r2(e[1])}L${r2(h2[0])} ${r2(h2[1])}" fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;
}

/* the plays: own players (O), defenders (X), the run (arrow) */
const PLAYS = {
  wurf: { name: "Wurf am Verteidiger vorbei", us: [[148, 414]], them: [[340, 330]], runs: [[[166, 372], [180, 300], [212, 252], [252, 214]]] },
  durch: { name: "Durchbruch zwischen zwei Verteidigern", xh: 24, us: [[256, 432]], them: [[180, 222], [332, 222]], runs: [[[256, 390], [228, 340], [282, 290], [256, 206]]] },
  kreis: { name: "Lauf an den Kreis", us: [[118, 410]], them: [[250, 300]], runs: [[[156, 412], [290, 440], [372, 360], [366, 226]]] },
  kreuz: { name: "Kreuzen im Rückraum", us: [[150, 440], [362, 440]], them: [[256, 262]], runs: [[[172, 400], [200, 340], [300, 330], [350, 248]], [[340, 400], [312, 340], [212, 330], [162, 248], true]] }
};
const STYLES = { hand: { court: 10, w: 26, handO: true, handX: true, handA: true }, geo: { court: 10, w: 26 }, mix: { court: 10, w: 26, handA: true } };

let MID = 0;
function mark(o) {
  const st = STYLES[o.stroke], pal = palette(o.color), pl = PLAYS[o.play], seed = o.seed || 7, X = pl.xh || 30;
  const players = (col, w, dashOff) => {
    let s = "";
    pl.them.forEach((p, i) => { s += cross(p[0], p[1], X, col.them, w, st.handX, seed + 11 * i); });
    pl.us.forEach((p, i) => { s += circleO(p[0], p[1], 32, col.us, w, st.handO, seed + 31 * i); });
    pl.runs.forEach((c, i) => { s += arrow(c, col.arrow, w, st.handA, seed + 97 * i, dashOff ? false : c[4]); });
    return s;
  };
  /* the court lines stop short of every player and of the run, as a coach lifts the pen */
  const id = "km" + (++MID), k = { them: "#000", us: "#000", arrow: "#000" };
  const cut = `<defs><mask id="${id}" maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512"><rect width="512" height="512" fill="#fff"/>${players(k, st.w + 22, true)}</mask></defs>`;
  const c = court(o.court, pal, st);
  return (c ? cut + `<g mask="url(#${id})">${c}</g>` : "") + players(pal, st.w);
}
const svg = (vb, body, extra = "") => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vb}"${extra}>${body}</svg>`;

/* ---------- the ten variants ---------- */
const V = [
  { id: "v01", label: "Hand · Wurf · Tor und Torraum", stroke: "hand", court: "d", play: "wurf" },
  { id: "v02", label: "Geometrisch · Wurf · Tor und Torraum", stroke: "geo", court: "d", play: "wurf" },
  { id: "v03", label: "Mischung · Wurf · Tor und Torraum", stroke: "mix", court: "d", play: "wurf" },
  { id: "v04", label: "Mischung · Wurf · nur Kreis, Kreuz, Pfeil", stroke: "mix", court: "none", play: "wurf" },
  { id: "v05", label: "Mischung · Wurf · nur Tor", stroke: "mix", court: "goal", play: "wurf" },
  { id: "v06", label: "Mischung · Wurf · Tor, Torraum, 9 m", stroke: "mix", court: "d9", play: "wurf" },
  { id: "v07", label: "Mischung · Durchbruch · Tor und Torraum", stroke: "mix", court: "d", play: "durch" },
  { id: "v08", label: "Mischung · Lauf an den Kreis · Tor und Torraum", stroke: "mix", court: "d", play: "kreis" },
  { id: "v09", label: "Mischung · Kreuzen · Tor und Torraum", stroke: "mix", court: "d", play: "kreuz" },
  { id: "v10", label: "Mischung · Durchbruch · Tor, Torraum, 9 m", stroke: "mix", court: "d9", play: "durch" }
];
/* the recommendation */
const FINAL = { stroke: "mix", court: "d9", play: "durch", seed: 7 };
const SECOND = { stroke: "mix", court: "d", play: "durch", seed: 7 };

/* ---------- small versions, drawn on the pixel grid ---------- */
function px32(col, acc) {
  const a = acc || col;
  return `<path d="M2 5H30" stroke="${col}" stroke-width="2" stroke-linecap="square"/><rect x="13" y="2" width="6" height="3" fill="${col}"/>`
    + `<path d="M6 5A7 7 0 0 0 13 12H19A7 7 0 0 0 26 5" fill="none" stroke="${col}" stroke-width="2"/>`
    + `<path d="M7 15L11 19M11 15L7 19M21 15L25 19M25 15L21 19" stroke="${col}" stroke-width="2.4" stroke-linecap="round"/>`
    + `<circle cx="16" cy="26.5" r="3" fill="none" stroke="${a}" stroke-width="2.4"/>`
    + `<path d="M16 22.5V15M13 17.5L16 14.5L19 17.5" fill="none" stroke="${a}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>`;
}
function px16(col, acc) {
  const a = acc || col;
  return `<path d="M1 2.5H15" stroke="${col}" stroke-width="1"/><rect x="6" y="1" width="4" height="2" fill="${col}"/>`
    + `<path d="M3 3A3.5 3.5 0 0 0 6.5 6.5H9.5A3.5 3.5 0 0 0 13 3" fill="none" stroke="${col}" stroke-width="1.2"/>`
    + `<path d="M3 8.5L5 10.5M5 8.5L3 10.5M11 8.5L13 10.5M13 8.5L11 10.5" stroke="${col}" stroke-width="1.3" stroke-linecap="round"/>`
    + `<circle cx="8" cy="13.6" r="1.6" fill="none" stroke="${a}" stroke-width="1.3"/>`
    + `<path d="M8 11.4V7.6M6.6 9L8 7.6L9.4 9" fill="none" stroke="${a}" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>`;
}

/* ---------- wordmarks ---------- */
const WM = [
  { id: "kanit", name: "Kanit ExtraBold Italic", font: "Kanit-ExtraBoldItalic", track: -0.01, why: "die Schrift der App «Anlauf». Schräg wie der Pfeil, sportlich, passt zum Titel in der App." },
  { id: "archivo", name: "Archivo ExtraBold", font: "Archivo-ExtraBold", track: -0.03, why: "aufrecht, kräftig, ruhig. Lässt dem Zeichen die Bewegung." },
  { id: "familjen", name: "Familjen Grotesk Bold", font: "FamiljenGrotesk-Bold", track: -0.02, why: "schmaler, mit kleinen Eigenheiten im g und e. Freundlicher, weniger Sportplakat." },
  { id: "bricolage", name: "Bricolage Grotesque ExtraBold", font: "BricolageGrotesque-ExtraBold", track: -0.03, why: "eigenwillig, fast handgemacht. Nimmt den Filzstift auf, wird aber schnell verspielt." }
];
const WM_REC = "kanit";
/* layouts: quer (one line), zweizeilig (two lines beside the mark), gestapelt (mark above) */
function lockup(wm, layout, o, pal2) {
  const p = pal2 || { mark: "two", ink: INK, accent: BLUE };
  const m = mark(Object.assign({}, o, { color: p.mark }));
  const f = wm.font, sz = 150;
  if (layout === "quer") {
    const t = text(f, "Handball Intelligence", 0, 0, sz, { track: wm.track }), x = 600, base = 256 + (-(t.top) - t.bottom) / 2 + t.bottom - 6;
    const a = text(f, "Handball ", x, 300, sz, { track: wm.track }), b = text(f, "Intelligence", x + a.w, 300, sz, { track: wm.track });
    return { vb: `0 0 ${x + a.w + b.w + 30} 512`, body: m + `<path d="${a.d}" fill="${p.ink}"/><path d="${b.d}" fill="${p.accent}"/>` };
  }
  if (layout === "zweizeilig") {
    const a = text(f, "Handball", 590, 236, sz, { track: wm.track }), b = text(f, "Intelligence", 590, 392, sz, { track: wm.track });
    return { vb: `0 0 ${590 + Math.max(a.w, b.w) + 30} 512`, body: m + `<path d="${a.d}" fill="${p.ink}"/><path d="${b.d}" fill="${p.accent}"/>` };
  }
  const a = text(f, "Handball", 256, 650, 120, { track: wm.track, anchor: "middle" }), b = text(f, "Intelligence", 256, 780, 120, { track: wm.track, anchor: "middle" });
  const W = Math.max(a.w, b.w, 512), x0 = 256 - W / 2 - 20;
  return { vb: `${x0} 0 ${W + 40} 820`, body: m + `<path d="${a.d}" fill="${p.ink}"/><path d="${b.d}" fill="${p.accent}"/>` };
}

/* ---------- write files ---------- */
const W = (rel, s) => { const f = path.join(here, rel); fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, s + "\n"); };
V.forEach((v) => { W(`varianten/${v.id}.svg`, svg("0 0 512 512", mark(Object.assign({ color: "two" }, v)))); });

const wmRec = WM.find((w) => w.id === WM_REC);
const fin = (c) => mark(Object.assign({}, FINAL, { color: c }));
const out = {
  "zeichen.svg": svg("0 0 512 512", fin("two")),
  "zeichen-tinte.svg": svg("0 0 512 512", fin("ink")),
  "zeichen-tinte-akzent.svg": svg("0 0 512 512", fin("accent")),
  "zeichen-negativ.svg": svg("0 0 512 512", `<rect width="512" height="512" fill="${INK}"/>` + mark(Object.assign({}, FINAL, { color: "#ffffff" }))),
  "zeichen-weiss.svg": svg("0 0 512 512", fin("#ffffff")),
  "favicon-16.svg": svg("0 0 16 16", px16(INK, BLUE)),
  "favicon-32.svg": svg("0 0 32 32", px32(INK, BLUE)),
  "app-icon.svg": svg("0 0 1024 1024", `<rect width="1024" height="1024" fill="${BOARD}"/><g transform="translate(-6 34) scale(2.02)">${fin("two")}</g>`),
  "app-icon-maske.svg": svg("0 0 1024 1024", `<rect width="1024" height="1024" fill="${BOARD}"/><g transform="translate(240 250) scale(1.0625)">${fin("two")}</g>`),
  "app-icon-einfarbig.svg": svg("0 0 1024 1024", `<g transform="translate(240 250) scale(1.0625)">${fin("#ffffff")}</g>`)
};
[["quer", "quer"], ["zweizeilig", "zweizeilig"], ["gestapelt", "gestapelt"]].forEach(([l, n]) => {
  const c = lockup(wmRec, l, FINAL), k = lockup(wmRec, l, FINAL, { mark: "ink", ink: INK, accent: INK }), w = lockup(wmRec, l, FINAL, { mark: "#ffffff", ink: "#ffffff", accent: "#ffffff" });
  out[`wortmarke-${n}.svg`] = svg(c.vb, c.body);
  out[`wortmarke-${n}-einfarbig.svg`] = svg(k.vb, k.body);
  out[`wortmarke-${n}-negativ.svg`] = svg(w.vb, `<rect x="-2000" y="-2000" width="6000" height="6000" fill="${INK}"/>` + w.body);
  out[`wortmarke-${n}-weiss.svg`] = svg(w.vb, w.body);
});
/* open graph: 1200 x 630 */
{
  const a = text(wmRec.font, "Handball", 640, 300, 118, { track: wmRec.track }), b = text(wmRec.font, "Intelligence", 640, 420, 118, { track: wmRec.track });
  const t = text("Archivo-ExtraBold", "Spielanalyse für Handballtrainerinnen und -trainer", 640, 520, 30, { track: 0 });
  out["open-graph.svg"] = svg("0 0 1200 630", `<rect width="1200" height="630" fill="${BOARD}"/><g transform="translate(70 70) scale(0.95)">${fin("two")}</g><path d="${a.d}" fill="${INK}"/><path d="${b.d}" fill="${BLUE}"/><path d="${t.d}" fill="#5a6068"/>`);
}
Object.keys(out).forEach((n) => W("final/" + n, out[n]));

/* everything the page shows, as data for the page script */
const page = { V: V.map((v) => ({ id: v.id, label: v.label, svg: svg("0 0 512 512", mark(Object.assign({ color: "two" }, v))), small: svg("0 0 512 512", mark(Object.assign({ color: "ink" }, v))) })) };
page.colors = ["two", "ink", "accent"].map((c) => svg("0 0 512 512", fin(c)));
page.layout = {
  hoch: svg("40 0 432 560", fin("two").replace(/^/, "")),
  quadrat: svg("0 0 512 512", fin("two")),
  quer: svg("0 0 640 380", `<g transform="translate(640 -66) rotate(90)">${fin("two")}</g>`)
};
page.wm = WM.map((w) => ({ id: w.id, name: w.name, why: w.why, quer: (() => { const l = lockup(w, "quer", FINAL); return svg(l.vb, l.body); })(), zwei: (() => { const l = lockup(w, "zweizeilig", FINAL); return svg(l.vb, l.body); })(), stapel: (() => { const l = lockup(w, "gestapelt", FINAL); return svg(l.vb, l.body); })() }));
page.out = out;
page.second = svg("0 0 512 512", mark(Object.assign({}, SECOND, { color: "two" })));
fs.writeFileSync(path.join(here, "data.json"), JSON.stringify(page));
console.log("ok", Object.keys(out).length, "final files,", V.length, "variants");
