/* Logos for "Handball Intelligence", field: things of the sport and type.
 *
 *   npm i opentype.js@1.3.4        (once, anywhere on NODE_PATH)
 *   node docs/design/brand2/dinge/build.js
 *
 * Every word is converted to outlines from the fonts in ./fonts (all SIL OFL), so the SVGs in
 * ./logos need no font. Writes logos/*.svg and index.html. Each idea is one function that returns
 * its mark, its lockup and its colours; the page and the mock-ups are built from those.
 */
"use strict";
const fs = require("fs"), path = require("path"), opentype = require("opentype.js");
const here = __dirname, F = {};
function font(n) { return F[n] || (F[n] = opentype.loadSync(path.join(here, "fonts", n + ".ttf"))); }
/* text as one path; returns d, width and the ink box */
function text(fn, s, x, y, size, o = {}) {
  const f = font(fn), k = size / f.unitsPerEm, tr = (o.track || 0) * size, gl = f.stringToGlyphs(s);
  let w = 0;
  gl.forEach((g, i) => { w += g.advanceWidth * k + (i < gl.length - 1 ? f.getKerningValue(g, gl[i + 1]) * k + tr : 0); });
  let cx = o.anchor === "end" ? x - w : o.anchor === "middle" ? x - w / 2 : x;
  const x0 = cx, parts = [];
  gl.forEach((g, i) => {
    parts.push(g.getPath(cx, y, size).toPathData(2));
    cx += g.advanceWidth * k + (i < gl.length - 1 ? f.getKerningValue(g, gl[i + 1]) * k + tr : 0);
  });
  return { d: parts.join(""), w, x0 };
}
const P = (d, fill, extra = "") => `<path d="${d}" fill="${fill}"${extra}/>`;
const svg = (vb, body, attrs = "") => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vb}"${attrs}>${body}</svg>`;

/* a bar in alternating bands; corners start with colour a */
function bands(x, y, w, h, seg, a, b, vertical) {
  let out = "", n = Math.round((vertical ? h : w) / seg); if (n % 2 === 0) n += 1; /* odd: both ends in colour a, as on a real goal */
  const s = (vertical ? h : w) / n;
  for (let i = 0; i < n; i++) {
    const c = i % 2 ? b : a;
    out += vertical ? `<rect x="${x}" y="${(y + i * s).toFixed(2)}" width="${w}" height="${(s + 0.4).toFixed(2)}" fill="${c}"/>`
      : `<rect x="${(x + i * s).toFixed(2)}" y="${y}" width="${(s + 0.4).toFixed(2)}" height="${h}" fill="${c}"/>`;
  }
  return out;
}

/* the ball: one broad curved band across a plain disc and a thin seam on each side of it. One
   band reads as a modern handball; several parallel bands read as a beach ball. */
let BID = 0;
function drawBall(cx, cy, r, base, panel, edge, ew) {
  const id = "bc" + (++BID), f = (v) => v.toFixed(1);
  const band = `M${f(cx - r * 1.2)} ${f(cy + r * 0.55)} C ${f(cx - r * 0.5)} ${f(cy - r * 0.15)}, ${f(cx + r * 0.2)} ${f(cy - r * 0.55)}, ${f(cx + r * 1.2)} ${f(cy - r * 0.62)} L ${f(cx + r * 1.2)} ${f(cy - r * 0.08)} C ${f(cx + r * 0.3)} ${f(cy - r * 0.05)}, ${f(cx - r * 0.35)} ${f(cy + r * 0.3)}, ${f(cx - r * 0.95)} ${f(cy + r * 1.1)} Z`;
  return `<defs><clipPath id="${id}"><circle cx="${cx}" cy="${cy}" r="${r}"/></clipPath></defs>`
    + `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${base}"/>`
    + `<path d="${band}" fill="${panel}" clip-path="url(#${id})"/>`
    + (edge ? `<circle cx="${cx}" cy="${cy}" r="${f(r - ew / 2)}" fill="none" stroke="${edge}" stroke-width="${ew}"/>` : "");
}

const IDEAS = [];

