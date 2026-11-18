/*
 * The look of the four steps of «So funktioniert es» (U33, after Lukas' design of 18.11.): a dark
 * court ground with the club's green, big yellow cards, the step's word as a ghost in the back
 * and one white line at the foot (styles in stage.css, «#stage.steps»). This file draws the
 * courts as SVG in any projection and adds the shared pieces; the templates place the cards.
 *
 * Court metres as in hall.js: x along the court (0 to 40, goals at x = 0 and x = 40), y across it
 * (0 to 20). A projection `M([x, y])` turns metres into stage px: `top` for a flat view from
 * above (turned and scaled), `persp` for a camera (hall.js view, the floor at z = 0).
 */
(function () {
  const K = {
    ink: "#16171a",
    attn: "#ffd23c",
    paper: "#f7f6f2",
    night: "#2d3237",
    night2: "#383e44",
    night3: "#454c53",
    pitch: "#10684a",
    pitch2: "#0d5a40",
    pitch3: "#1b7d5a",
    chalk: "#f3f1ec",
  };
  const f1 = (v) => (+v).toFixed(1);
  const curve = (f, a, b, n = 36) => Array.from({ length: n + 1 }, (_, i) => f(a + ((b - a) * i) / n));

  /** a flat view from above: the court's origin at [x0, y0] px, `s` px per metre, turned by `rot` degrees */
  function top({ x0, y0, s, rot = 0 }) {
    const c = Math.cos((rot * Math.PI) / 180);
    const d = Math.sin((rot * Math.PI) / 180);
    return ([x, y]) => [x0 + s * (x * c - y * d), y0 + s * (x * d + y * c)];
  }
  /** a camera's view (hall.js `HALL.view`), the floor at z = 0 */
  function persp(view) {
    return ([x, y]) => view.P([x, y, 0]);
  }

  /** an SVG path through points in metres */
  function path(M, pts, close = false) {
    return `M${pts.map((p) => M(p).map(f1).join(" ")).join("L")}${close ? "Z" : ""}`;
  }

  // the goal area of one goal: 6 m quarter circles around the posts and the line between
  function zonePts(side) {
    const gx = side < 0 ? 0 : 40;
    const s = side < 0 ? 1 : -1;
    return [
      [gx, 2.5],
      ...curve((t) => [gx + s * 6 * Math.cos(t), 8.5 - 6 * Math.sin(t)], Math.PI / 2, 0),
      ...curve((t) => [gx + s * 6 * Math.cos(t), 11.5 + 6 * Math.sin(t)], 0, Math.PI / 2),
      [gx, 17.5],
    ];
  }
  // the free throw line (9 m): quarter circles around the posts, cut at the sidelines
  function ninePts(side) {
    const gx = side < 0 ? 0 : 40;
    const s = side < 0 ? 1 : -1;
    const a = Math.asin(Math.min(1, 8.5 / 9));
    return [
      ...curve((t) => [gx + s * 9 * Math.cos(t), 8.5 - 9 * Math.sin(t)], a, 0),
      ...curve((t) => [gx + s * 9 * Math.cos(t), 11.5 + 9 * Math.sin(t)], 0, a),
    ];
  }

  /**
   * The court: floor, goal areas in green, the lines in chalk, the goals. `sides` which halves
   * (-1 the left with its goal, 1 the right); `w` the line width in px; colours to override.
   */
  function court(M, opts = {}) {
    const { sides = [-1, 1], w = 2.4, floor = K.night2, zone = K.pitch, line = K.chalk, goal = K.chalk, nine = true, zoneLine = line } = opts;
    const x0 = sides.includes(-1) ? 0 : 20;
    const x1 = sides.includes(1) ? 40 : 20;
    const L = `stroke="${line}" stroke-width="${w}" stroke-linejoin="round" fill="none"`;
    const out = [];
    out.push(`<path d="${path(M, [[x0, 0], [x1, 0], [x1, 20], [x0, 20]], true)}" fill="${floor}"/>`);
    for (const s of sides) {
      out.push(`<path d="${path(M, zonePts(s), true)}" fill="${zone}" stroke="${zoneLine}" stroke-width="${w}" stroke-linejoin="round"/>`);
      if (nine) out.push(`<path d="${path(M, ninePts(s))}" ${L} stroke-dasharray="${f1(w * 3.2)} ${f1(w * 2.6)}"/>`);
      const gx = s < 0 ? 0 : 40;
      const k = s < 0 ? 1 : -1;
      out.push(`<path d="${path(M, [[gx + k * 7, 9.5], [gx + k * 7, 10.5]])}" ${L}/>`);
      // the goal: 3 m wide, 1 m deep behind the line
      out.push(`<path d="${path(M, [[gx, 8.5], [gx - k * 1, 8.5], [gx - k * 1, 11.5], [gx, 11.5]])}" fill="none" stroke="${goal}" stroke-width="${f1(w * 1.5)}" stroke-linejoin="miter"/>`);
    }
    out.push(`<path d="${path(M, [[x0, 0], [x1, 0], [x1, 20], [x0, 20]], true)}" ${L}/>`);
    if (sides.length === 2) out.push(`<path d="${path(M, [[20, 0], [20, 20]])}" ${L}/>`);
    return out.join("");
  }

  /** players as dots: `list` of [x, y] metres, filled `fill`, with an ink edge */
  function dots(M, list, { r = 9, fill = K.pitch3, edge = K.ink, ew = 2.5 } = {}) {
    return list
      .map((p) => {
        const [x, y] = M(p);
        return `<circle cx="${f1(x)}" cy="${f1(y)}" r="${r}" fill="${fill}" stroke="${edge}" stroke-width="${ew}"/>`;
      })
      .join("");
  }

  /** the SVG ground of the stage (behind the cards) */
  function ground(svg) {
    const el = document.getElementById("stage");
    const W = el.clientWidth;
    const H = el.clientHeight;
    el.insertAdjacentHTML("afterbegin", `<svg class="ground" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">${svg}</svg>`);
  }

  /** an element on the stage from HTML */
  function add(html) {
    const el = document.getElementById("stage");
    el.insertAdjacentHTML("beforeend", html);
    return el.lastElementChild;
  }

  /** the step's word in the back */
  function ghost(word, style) {
    const g = add(`<div class="ghost" aria-hidden="true"></div>`);
    g.textContent = word;
    Object.assign(g.style, style);
    return g;
  }

  /** the one white line at the foot, with an icon in front if given */
  function say(text, icon) {
    const s = add(`<p class="say">${icon ? ICON[icon] : ""}<span></span></p>`);
    // each sentence keeps together where it fits, so a second line starts with a sentence
    const span = s.querySelector("span");
    text.split(/(?<=[.!?])\s+/).forEach((part, i) => {
      if (i) span.append(" ");
      const b = document.createElement("span");
      b.style.display = "inline-block";
      b.textContent = part;
      span.append(b);
    });
    return s;
  }

  /** the icons (stroke in currentColor), 24 px grid */
  const ICON = {
    bell: `<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="${K.attn}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 16V11a6 6 0 0 1 12 0v5l1.6 2H4.4z"/><path d="M10 21h4"/></svg>`,
    camera: `<svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="${K.ink}" stroke-width="2.3" stroke-linejoin="round"><path d="M3.5 8.5h3.6l1.6-2.4h6.6l1.6 2.4h3.6v10H3.5z"/><circle cx="12" cy="13.2" r="3.2"/></svg>`,
    check: `<svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="${K.ink}" stroke-width="3.6" stroke-linecap="square"><path d="M4 12.5l5 5L20.5 6"/></svg>`,
  };

  /** the camera sign: a yellow disc with an ink edge and the camera in it, centred on [x, y] */
  function camera([x, y], r = 34) {
    return add(
      `<div style="position:absolute;left:${f1(x - r)}px;top:${f1(y - r)}px;width:${2 * r}px;height:${2 * r}px;border-radius:50%;background:${K.attn};border:3px solid ${K.ink};box-shadow:5px 5px 0 rgb(10 12 14 / .6);padding:${f1(r * 0.36)}px">${ICON.camera}</div>`,
    );
  }

  window.STEPS = { K, top, persp, path, court, dots, ground, add, ghost, say, camera, ICON, curve, zonePts, ninePts };
})();
