/* Runde 2: shared drawing code for both syntheses. Every colour comes from CSS variables, so
   each direction styles the same court, charts and frames its own way.
   Court: half court 20 m wide, goal at the top, 10 units per metre (viewBox 0 0 200 124). */
(function () {
  "use strict";

  function half() {
    return '<rect x="-2" y="-2" width="204" height="130" fill="var(--mf-floor)"/>'
      + '<path d="M40 0 A60 60 0 0 0 85 60 L115 60 A60 60 0 0 0 160 0 Z" fill="var(--mf-area)"/>'
      + '<g fill="none" stroke="var(--mf-line)" stroke-width="1.6"><path d="M40 0 A60 60 0 0 0 85 60 L115 60 A60 60 0 0 0 160 0"/>'
      + '<path d="M10 0 A90 90 0 0 0 85 90 L115 90 A90 90 0 0 0 190 0" stroke-dasharray="5 4"/>'
      + '<path d="M95 70h10M97.5 40h5"/><path d="M0 1h200" stroke-width="2.2"/></g>'
      + '<rect x="85" y="-1" width="30" height="4" fill="var(--mf-goal)"/>';
  }
  function us(p) { return '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="5.8" fill="var(--home)" stroke="var(--mf-us-ring)" stroke-width="1.6"/>'; }
  function them(p) { return '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="4.9" fill="var(--mf-them-fill)" stroke="var(--away-mark)" stroke-width="2.6"/>'; }
  function seg(a, dash) {
    var dx = a[2] - a[0], dy = a[3] - a[1], l = Math.hypot(dx, dy), ux = dx / l, uy = dy / l, x = a[2], y = a[3];
    var head = dash ? "" : '<path d="M' + (x - ux * 8 - uy * 4) + " " + (y - uy * 8 + ux * 4) + "L" + x + " " + y + "L" + (x - ux * 8 + uy * 4) + " " + (y - uy * 8 - ux * 4) + '" fill="none" stroke="var(--mf-path)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>';
    return '<path d="M' + a[0] + " " + a[1] + "L" + x + " " + y + '" stroke="var(--mf-path)" stroke-width="2.2" stroke-linecap="round" fill="none"' + (dash ? ' stroke-dasharray="0.5 5.5"' : "") + "/>" + head;
  }
  var D60 = [[34, 46], [60, 62], [88, 70], [112, 70], [140, 62], [166, 46]];
  var A = [[100, 104], [52, 92], [150, 92], [14, 26], [187, 22], [104, 64]];
  var SC = {
    ra: { us: D60, them: A, pass: [150, 92, 187, 22], shot: [187, 22, 112, 5] },
    tv: { us: [[156, 104], [118, 116], [58, 108]], them: [[100, 50], [66, 90], [38, 62]], pass: [66, 90, 100, 50], shot: [100, 50, 93, 5] },
    kr: { us: [[100, 104], [52, 92], [150, 92], [14, 26], [187, 22], [97, 64]], them: D60, pass: [52, 92, 97, 64], shot: [97, 64, 90, 5] },
    p1: { us: [[101, 9]], them: [[187, 22], [150, 90]], shot: [187, 22, 108, 6] },
    leer: { us: [], them: [] }
  };
  function courts(root) {
    root.querySelectorAll("svg.mf[data-mf]").forEach(function (s) {
      var c = SC[s.dataset.mf] || SC.leer, h = half();
      if (c.pass) h += seg(c.pass, true);
      if (c.shot) h += seg(c.shot, false);
      c.them.forEach(function (p) { h += them(p); });
      c.us.forEach(function (p) { h += us(p); });
      s.setAttribute("viewBox", "0 0 200 124"); if (!s.hasAttribute("role")) s.setAttribute("aria-hidden", "true"); s.innerHTML = h;
    });
    root.querySelectorAll("svg.shotmap").forEach(function (s) {
      var shots = [[14, 24, 1], [24, 36, 0], [186, 20, 1], [190, 30, 1], [178, 38, 0], [100, 66, 1], [92, 64, 1], [108, 68, 1], [116, 66, 0], [58, 86, 1], [50, 94, 0], [68, 98, 1], [100, 100, 1], [94, 106, 0], [108, 102, 1], [142, 90, 1], [150, 96, 0], [134, 100, 1], [100, 73, 1], [85, 71, 1], [154, 82, 0], [42, 72, 1], [100, 34, 1], [113, 37, 1], [89, 38, 0], [164, 62, 0]];
      var h = half();
      shots.forEach(function (d) {
        h += d[2] ? '<circle cx="' + d[0] + '" cy="' + d[1] + '" r="4.4" fill="var(--home)" stroke="var(--mf-us-ring)" stroke-width="1.2"/>'
          : '<path d="M' + (d[0] - 3.2) + " " + (d[1] - 3.2) + "l6.4 6.4M" + (d[0] + 3.2) + " " + (d[1] - 3.2) + 'l-6.4 6.4" stroke="var(--mf-path)" stroke-width="1.8" stroke-linecap="round"/>';
      });
      s.setAttribute("viewBox", "0 0 200 124"); s.innerHTML = h;
    });
    root.querySelectorAll("svg.zonen").forEach(function (s) {
      var z = [["LA", 16, 30, 2], ["RL", 50, 96, 3], ["RM", 100, 108, 2], ["RR", 150, 96, 1], ["RA", 174, 36, 9], ["KM", 100, 72, 1]];
      var h = half();
      z.forEach(function (d) {
        var r = 6.4 * Math.sqrt(d[3]), top = d[3] === 9;
        h += '<circle cx="' + d[1] + '" cy="' + d[2] + '" r="' + r.toFixed(1) + '" fill="' + (top ? "var(--z-top)" : "var(--z-fill)") + '" stroke="var(--z-stroke)" stroke-width="1.5"/>';
        h += '<text x="' + d[1] + '" y="' + (d[2] + 4.6) + '" text-anchor="middle" fill="' + (top ? "var(--z-top-text)" : "var(--z-text)") + '">' + d[3] + "</text>";
      });
      s.setAttribute("viewBox", "0 0 200 124"); s.innerHTML = h;
    });
    /* whole court seen from the camera: stand-in for a video frame */
    root.querySelectorAll("svg.videobild").forEach(function (s) {
      var L = "var(--v-line)";
      var h = '<rect width="400" height="200" fill="var(--v-floor)"/>'
        + '<path d="M0 40 A60 60 0 0 1 60 85 L60 115 A60 60 0 0 1 0 160 Z" fill="var(--v-area)"/><path d="M400 40 A60 60 0 0 0 340 85 L340 115 A60 60 0 0 0 400 160 Z" fill="var(--v-area)"/>'
        + '<g fill="none" stroke="' + L + '" stroke-width="1.6"><rect x="1" y="1" width="398" height="198"/><path d="M200 0v200"/>'
        + '<path d="M0 40 A60 60 0 0 1 60 85 L60 115 A60 60 0 0 1 0 160"/><path d="M400 40 A60 60 0 0 0 340 85 L340 115 A60 60 0 0 0 400 160"/>'
        + '<path d="M0 10 A90 90 0 0 1 90 85 L90 115 A90 90 0 0 1 0 190" stroke-dasharray="7 5"/><path d="M400 10 A90 90 0 0 0 310 85 L310 115 A90 90 0 0 0 400 190" stroke-dasharray="7 5"/></g>';
      [[330, 60], [318, 84], [312, 104], [320, 128], [336, 150], [352, 100]].forEach(function (p) { h += '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="6.5" fill="var(--home)" stroke="var(--mf-us-ring)" stroke-width="1.6"/>'; });
      [[262, 100], [276, 50], [280, 152], [372, 22], [378, 180], [326, 106], [392, 100]].forEach(function (p) { h += '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="5.6" fill="var(--mf-them-fill)" stroke="var(--away-mark)" stroke-width="2.8"/>'; });
      h += '<rect x="354" y="5" width="36" height="36" fill="none" stroke="var(--signal)" stroke-width="2.5"/>';
      s.setAttribute("viewBox", "0 0 400 200"); s.setAttribute("aria-hidden", "true"); s.innerHTML = h;
    });
  }

  /* goal difference over 60 minutes */
  function charts(root) {
    root.querySelectorAll("svg.flow").forEach(function (s) {
      var data = [[0, 0], [5, 1], [10, 1], [15, 2], [20, 3], [25, 3], [30, 4], [35, 4], [38, 4], [41, 3], [44, 3], [50, 5], [55, 7], [60, 8]];
      var X0 = 30, X1 = 508, Y0 = 128, Y1 = 14, MIN = -2, MAX = 10;
      function x(m) { return X0 + (X1 - X0) * m / 60; } function y(v) { return Y0 - (Y0 - Y1) * (v - MIN) / (MAX - MIN); }
      var c = '<rect x="' + x(38) + '" y="' + Y1 + '" width="' + (x(44) - x(38)) + '" height="' + (Y0 - Y1) + '" fill="var(--ch-phase)"/>';
      [0, 4, 8].forEach(function (v) { c += '<line x1="' + X0 + '" x2="' + X1 + '" y1="' + y(v) + '" y2="' + y(v) + '" stroke="' + (v ? "var(--ch-rule)" : "var(--ch-axis)") + '" stroke-width="' + (v ? 1 : 1.5) + '"/><text x="' + (X0 - 8) + '" y="' + (y(v) + 4) + '" text-anchor="end">' + (v ? "+" + v : "0") + "</text>"; });
      c += '<line x1="' + x(30) + '" x2="' + x(30) + '" y1="' + Y1 + '" y2="' + Y0 + '" stroke="var(--ch-axis)" stroke-width="1" stroke-dasharray="2 4"/>';
      [[0, "Anwurf"], [30, "Halbzeit 13:9"], [60, "Schluss 26:18"]].forEach(function (t) { c += '<text x="' + x(t[0]) + '" y="' + (Y0 + 18) + '" text-anchor="' + (t[0] === 0 ? "start" : t[0] === 60 ? "end" : "middle") + '">' + t[1] + "</text>"; });
      var pts = data.map(function (d) { return x(d[0]).toFixed(1) + "," + y(d[1]).toFixed(1); }).join(" ");
      c += '<polyline points="' + pts + '" fill="none" stroke="var(--ch-line)" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>';
      c += '<circle cx="' + x(60) + '" cy="' + y(8) + '" r="4.5" fill="var(--ch-line)"/><text x="' + (x(60) - 10) + '" y="' + (y(8) - 9) + '" text-anchor="end" class="big">+8</text>';
      c += '<text x="' + x(41) + '" y="' + (Y1 + 14) + '" text-anchor="middle" class="on">38. bis 44.</text>';
      s.setAttribute("viewBox", "0 0 520 152"); s.innerHTML = c;
    });
    root.querySelectorAll("svg.zeitleiste").forEach(function (s) {
      var W = 1000, u = [2, 5, 9, 11, 14, 17, 19, 22, 24, 26, 27, 29, 29.5, 32, 35, 36, 46, 48, 50, 51, 53, 54, 56, 57, 58, 59.5], t = [3, 7, 12, 16, 20, 23, 25, 28, 30, 39, 40, 41, 42, 43, 44, 49, 55, 58.5];
      function x(m) { return (m / 60) * W; }
      var c = '<rect x="' + x(38) + '" y="0" width="' + (x(44) - x(38)) + '" height="62" fill="var(--ch-phase)"/>';
      c += '<rect x="0" y="52" width="' + x(21) + '" height="10" fill="var(--tl-def1)"/><rect x="' + x(21) + '" y="52" width="' + (x(33) - x(21)) + '" height="10" fill="var(--tl-def2)"/><rect x="' + x(33) + '" y="52" width="' + (W - x(33)) + '" height="10" fill="var(--tl-def1)"/>';
      c += '<line x1="0" x2="' + W + '" y1="27" y2="27" stroke="var(--ch-axis)" stroke-width="1"/><line x1="' + x(30) + '" x2="' + x(30) + '" y1="0" y2="62" stroke="var(--ch-axis)" stroke-width="1" stroke-dasharray="2 3"/>';
      u.forEach(function (m) { c += '<rect x="' + (x(m) - 2.5) + '" y="6" width="5" height="20" fill="var(--home)"/>'; });
      t.forEach(function (m) { c += '<rect x="' + (x(m) - 2.5) + '" y="28" width="5" height="17" fill="var(--away-mark)"/>'; });
      c += '<line x1="' + x(41.2) + '" x2="' + x(41.2) + '" y1="-6" y2="66" stroke="var(--tl-head)" stroke-width="2.5"/><rect x="' + (x(41.2) - 6) + '" y="-10" width="12" height="8" fill="var(--tl-head)"/>';
      s.setAttribute("viewBox", "-6 -12 1012 80"); s.setAttribute("preserveAspectRatio", "none"); s.innerHTML = c;
    });
  }

  /* own pictograms: one figure, one stroke weight, square ends */
  var PICTO = {
    fluegel: '<circle cx="70" cy="18" r="9" class="f"/><path d="M66 32 L52 56 M62 38 L84 30 L92 14 M62 38 L42 36 M52 56 L64 72 L60 94 M52 56 L34 70 L16 66"/><circle cx="94" cy="6" r="6" class="f"/>',
    gegenstoss: '<circle cx="62" cy="18" r="9" class="f"/><circle cx="88" cy="48" r="6" class="f"/><path d="M58 33 L46 58 M57 37 L76 48 M57 37 L40 32 L34 44 M46 58 L62 70 L58 92 M46 58 L30 68 L12 62"/>',
    kreis: '<circle cx="50" cy="20" r="9" class="f"/><path d="M50 34 V62 M50 40 L32 28 M50 40 L70 24 L76 10 M50 62 L38 92 M50 62 L62 92"/><circle cx="80" cy="6" r="6" class="f"/>',
    abwehr: '<circle cx="50" cy="20" r="9" class="f"/><path d="M50 36 V62 M50 40 L33 30 L33 10 M50 40 L67 30 L67 10 M50 62 L38 92 M50 62 L62 92"/>'
  };
  function pictos(root) {
    root.querySelectorAll("[data-picto]").forEach(function (el) {
      el.innerHTML = '<svg class="picto" viewBox="0 0 100 100" aria-hidden="true">' + PICTO[el.dataset.picto] + "</svg>";
    });
  }

  var ICONS = {
    spiele: '<rect x="3" y="6" width="18" height="12"/><path d="M12 6v12"/><path d="M7 10.2v3.6M16 10.2h2v1.8h-2v1.8h2"/>',
    szenen: '<rect x="3" y="5" width="18" height="14"/><path d="M10 9.2v5.6l5-2.8z" fill="currentColor"/>',
    saison: '<path d="M4 19.5h16"/><path d="M6.5 16v-4M11 16V7.5M15.5 16v-6M20 16V5"/>',
    team: '<path d="M8.5 4 4 6.8l1.8 3.6L8 9.2V20h8V9.2l2.2 1.2L20 6.8 15.5 4c-.6 1.3-1.9 2-3.5 2s-2.9-.7-3.5-2z"/>',
    suche: '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    play: '<path d="M8 5.5v13l10.5-6.5z" fill="currentColor"/>'
  };
  function icons(root) {
    root.querySelectorAll("i[data-ic]").forEach(function (el) {
      el.outerHTML = '<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">' + ICONS[el.dataset.ic] + "</svg>";
    });
  }

  /* LED: unlit segments behind the digits */
  function leds(root) {
    root.querySelectorAll(".led:not([data-ghost])").forEach(function (el) {
      var t = el.textContent; el.dataset.ghost = t.replace(/[0-9]/g, "8"); el.innerHTML = "<i>" + t + "</i>";
    });
  }

  /* frames: one template, shown at desktop (1280) and phone (390) width, scaled down to fit */
  var W = { desk: 1280, phone: 390 };
  document.querySelectorAll("[data-tpl]").forEach(function (slot) {
    var tpl = document.getElementById(slot.dataset.tpl); if (!tpl) return;
    var kind = slot.dataset.w, node = tpl.content.cloneNode(true), app = node.firstElementChild;
    app.classList.add(kind === "desk" ? "is-desk" : "is-phone");
    var fr = document.createElement("div"); fr.className = "frame " + kind; fr.style.width = W[kind] + "px";
    fr.appendChild(node); slot.classList.add("fit"); slot.appendChild(fr);
  });
  function fit() {
    document.querySelectorAll(".fit").forEach(function (f) {
      var fr = f.firstElementChild, k = Math.min(1, f.clientWidth / fr.offsetWidth);
      fr.style.transform = "scale(" + k + ")"; f.style.height = Math.ceil(fr.offsetHeight * k) + "px";
    });
  }
  icons(document); pictos(document); leds(document); courts(document); charts(document);
  fit();
  window.addEventListener("resize", fit);
  window.addEventListener("load", fit);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
})();