/* ============ 1 PFOSTEN: the two l of "handball" are the posts of a goal ============ */
IDEAS.push((() => {
  const C = { ink: "#121417", red: "#e1251b", white: "#ffffff", net: "#c4c9cf", bg: "#ffffff" };
  function lockup(m) { /* m = mono colour or null */
    const red = m || C.red, wh = m ? "transparent" : C.white, ink = m || C.ink, net = m ? m : C.net;
    const S = 300, base = 300, g = font("Anton"), k = S / g.unitsPerEm;
    const pw = (436 - 72) * k, ph = 1760 * k, word = text("Anton", "handba", 0, base, S);
    const gx = word.w + 10, gw = ph * 1.32, top = base - ph;
    let goal = "";
    /* net: a light grid behind the frame */
    for (let x = gx + pw + 30; x < gx + gw - pw - 8; x += 30) goal += `<line x1="${x}" x2="${x}" y1="${top + pw}" y2="${base}" stroke="${net}" stroke-width="2" opacity="${m ? 0.3 : 1}"/>`;
    for (let y = top + pw + 30; y < base - 4; y += 30) goal += `<line x1="${gx + pw}" x2="${gx + gw - pw}" y1="${y}" y2="${y}" stroke="${net}" stroke-width="2" opacity="${m ? 0.3 : 1}"/>`;
    const seg = pw * 1.25;
    goal += bands(gx, top, pw, ph, seg, red, wh, true) + bands(gx + gw - pw, top, pw, ph, seg, red, wh, true) + bands(gx, top, gw, pw, seg, red, wh, false);
    /* outline so the white bands read as part of the frame */
    goal += `<path d="M${gx} ${base}V${top}H${gx + gw}V${base}H${gx + gw - pw}V${top + pw}H${gx + pw}V${base}Z" fill="none" stroke="${red}" stroke-width="5" stroke-linejoin="miter"/>`;
    const W = gx + gw, sub = text("Archivo-ExpandedBold", "INTELLIGENCE", W, base + 78, 50.5, { track: 0.21, anchor: "end" });
    return { body: P(word.d, ink) + goal + P(sub.d, ink), vb: `-6 ${top - 6} ${W + 12} ${base + 90 - top}` };
  }
  function mark(m, onDark) {
    const red = m || C.red, wh = m ? "transparent" : C.white, pw = 52, ph = 300, gw = 450, x = 31, top = 106, base = top + ph;
    let goal = "";
    const net = onDark ? "rgb(255 255 255 / .28)" : m ? "rgb(0 0 0 / .25)" : C.net;
    for (let xx = x + pw + 38; xx < x + gw - pw - 10; xx += 38) goal += `<line x1="${xx}" x2="${xx}" y1="${top + pw}" y2="${base}" stroke="${net}" stroke-width="3"/>`;
    for (let y = top + pw + 38; y < base - 6; y += 38) goal += `<line x1="${x + pw}" x2="${x + gw - pw}" y1="${y}" y2="${y}" stroke="${net}" stroke-width="3"/>`;
    goal += bands(x, top, pw, ph, 62, red, wh, true) + bands(x + gw - pw, top, pw, ph, 62, red, wh, true) + bands(x, top, gw, pw, 62, red, wh, false);
    goal += `<path d="M${x} ${base}V${top}H${x + gw}V${base}H${x + gw - pw}V${top + pw}H${x + pw}V${base}Z" fill="none" stroke="${red}" stroke-width="7"/>`;
    return goal;
  }
  return {
    key: "pfosten", name: "Pfosten", kind: "Wortmarke", font: "Anton, Archivo Expanded",
    see: "Das Wort «handball», und die zwei l am Ende sind ein Handballtor mit rot-weissen Pfosten.",
    idea: "Ein einziger Einfall: Die zwei l von «handball» stehen auseinander und tragen eine Latte. Mehr braucht es nicht, um zu sagen, um welchen Sport es geht. Rot-weiss gestreifte Pfosten gibt es nur im Handball.",
    colors: [["Torrot", C.red], ["Tinte", C.ink], ["Netzgrau", C.net]],
    lockup, mark, iconBg: C.ink, iconMark: () => mark(null, true), scene: "banner"
  };
})());

