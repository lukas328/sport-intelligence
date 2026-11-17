/*
 * Helpers for the templates (templates/*.html). compose.mjs sets window.CAPTURES (from
 * captures/captures.json: size, density and boxes of each app picture) before the page loads.
 * A template builds its picture with these helpers and ends with `done()`; compose.mjs then
 * photographs #stage and writes the callouts (in per cent of the picture) to the manifest.
 *
 * Coordinates: boxes from the captures are in CSS pixels of the app (rect = [x, y, w, h]);
 * everything on the stage is in CSS pixels of the stage (the 1x picture).
 */
(function () {
  const shot = { callouts: [], warnings: [], transparent: false };
  /** every phone shows the app at the same size, so the pictures belong together */
  const PHONE_SCREEN = 380;
  window.SHOT = shot;

  /** the capture `name`: { src, w, h (CSS px of the app), rects } */
  function cap(name) {
    const c = (window.CAPTURES || {})[name];
    if (!c) throw new Error(`capture «${name}» is missing: run capture.mjs`);
    const s = c.scale || 1;
    const rects = {};
    for (const [k, r] of Object.entries(c.rects || {})) rects[k] = r.map((v) => v / s);
    return { src: c.src, w: c.width / s, h: c.height / s, rects };
  }

  /** a box from the capture, or the fallback (and a warning) when the app did not show it */
  function rect(name, key, fallback) {
    const r = cap(name).rects[key];
    if (r) return r;
    shot.warnings.push(`${name}: box «${key}» not found, using the fallback`);
    return fallback;
  }

  /**
   * the stage: size in CSS px of the 1x picture; `clear` leaves the background transparent,
   * `budget2x` sets a smaller weight for the 2x file than compose.mjs's default
   */
  function stage(width, height, opts = {}) {
    const el = document.getElementById("stage");
    el.style.width = `${width}px`;
    el.style.height = `${height}px`;
    if (opts.clear) {
      el.classList.add("clear");
      shot.transparent = true;
    }
    shot.width = width;
    shot.height = height;
    // a lower weight for a picture the page loads at once (bytes of the 2x file)
    if (opts.budget2x) shot.budget2x = opts.budget2x;
    return el;
  }

  /**
   * Fills a .screen element (its width set by CSS) with part of a capture. `crop` = [x, y, w, h]
   * in app CSS px (default the whole capture); the screen's height follows the crop unless
   * `height` is given. Returns a function that maps an app box to a box in the screen.
   */
  function screen(el, name, crop, height) {
    const c = cap(name);
    const [x, y, w, h] = crop || [0, 0, c.w, c.h];
    const k = el.clientWidth / w;
    el.style.height = `${height ?? h * k}px`;
    const img = document.createElement("img");
    img.className = "cap";
    img.src = c.src;
    img.alt = "";
    img.style.width = `${c.w * k}px`;
    img.style.transform = `translate(${-x * k}px, ${-y * k}px)`;
    el.prepend(img);
    const map = ([rx, ry, rw, rh]) => [(rx - x) * k, (ry - y) * k, rw * k, rh * k];
    map.k = k;
    map.el = el;
    return map;
  }

  /**
   * A phone on the stage showing a whole capture. `left` in stage px; the phone is moved up or
   * down so that the app's line `y` (CSS px of the capture) sits at the stage's line `at`, or,
   * with `bottom`, so that the phone stands that far above the stage's bottom edge.
   */
  function phone(name, { left, width = PHONE_SCREEN, y = 0, at = 0, bottom }) {
    const body = document.createElement("div");
    body.className = "phone";
    body.style.left = `${left}px`;
    const scr = document.createElement("div");
    scr.className = "screen";
    scr.style.width = `${width}px`;
    body.append(scr);
    document.getElementById("stage").append(body);
    const map = screen(scr, name);
    const pad = (body.offsetWidth - width) / 2;
    const top =
      bottom !== undefined ? shot.height - bottom - body.offsetHeight : at - pad - y * map.k;
    body.style.top = `${top}px`;
    return map;
  }

  /**
   * A browser window with the app's address, showing `crop` of a capture. `width` is the outer
   * width in stage px; the window may run over the stage's edge (the picture cuts it there).
   */
  function browser(name, crop, { left, top, width }) {
    const win = document.createElement("div");
    win.className = "browser";
    Object.assign(win.style, { left: `${left}px`, top: `${top}px`, width: `${width}px` });
    win.innerHTML =
      '<div class="bar"><i></i><i></i><i></i><span>app.handball-intelligence.com</span></div>';
    const scr = document.createElement("div");
    scr.className = "screen";
    win.append(scr);
    document.getElementById("stage").append(win);
    return screen(scr, name, crop);
  }

  /** where a box inside `el` sits on the stage */
  function onStage(el, [x, y, w, h]) {
    const s = document.getElementById("stage").getBoundingClientRect();
    const r = el.getBoundingClientRect();
    return [r.left - s.left + el.clientLeft + x, r.top - s.top + el.clientTop + y, w, h];
  }

  /** a ring around an app box, inside the screen; `pad` in stage px */
  function ring(map, r, pad = 6, round = false) {
    const [x, y, w, h] = map(r);
    const d = document.createElement("div");
    d.className = round ? "ring round" : "ring";
    Object.assign(d.style, {
      left: `${x - pad}px`,
      top: `${y - pad}px`,
      width: `${w + 2 * pad}px`,
      height: `${h + 2 * pad}px`,
    });
    map.el.append(d);
    return onStage(map.el, [x - pad, y - pad, w + 2 * pad, h + 2 * pad]);
  }

  /** the spotlight: the screen a little darker except around these app boxes */
  function spot(map, rects, pad = 8, alpha = 0.34) {
    const el = map.el;
    const W = el.clientWidth;
    const H = el.clientHeight;
    const holes = rects
      .map(map)
      .map(
        ([x, y, w, h]) => `M${x - pad} ${y - pad}h${w + 2 * pad}v${h + 2 * pad}h${-(w + 2 * pad)}z`,
      )
      .join("");
    el.insertAdjacentHTML(
      "beforeend",
      `<svg class="veil" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}"><path fill="rgb(22 23 26 / ${alpha})" fill-rule="evenodd" d="M0 0H${W}V${H}H0z${holes}"/></svg>`,
    );
  }

  /** a point of an app box on the stage: fx, fy from 0 (left, top) to 1 (right, bottom) */
  function at(map, r, fx = 0.5, fy = 0.5) {
    const [x, y, w, h] = onStage(map.el, map(r));
    return [x + w * fx, y + h * fy];
  }

  /**
   * A callout for the website: an arrow from `from` (where the label sits) to `to` (the spot),
   * both [x, y] on the stage. `place` says where the label goes from `from`: "r" right of it,
   * "l" left, "t" above and "b" below (centred), "tl"/"bl" above/below running to the right,
   * "tr"/"br" above/below running to the left. `bend` curves the arrow (+ one way, − the other).
   */
  function callout(id, from, to, place = "r", bend = 0.25) {
    shot.callouts.push({ id, from, to, place, bend });
  }

  /** waits for the pictures, then tells compose.mjs the stage is ready */
  async function done() {
    await document.fonts.ready;
    await Promise.all(Array.from(document.images).map((i) => i.decode().catch(() => {})));
    window.READY = shot;
  }

  window.S = { cap, rect, stage, screen, phone, browser, onStage, ring, spot, at, callout, done };
})();