/* ============ 2 WINKEL: the goal from the front, the ball in the top corner ============ */
IDEAS.push((() => {
  const C = { navy: "#0d1b3d", red: "#e1251b", white: "#ffffff", ball: "#ffc72c" };
  function goal(m, onDark) {
    const red = m || C.red, wh = m ? (onDark ? "transparent" : "transparent") : C.white, edge = m || (onDark ? "transparent" : C.navy);
    const t = 44, x = 40, y = 112, w = 432, h = 300, b = y + h;
    let s = "";
    const net = onDark ? "rgb(255 255 255 / .22)" : m ? "rgb(0 0 0 / .18)" : "rgb(13 27 61 / .16)";
    for (let xx = x + t + 24; xx < x + w - t; xx += 24) s += `<line x1="${xx}" x2="${xx}" y1="${y + t}" y2="${b}" stroke="${net}" stroke-width="3"/>`;
    for (let yy = y + t + 24; yy < b; yy += 24) s += `<line x1="${x + t}" x2="${x + w - t}" y1="${yy}" y2="${yy}" stroke="${net}" stroke-width="3"/>`;
    s += bands(x, y, t, h, 50, red, wh, true) + bands(x + w - t, y, t, h, 50, red, wh, true) + bands(x, y, w, t, 432 / 9, red, wh, false);
    s += `<path d="M${x} ${b}V${y}H${x + w}V${b}H${x + w - t}V${y + t}H${x + t}V${b}Z" fill="none" stroke="${edge}" stroke-width="6" stroke-linejoin="round"/>`;
    /* the ball, just under the crossbar in the far corner */
    const cx = x + w - t - 72, cy = y + t + 72, r = 66, bc = m ? (onDark ? m : "transparent") : C.ball, bs = m ? (onDark ? "#000" : m) : C.navy;
    s += drawBall(cx, cy, r, m ? "none" : C.ball, m || C.navy, m || C.navy, 7);
    return s;
  }
  function lockup(m) {
    const ink = m || C.navy, a = text("BricolageGrotesque-ExtraBold", "Handball", 560, 250, 150, { track: -0.025 }), b = text("BricolageGrotesque-ExtraBold", "Intelligence", 560, 392, 150, { track: -0.025 });
    return { body: goal(m) + P(a.d, ink) + P(b.d, ink), vb: `30 100 ${560 + Math.max(a.w, b.w) - 20} 330` };
  }
  return {
    key: "winkel", name: "Winkel", kind: "Zeichen und Wortmarke", font: "Bricolage Grotesque",
    see: "Ein Handballtor von vorn, der Ball fliegt oben in den Winkel.",
    idea: "Das Tor ist das Bild, das jede Handballerin im Kopf hat. Der Ball im Winkel ist der schönste Moment im Spiel, und er sagt, was die App will: dorthin zeigen, wo es passiert.",
    colors: [["Torrot", C.red], ["Nachtblau", C.navy], ["Ballgelb", C.ball]],
    lockup, mark: (m) => goal(m), iconBg: C.navy, iconMark: () => goal(null, true), scene: "phone"
  };
})());

/* ============ 3 TAKTIK: a play as the coach draws it on the board ============ */
IDEAS.push((() => {
  const C = { blue: "#1d47d1", red: "#e1251b", ink: "#111316", board: "#f7f8f7" };
  /* marker strokes: round caps, a slightly irregular hand */
  function draw(m, onDark) {
    const blue = m || C.blue, red = m || C.red, ink = m || (onDark ? "rgb(255 255 255 / .55)" : "rgb(17 19 22 / .38)"), w = 30;
    let s = "";
    /* end line, goal and goal area as on the printed board */
    s += `<path d="M40 52 H472" fill="none" stroke="${ink}" stroke-width="10" stroke-linecap="round"/>`;
    s += `<rect x="216" y="36" width="80" height="22" rx="3" fill="${m || (onDark ? "#fff" : C.ink)}"/>`;
    s += `<path d="M96 52 C 110 190, 402 190, 416 52" fill="none" stroke="${ink}" stroke-width="10" stroke-linecap="round" stroke-dasharray="1 22"/>`;
    s += `<path d="M 86 400 c 0 -34 24 -54 52 -53 c 30 1 52 24 50 54 c -2 31 -26 50 -54 48 c -28 -2 -49 -21 -48 -49 Z" fill="none" stroke="${blue}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;
    s += `<path d="M318 268 L 398 350 M 400 266 L 320 352" fill="none" stroke="${red}" stroke-width="${w}" stroke-linecap="round"/>`;
    s += `<path d="M 168 318 C 190 230, 220 190, 250 150" fill="none" stroke="${blue}" stroke-width="${w}" stroke-linecap="round"/>`;
    s += `<path d="M 206 154 L 256 126 L 272 184" fill="none" stroke="${blue}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;
    return s;
  }
  function lockup(m) {
    const ink = m || C.ink, blue = m || C.blue;
    const a = text("Archivo-ExtraBold", "Handball", 560, 250, 150, { track: -0.03 }), b = text("Archivo-ExtraBold", "Intelligence", 560, 392, 150, { track: -0.03 });
    return { body: draw(m) + P(a.d, ink) + P(b.d, blue), vb: `40 40 ${560 + Math.max(a.w, b.w) - 10} 400` };
  }
  return {
    key: "taktik", name: "Taktik", kind: "Zeichen und Wortmarke", font: "Archivo ExtraBold",
    see: "Ein Spielzug, wie die Trainerin ihn auf die Tafel zeichnet: oben das Tor, unsere Spielerin als Kreis, der Gegner als Kreuz, der Pfeil zum Tor.",
    idea: "Auswerten heisst im Handball seit jeher: Kreis, Kreuz und Pfeil auf der Magnettafel. Das Zeichen ist mit Filzstift gezeichnet, nicht konstruiert, und sagt damit, wofür die App da ist.",
    colors: [["Markerblau", C.blue], ["Markerrot", C.red], ["Tinte", C.ink]],
    lockup, mark: (m) => draw(m), iconBg: C.board, iconMark: () => draw(null), scene: "bottle"
  };
})());

/* ============ 4 SUCHER: a ball in the camera's frame ============ */
IDEAS.push((() => {
  const C = { ink: "#0f1114", rec: "#ff3b2f", ball: "#1f5bff", white: "#ffffff" };
  function draw(m, onDark) {
    const ink = m || (onDark ? C.white : C.ink), rec = m || C.rec, ball = m || C.ball, seam = m ? (onDark ? "#000" : "#fff") : C.ink, t = 34, L = 104;
    let s = `<path d="M${52 + L} 52H52V${52 + L}M${460 - L} 52H460V${52 + L}M460 ${460 - L}V460H${460 - L}M${52 + L} 460H52V${460 - L}" fill="none" stroke="${ink}" stroke-width="${t}" stroke-linecap="butt" stroke-linejoin="miter"/>`;
    s += `<circle cx="132" cy="132" r="22" fill="${rec}"/>`;
    const cx = 264, cy = 272, r = 118;
    s += drawBall(cx, cy, r, m ? "none" : "#ffffff", m || C.ball, m || C.ink, 14);
    return s;
  }
  function lockup(m) {
    const ink = m || C.ink, a = text("Sora-ExtraBold", "handball", 560, 250, 148, { track: -0.04 }), b = text("Sora-ExtraBold", "intelligence", 560, 392, 148, { track: -0.04 });
    return { body: draw(m) + P(a.d, ink) + P(b.d, m || "#5b6068"), vb: `30 30 ${560 + Math.max(a.w, b.w) - 10} 452` };
  }
  return {
    key: "sucher", name: "Sucher", kind: "Zeichen und Wortmarke", font: "Sora ExtraBold",
    see: "Ein Ball im Sucher einer Kamera, die gerade aufnimmt.",
    idea: "Alles beginnt mit einem Video. Der rote Aufnahmepunkt und die vier Ecken des Suchers kennt jedes Kind vom Handy; drinnen ist der Ball. Der Name steht klein und kleingeschrieben daneben.",
    colors: [["Ballblau", C.ball], ["Aufnahmerot", C.rec], ["Tinte", C.ink]],
    lockup, mark: (m) => draw(m), iconBg: C.ink, iconMark: () => draw(null, true), scene: "jacket"
  };
})());

/* ============ 5 SKRIPT: the jersey script with a tail ============ */
IDEAS.push((() => {
  const C = { red: "#d4152b", navy: "#0f2347", white: "#ffffff" };
  function lockup(m, onDark) {
    const red = m || C.red, navy = m ? "none" : C.navy, cut = m ? (onDark ? "#000" : "#fff") : C.white;
    const S = 250, base = 250, w = text("Yellowtail", "Handball", 40, base, S, { track: 0.0 });
    const x0 = w.x0 + 30, x1 = w.x0 + w.w + 6;
    /* the tail: leaves the last l, sweeps back under the word and ends in a point under the H */
    const ty = base + 34, th = 62;
    const tail = `M${x1 - 30} ${base - 22} C ${x1 + 40} ${base + 2}, ${x1 + 20} ${ty + th * 0.8}, ${x1 - 90} ${ty + th} L ${x0 + 120} ${ty + th - 6} C ${x0 + 60} ${ty + th - 8}, ${x0 + 10} ${ty + th - 20}, ${x0 - 20} ${ty + th - 30} C ${x0 + 40} ${ty + 6}, ${x0 + 100} ${ty}, ${x0 + 160} ${ty} L ${x1 - 110} ${ty} C ${x1 - 50} ${ty}, ${x1 - 30} ${base}, ${x1 - 52} ${base - 22} Z`;
    const sub = text("Archivo-ExpandedBold", "INTELLIGENCE", (x0 + 160 + x1 - 110) / 2 + 10, ty + 45, 34, { track: 0.18, anchor: "middle" });
    let s = "";
    if (!m) s += `<path d="${w.d}" fill="${navy}" stroke="${navy}" stroke-width="22" stroke-linejoin="round"/><path d="${tail}" fill="${navy}" stroke="${navy}" stroke-width="22" stroke-linejoin="round"/>`;
    if (m) { const mid = "sk" + (++BID); s += `<defs><mask id="${mid}" maskUnits="userSpaceOnUse" x="-2000" y="-2000" width="6000" height="6000"><path d="${tail}" fill="#fff"/><path d="${sub.d}" fill="#000"/></mask></defs>` + P(w.d, red) + `<path d="${tail}" fill="${red}" mask="url(#${mid})"/>`; }
    else s += P(w.d, red) + P(tail, red) + P(sub.d, cut);
    return { body: s, vb: `${x0 - 50} 40 ${x1 - x0 + 110} ${ty + th + 30 - 40}` };
  }
  function mark(m, onDark) {
    const g = text("Yellowtail", "H", 0, 0, 380), red = m || C.red, bb = font("Yellowtail").getPath("H", 0, 0, 380).getBoundingBox(), tx = 256 - (bb.x1 + bb.x2) / 2, ty = 256 - (bb.y1 + bb.y2) / 2;
    let s = "";
    if (!m && !onDark) s += `<path d="${g.d}" fill="${C.navy}" stroke="${C.navy}" stroke-width="26" stroke-linejoin="round" transform="translate(${tx} ${ty})"/>`;
    s += `<path d="${g.d}" fill="${onDark && !m ? C.white : red}" transform="translate(${tx} ${ty})"/>`;

    return s;
  }
  return {
    key: "skript", name: "Skript", kind: "Wortmarke", font: "Yellowtail, Archivo Expanded",
    see: "Der Schriftzug «Handball» wie auf der Brust eines Trikots, mit dem Schwung darunter.",
    idea: "So stehen Vereinsnamen seit hundert Jahren auf Trikots: geschrieben, rot mit dunkler Kante, und unter dem Wort ein Schwung, in dem der Rest des Namens steht. Stolz, warm, sofort Sport.",
    colors: [["Trikotrot", C.red], ["Marine", C.navy], ["Weiss", C.white]],
    lockup, mark: (m) => mark(m), iconBg: C.red, iconMark: () => mark(null, true), scene: "jacket"
  };
})());

/* ============ 6 TIME-OUT: the green team time-out card ============ */
IDEAS.push((() => {
  const C = { green: "#12a150", deep: "#0b5e30", ink: "#111316", white: "#ffffff" };
  /* the card as the coach lays it on the timekeeper's table: upright, slightly turned */
  function card(m, onDark) {
    const g = m || C.green, t = m ? (onDark ? "#000" : "#fff") : C.white, sh = m ? "none" : C.deep;
    let s = `<g transform="rotate(-8 256 256)">`;
    if (!m) s += `<rect x="112" y="64" width="300" height="400" rx="26" fill="${sh}" transform="translate(10 12)"/>`;
    const cardD = "M138 64 H386 A26 26 0 0 1 412 90 V438 A26 26 0 0 1 386 464 H138 A26 26 0 0 1 112 438 V90 A26 26 0 0 1 138 64 Z", tD = "M158 128 H366 V196 H298 V412 H226 V196 H158 Z";
    s += m ? `<path d="${cardD} ${tD}" fill="${g}" fill-rule="evenodd"/>` : `<path d="${cardD}" fill="${g}"/><path d="${tD}" fill="${t}"/>`;
    s += `</g>`;
    return s;
  }
  function lockup(m) {
    const ink = m || C.ink, a = text("Rubik-ExtraBold", "Handball", 560, 250, 150, { track: -0.02 }), b = text("Rubik-ExtraBold", "Intelligence", 560, 392, 150, { track: -0.02 });
    return { body: card(m) + P(a.d, ink) + P(b.d, m || C.deep), vb: `90 40 ${560 + Math.max(a.w, b.w) - 70} 450` };
  }
  return {
    key: "timeout", name: "Time-out", kind: "Zeichen und Wortmarke", font: "Rubik ExtraBold",
    see: "Die grüne Time-out-Karte mit dem T, die die Trainerin auf den Tisch legt.",
    idea: "Die grüne Karte mit dem T gibt es nur im Handball: Damit holt die Trainerin ihr Team zu sich und sagt in einer Minute, was anders werden muss. Genau das will die App sein. Jede Handballerin kennt die Karte, niemand ausserhalb hat sie.",
    colors: [["Time-out-Grün", C.green], ["Tiefgrün", C.deep], ["Tinte", C.ink]],
    lockup, mark: (m) => card(m), iconBg: C.ink, iconMark: () => card(null, true), scene: "bottle"
  };
})());

/* ============ output ============ */
const out = path.join(here, "logos");
const files = {};
IDEAS.forEach((I) => {
  const L = I.lockup(null), M = I.lockup("#000"), MW = I.lockup("#fff", true);
  files[I.key + "-wortmarke.svg"] = svg(L.vb, L.body);
  files[I.key + "-einfarbig-schwarz.svg"] = svg(M.vb, M.body);
  files[I.key + "-einfarbig-weiss.svg"] = svg(MW.vb, MW.body);
  files[I.key + "-zeichen.svg"] = svg("0 0 512 512", I.mark(null));
  files[I.key + "-app-icon.svg"] = svg("0 0 1024 1024", `<rect width="1024" height="1024" rx="228" fill="${I.iconBg}"/><g transform="translate(176 176) scale(1.3125)">${I.iconMark()}</g>`);
});
Object.keys(files).forEach((n) => fs.writeFileSync(path.join(out, n), files[n] + "\n"));

/* ---------- the page ---------- */
const inl = (n, cls = "") => files[n].replace("<svg ", `<svg class="${cls}" role="img" aria-label="${n.replace(".svg", "").replace(/-/g, " ")}" `);
function scene(I) {
  const icon = files[I.key + "-app-icon.svg"].replace("<svg ", '<svg class="ic" ');
  const mono = files[I.key + "-einfarbig-weiss.svg"].replace("<svg ", '<svg class="m" ');
  const color = files[I.key + "-wortmarke.svg"].replace("<svg ", '<svg class="m" ');
  if (I.scene === "banner") return `<figure class="sc banner"><div class="wall"><div class="ban">${mono}</div></div><figcaption>Hallenbanner an der Tribüne, 6 auf 1 Meter</figcaption></figure>`;
  if (I.scene === "phone") return `<figure class="sc phone"><div class="ph"><div class="grid">${["#3a7bd5", "#2fb36e", "#f2a33a", "#8e5bd8", "#e0533c", "#1c1c1e", "#5ac8fa", "#ffcc00", "#34c759", "#ff2d55", "#af52de"].map((c, i) => (i === 5 ? `<div class="app me">${icon}<span>Handball I…</span></div>` : "") + `<div class="app"><i style="background:${c}"></i><span>App</span></div>`).join("")}</div></div><figcaption>Auf dem Homescreen, neben anderen Apps</figcaption></figure>`;
  if (I.scene === "bottle") return `<figure class="sc bottle"><div class="bt"><div class="cap"></div><div class="body"><div class="stick">${files[I.key + "-zeichen.svg"].replace("<svg ", '<svg class="z" ')}</div></div></div><figcaption>Kleber auf der Trinkflasche, 6 cm</figcaption></figure>`;
  return `<figure class="sc jacket"><div class="jk"><svg viewBox="0 0 400 300" class="shape" aria-hidden="true"><path d="M110 20 L160 8 Q200 30 240 8 L290 20 L370 70 L340 300 L60 300 L30 70 Z" fill="#14213d"/><path d="M200 26 V300" stroke="#0a1328" stroke-width="4"/><path d="M160 8 Q200 30 240 8 L232 30 Q200 46 168 30 Z" fill="#0a1328"/></svg><div class="chest">${mono}</div></div><figcaption>Gestickt auf der Trainerjacke</figcaption></figure>`;
}
const fontsCss = ""; /* the page uses the outlined SVGs only, no web fonts needed for the logos */
const tafeln = IDEAS.map((I, n) => `
<section class="tafel" id="${I.key}">
  <header class="th"><span class="no">${n + 1}</span><div><h2>${I.name}</h2><p>${I.kind} · Schrift: ${I.font}</p></div></header>
  <p class="see"><b>Das sieht man:</b> ${I.see}</p>
  <div class="grid2">
    <div class="big">${inl(I.key + "-zeichen.svg", "zeichen")}</div>
    <div class="right">
      <div class="cell lock">${inl(I.key + "-wortmarke.svg", "w")}</div>
      <div class="cell row">
        <div class="icons">${files[I.key + "-app-icon.svg"].replace("<svg ", '<svg class="i180" role="img" aria-label="App-Icon" ')}<div class="smalls">${files[I.key + "-app-icon.svg"].replace("<svg ", '<svg class="i32" role="img" aria-label="App-Icon, 32 px" ')}<small>32 px</small>${files[I.key + "-app-icon.svg"].replace("<svg ", '<svg class="i16" role="img" aria-label="App-Icon, 16 px" ')}<small>16 px</small></div></div>
        <div class="monos"><div class="mono b">${inl(I.key + "-einfarbig-schwarz.svg", "w")}</div><div class="mono d">${inl(I.key + "-einfarbig-weiss.svg", "w")}</div></div>
      </div>
      <div class="cell scenecell">${scene(I)}</div>
    </div>
  </div>
  <div class="foot"><p>${I.idea}</p><ul class="sw">${I.colors.map((c) => `<li><i style="background:${c[1]}"></i><b>${c[0]}</b> ${c[1]}</li>`).join("")}</ul></div>
</section>`).join("\n");

const RANK = fs.readFileSync(path.join(here, "rangfolge.html"), "utf8");
const page = `<!doctype html>
<html lang="de-CH">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Handball Intelligence Logos</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..900&display=swap">
<style>
:root { color-scheme: light; --bg: #ecedef; --paper: #ffffff; --ink: #121417; --ink-2: #555b63; --rule: #d6d9dd; --f: "Archivo", system-ui, sans-serif; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 400 16px/1.5 var(--f); }
.wrap { max-width: 1320px; margin: 0 auto; padding-block: 48px 96px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; gap: 56px; }
.intro { display: grid; gap: 16px; max-width: 900px; }
.intro .lab { font: 700 13px/1 var(--f); font-stretch: 125%; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-2); }
.intro h1 { margin: 0; font: 900 clamp(44px, 8vw, 104px)/.9 var(--f); font-stretch: 75%; letter-spacing: -.02em; text-wrap: balance; }
.intro p { margin: 0; font-size: 19px; color: var(--ink-2); max-width: 64ch; }
.intro nav { display: flex; flex-wrap: wrap; gap: 8px 20px; font-weight: 700; }
.intro nav a { color: var(--ink); text-underline-offset: 4px; }
.tafel { background: var(--paper); padding: 32px; display: grid; gap: 24px; scroll-margin-top: 16px; }
.th { display: flex; gap: 20px; align-items: center; }
.th .no { font: 900 64px/1 var(--f); font-stretch: 62%; }
.th h2 { margin: 0; font: 900 40px/1 var(--f); font-stretch: 80%; }
.th p { margin: 6px 0 0; color: var(--ink-2); font-size: 14px; }
.see { margin: 0; font-size: 19px; max-width: 70ch; }
.grid2 { display: grid; grid-template-columns: minmax(0, 5fr) minmax(0, 7fr); gap: 24px; }
.big { background: #f6f7f8; display: grid; place-items: center; padding: 32px; min-height: 480px; }
.big .zeichen { width: 100%; max-width: 440px; height: auto; }
.right { display: grid; gap: 24px; align-content: start; min-width: 0; }
.cell { background: #f6f7f8; padding: 24px; min-width: 0; }
.cell.lock { display: grid; place-items: center; min-height: 170px; background: #fff; box-shadow: inset 0 0 0 1px var(--rule); }
.cell.lock .w { width: 100%; max-width: 560px; height: auto; max-height: 160px; }
.cell.row { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 24px; align-items: center; }
.icons { display: flex; gap: 20px; align-items: flex-end; }
.i180 { width: 140px; height: 140px; filter: drop-shadow(0 6px 12px rgb(0 0 0 / .18)); }
.smalls { display: grid; grid-template-columns: auto auto; gap: 6px 8px; align-items: center; font-size: 12px; color: var(--ink-2); }
.i32 { width: 32px; height: 32px; } .i16 { width: 16px; height: 16px; }
.monos { display: grid; gap: 12px; min-width: 0; }
.mono { display: grid; place-items: center; padding: 14px 16px; min-height: 72px; }
.mono.b { background: #fff; box-shadow: inset 0 0 0 1px var(--rule); }
.mono.d { background: #121417; }
.mono .w { width: 100%; max-width: 300px; height: auto; max-height: 64px; }
.scenecell { padding: 0; overflow: hidden; }
.sc { margin: 0; }
.sc figcaption { font-size: 13px; color: var(--ink-2); padding: 10px 16px 12px; background: #fff; box-shadow: inset 0 1px 0 var(--rule); }
.banner .wall { height: 230px; display: grid; place-items: center; background: linear-gradient(#c3a27a 0 62%, #b08c62 62% 64%, #d9dcdf 64%); }
.banner .ban { width: 82%; height: 92px; display: grid; place-items: center; background: #121417; box-shadow: 0 8px 16px rgb(0 0 0 / .3); position: relative; }
.banner .ban::before, .banner .ban::after { content: ""; position: absolute; top: 8px; width: 8px; height: 8px; border-radius: 50%; background: #9aa0a6; }
.banner .ban::before { left: 10px; } .banner .ban::after { right: 10px; }
.banner .m { height: 62px; width: auto; max-width: 90%; }
.phone { background: #2b3a55; display: grid; place-items: center; padding: 24px 0; }
.ph { width: 270px; padding: 28px 22px; border-radius: 34px; background: #1a2a48; box-shadow: 0 0 0 7px #0d0f12; }
.ph .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px 12px; }
.ph .app { display: grid; justify-items: center; gap: 5px; font: 500 10px/1.1 -apple-system, system-ui, sans-serif; color: #fff; }
.ph .app i { width: 48px; height: 48px; border-radius: 11px; opacity: .55; }
.ph .app .ic { width: 48px; height: 48px; }
.ph .app.me span { font-weight: 600; }
.bottle { background: #d7dbe0; display: grid; place-items: center; padding: 20px 0 0; }
.bt { display: grid; justify-items: center; }
.bt .cap { width: 56px; height: 26px; background: #121417; border-radius: 6px 6px 2px 2px; }
.bt .body { width: 130px; height: 200px; margin-top: 4px; border-radius: 28px 28px 10px 10px; background: #1b6ad1; display: grid; place-items: center; box-shadow: inset -14px 0 0 rgb(0 0 0 / .12), inset 10px 0 0 rgb(255 255 255 / .12); }
.bt .stick { width: 92px; height: 92px; border-radius: 50%; background: #fff; display: grid; place-items: center; box-shadow: 0 1px 2px rgb(0 0 0 / .3); }
.bt .z { width: 72px; height: 72px; }
.jacket { background: #b9bec5; display: grid; place-items: center; padding-top: 16px; }
.jk { position: relative; width: 360px; }
.jk .shape { width: 100%; display: block; }
.jk .chest { position: absolute; left: 60%; top: 24%; width: 26%; }
.jk .chest .m { width: 100%; height: auto; }
.foot { display: grid; grid-template-columns: minmax(0, 7fr) minmax(0, 5fr); gap: 24px; align-items: start; }
.foot p { margin: 0; max-width: 66ch; }
.sw { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; font-size: 14px; }
.sw i { display: inline-block; width: 18px; height: 18px; vertical-align: -4px; margin-right: 8px; box-shadow: inset 0 0 0 1px rgb(0 0 0 / .2); }
.rank { background: var(--paper); padding: 32px; display: grid; gap: 16px; }
.rank h2 { margin: 0; font: 900 40px/1 var(--f); font-stretch: 80%; }
.rank ol { margin: 0; padding-left: 1.4em; display: grid; gap: 12px; max-width: 80ch; }
.rank li b { font-weight: 800; }
@media (max-width: 860px) { .grid2, .foot { grid-template-columns: 1fr; } .cell.row { grid-template-columns: 1fr; } .big { min-height: 0; } .tafel { padding: 20px; } }
</style>
</head>
<body>
<div class="wrap">
<header class="intro">
  <p class="lab">Handball Intelligence · Logo, zweite Runde · Feld: Dinge des Sports und Schrift</p>
  <h1>Sechs Zeichen für Handball Intelligence</h1>
  <p>Jede Idee auf einer eigenen Tafel: das Zeichen gross, mit Wortmarke, als App-Icon in drei Grössen, einfarbig schwarz und weiss, und in einer echten Situation. Unter jedem Zeichen steht, was man darauf sieht. Alle Schriften sind in Pfade umgewandelt (SIL OFL), die SVG-Dateien liegen in <code>logos/</code>.</p>
  <nav aria-label="Ideen">${IDEAS.map((I, n) => `<a href="#${I.key}">${n + 1} ${I.name}</a>`).join("")}<a href="#rangfolge">Rangfolge</a></nav>
</header>
${tafeln}
${RANK}
</div>
</body>
</html>
`;
fs.writeFileSync(path.join(here, "index.html"), page);
console.log("ok", Object.keys(files).length, "files");
