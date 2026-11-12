/* Renders the mockups in zielbild.html: app chrome per role, court thumbnails, LED ghosts,
   marker strokes, charts. Reference code, not production. The drawing helpers (court, marker)
   are small enough to port as they are. */
(function () {
  "use strict";

  /* ---------- icons: own set, one stroke weight ---------- */
  var ICONS = {
    heute: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none"/><path d="M12 3.5v3M12 17.5v3"/>',
    spiele: '<rect x="3" y="6" width="18" height="12" rx="1.5"/><path d="M12 6v12"/><path d="M7 10.2v3.6M16 10.2h2v1.8h-2v1.8h2"/>',
    szenen: '<rect x="3" y="5" width="18" height="14" rx="1.5"/><path d="M10 9.2v5.6l5-2.8z" fill="currentColor"/>',
    training: '<path d="M9.2 5h5.6l4.2 14H5z"/><path d="M7.4 11.5h9.2M6.2 15.5h11.6"/>',
    team: '<path d="M8.5 4 4 6.8l1.8 3.6L8 9.2V20h8V9.2l2.2 1.2L20 6.8 15.5 4c-.6 1.3-1.9 2-3.5 2s-2.9-.7-3.5-2z"/>',
    saison: '<path d="M4 19.5h16"/><path d="M6.5 16v-4M11 16V7.5M15.5 16v-6M20 16V5"/>',
    termine: '<rect x="4" y="5.5" width="16" height="14" rx="1.5"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>',
    kind: '<circle cx="12" cy="8" r="3.5"/><path d="M5 20c.6-4 3.4-6 7-6s6.4 2 7 6"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    suche: '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/>',
    glocke: '<path d="M6.5 16.5V11a5.5 5.5 0 0 1 11 0v5.5l1.5 1.5H5z"/><path d="M10.5 20.5h3"/>'
  };
  function icon(name) { return '<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">' + ICONS[name] + "</svg>"; }

  var NAV = {
    coach: [["spiele", "Spiele"], ["szenen", "Szenen"], ["saison", "Saison"], ["team", "Team"]]
  };
  var WHO = { coach: ["DT", "Demo Trainerin"] };

  function chrome(app) {
    var role = app.dataset.role, on = app.dataset.on, bare = app.dataset.bare;
    if (!role || bare) return;
    var items = NAV[role], who = WHO[role];
    var rail = '<nav class="rail"><div class="club"><span class="crest">HCZ</span><div><b>HC Zürichsee</b><small>' + (app.dataset.team || "Herren 1 · 3. Liga") + "</small></div></div>";
    rail += '<span class="btn up">' + icon("plus") + "Video hochladen</span>";
    items.forEach(function (i) { rail += '<span class="item' + (i[0] === on ? " on" : "") + '">' + icon(i[0]) + i[1] + "</span>"; });
    rail += '<div class="foot"><span class="item">' + icon("suche") + "Suchen</span>";
    rail += '<div class="me"><span class="crest" style="clip-path:none;border-radius:50%;width:30px;height:30px;padding:0;background:var(--ink);color:var(--paper)">' + who[0] + "</span>" + who[1] + "</div></div></nav>";
    var top = '<header class="topbar"><span class="crest">HCZ</span><span class="team">' + (app.dataset.teamShort || "Herren 1") + "<small>HC Zürichsee</small></span>";
    top += '<span class="sq line" title="Suchen">' + icon("suche") + '</span><span class="sq" title="Video hochladen">' + icon("plus") + "</span>";
    top += "</header>";
    var bar = '<nav class="tabbar">';
    items.forEach(function (i) { bar += '<span class="' + (i[0] === on ? "on" : "") + '">' + icon(i[0]) + i[1] + "</span>"; });
    bar += "</nav>";
    var main = app.querySelector(".main");
    app.insertAdjacentHTML("afterbegin", rail);
    var col = document.createElement("div");
    col.style.cssText = "flex:1;min-width:0;display:flex;flex-direction:column";
    col.innerHTML = top;
    col.appendChild(main);
    col.insertAdjacentHTML("beforeend", bar);
    app.appendChild(col);
  }

  /* ---------- seeded jitter for marker strokes ---------- */
  function rng(seed) { var s = seed >>> 0 || 1; return function () { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; }; }
  function smooth(p) {
    var d = "M" + p[0][0].toFixed(1) + " " + p[0][1].toFixed(1);
    for (var i = 1; i < p.length - 1; i++) {
      var mx = (p[i][0] + p[i + 1][0]) / 2, my = (p[i][1] + p[i + 1][1]) / 2;
      d += " Q" + p[i][0].toFixed(1) + " " + p[i][1].toFixed(1) + " " + mx.toFixed(1) + " " + my.toFixed(1);
    }
    var l = p[p.length - 1];
    return d + " L" + l[0].toFixed(1) + " " + l[1].toFixed(1);
  }
  var MARK = {
    under: function (r) { return [[[2, 55 + r() * 20], [30, 38 + r() * 25], [62, 52 + r() * 25], [98, 34 + r() * 30]]]; },
    hl: function (r) { return [[[1, 50 + r() * 10], [35, 46 + r() * 10], [70, 54 + r() * 8], [99, 46 + r() * 10]]]; },
    circle: function (r) {
      var p = [], n = 13, a0 = -2.4 + r() * 0.5;
      for (var i = 0; i <= n; i++) { var a = a0 + (i / n) * Math.PI * 2.14, k = 1 - i * 0.006 + (r() - 0.5) * 0.06; p.push([50 + Math.cos(a) * 46 * k, 50 + Math.sin(a) * 44 * k]); }
      return [p];
    },
    strike: function (r) { return [[[8, 78 + r() * 10], [45, 50 + r() * 8], [92, 18 + r() * 10]]]; },
    tick: function (r) { return [[[10, 52 + r() * 8], [36, 82 + r() * 6], [58, 44], [104, -18 + r() * 12]]]; }
  };
  function marks(root) {
    root.querySelectorAll("[data-mark]").forEach(function (el, i) {
      var kind = el.dataset.mark, r = rng(kind.length * 7919 + i * 104729 + (el.textContent.length + 3) * 31);
      var cls = kind === "hl" ? "mk hl harz" : "mk " + kind;
      var svg = '<svg class="' + cls + '" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">';
      MARK[kind](r).forEach(function (p) { svg += '<path d="' + smooth(p) + '"/>'; });
      el.insertAdjacentHTML("beforeend", svg + "</svg>");
    });
  }

  /* ---------- court: half court 20 m wide, goal at the top, 10 units per metre ---------- */
  function half() {
    return '<rect x="-2" y="-2" width="204" height="130" fill="var(--floor)"/>'
      + '<path d="M40 0 A60 60 0 0 0 85 60 L115 60 A60 60 0 0 0 160 0 Z" fill="var(--floor-area)"/>'
      + '<g fill="none" stroke="var(--line)" stroke-width="1.8"><path d="M40 0 A60 60 0 0 0 85 60 L115 60 A60 60 0 0 0 160 0"/>'
      + '<path d="M10 0 A90 90 0 0 0 85 90 L115 90 A90 90 0 0 0 190 0" stroke-dasharray="6 4.5" stroke-width="1.5"/>'
      + '<path d="M95 70h10M97.5 40h5"/><path d="M0 1h200" stroke-width="2.4"/></g>'
      + '<rect x="85" y="-1.5" width="30" height="4.5" fill="var(--ink)"/>';
  }
  function dot(p, us) {
    return us ? '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="6" fill="var(--club)" stroke="#fff" stroke-width="1.6"/>'
      : '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="5.6" fill="#fff" stroke="var(--ink)" stroke-width="1.6"/>';
  }
  function seg(a, dash) {
    var dx = a[2] - a[0], dy = a[3] - a[1], l = Math.hypot(dx, dy), ux = dx / l, uy = dy / l, x = a[2], y = a[3];
    var h = dash ? "" : '<path d="M' + (x - ux * 9 - uy * 4.5) + " " + (y - uy * 9 + ux * 4.5) + "L" + x + " " + y + "L" + (x - ux * 9 + uy * 4.5) + " " + (y - uy * 9 - ux * 4.5) + '" fill="none" stroke="var(--ink)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>';
    return '<path d="M' + a[0] + " " + a[1] + "L" + x + " " + y + '" stroke="var(--ink)" stroke-width="2.4" stroke-linecap="round" fill="none"' + (dash ? ' stroke-dasharray="1 6"' : "") + "/>" + h;
  }
  var D60 = [[34, 46], [60, 62], [88, 70], [112, 70], [140, 62], [166, 46]];
  var A = [[100, 104], [52, 92], [150, 92], [14, 26], [187, 22], [104, 64]];
  var SC = {
    ra: { us: D60, them: A, pass: [150, 92, 187, 22], shot: [187, 22, 112, 5] },
    tv: { us: [[156, 104], [118, 116], [58, 108]], them: [[100, 50], [66, 90], [38, 62]], pass: [66, 90, 100, 50], shot: [100, 50, 93, 5] },
    kr: { us: [[100, 104], [52, 92], [150, 92], [14, 26], [187, 22], [97, 64]], them: D60, pass: [52, 92, 97, 64], shot: [97, 64, 90, 5] },
    p1: { us: [[101, 9]], them: [[187, 22], [150, 90]], shot: [187, 22, 108, 6] },
    p2: { us: [[96, 9]], them: [[58, 86], [100, 100]], shot: [58, 86, 91, 6] },
    p3: { us: [[100, 18]], them: [[104, 64], [142, 92]], shot: [104, 64, 111, 5] },
    d60: { us: D60, them: A },
    d51: { us: [[34, 46], [60, 62], [100, 96], [112, 70], [140, 62], [166, 46]], them: A },
    kz: { us: [[100, 104], [52, 92], [150, 92], [14, 26], [187, 22], [104, 64]], them: [], pass: [100, 104, 60, 96], shot: [52, 92, 96, 74] },
    gs: { us: [[20, 110], [180, 110], [100, 118]], them: [], pass: [100, 118, 180, 110], shot: [180, 110, 150, 30] },
    leer: { us: [], them: [] }
  };
  function courts(root) {
    root.querySelectorAll("svg.mf[data-mf]").forEach(function (s) {
      var c = SC[s.dataset.mf] || SC.leer, h = half();
      if (c.pass) h += seg(c.pass, true);
      if (c.shot) h += seg(c.shot, false);
      c.them.forEach(function (p) { h += dot(p, false); });
      c.us.forEach(function (p) { h += dot(p, true); });
      s.setAttribute("viewBox", "0 0 200 124"); s.setAttribute("aria-hidden", "true"); s.innerHTML = h;
    });
    root.querySelectorAll("svg.shotmap").forEach(function (s) {
      var shots = [[14, 24, 1], [24, 36, 0], [186, 20, 1], [190, 30, 1], [178, 38, 0], [100, 66, 1], [92, 64, 1], [108, 68, 1], [116, 66, 0], [58, 86, 1], [50, 94, 0], [68, 98, 1], [100, 100, 1], [94, 106, 0], [108, 102, 1], [142, 90, 1], [150, 96, 0], [134, 100, 1], [100, 73, 1], [85, 71, 1], [154, 82, 0], [42, 72, 1], [100, 34, 1], [113, 37, 1], [89, 38, 0], [164, 62, 0]];
      var h = half();
      shots.forEach(function (d) { h += d[2] ? '<circle cx="' + d[0] + '" cy="' + d[1] + '" r="4.6" fill="var(--club)" stroke="#fff" stroke-width="1.2"/>' : '<path d="M' + (d[0] - 3.4) + " " + (d[1] - 3.4) + "l6.8 6.8M" + (d[0] + 3.4) + " " + (d[1] - 3.4) + 'l-6.8 6.8" stroke="var(--ink)" stroke-width="1.8" stroke-linecap="round"/>'; });
      s.setAttribute("viewBox", "0 0 200 124"); s.innerHTML = h;
    });
    /* whole court seen from the camera: used as the stand-in for a video frame */
    root.querySelectorAll("svg.videobild").forEach(function (s) {
      var L = "var(--line)";
      var h = '<rect width="400" height="200" fill="var(--floor)"/>'
        + '<path d="M0 40 A60 60 0 0 1 60 85 L60 115 A60 60 0 0 1 0 160 Z" fill="var(--floor-area)"/><path d="M400 40 A60 60 0 0 0 340 85 L340 115 A60 60 0 0 0 400 160 Z" fill="var(--floor-area)"/>'
        + '<g fill="none" stroke="' + L + '" stroke-width="2"><rect x="1" y="1" width="398" height="198"/><path d="M200 0v200"/>'
        + '<path d="M0 40 A60 60 0 0 1 60 85 L60 115 A60 60 0 0 1 0 160"/><path d="M400 40 A60 60 0 0 0 340 85 L340 115 A60 60 0 0 0 400 160"/>'
        + '<path d="M0 10 A90 90 0 0 1 90 85 L90 115 A90 90 0 0 1 0 190" stroke-dasharray="7 5"/><path d="M400 10 A90 90 0 0 0 310 85 L310 115 A90 90 0 0 0 400 190" stroke-dasharray="7 5"/></g>';
      [[330, 60], [318, 84], [312, 104], [320, 128], [336, 150], [352, 100]].forEach(function (p) { h += '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="6.5" fill="var(--club)" stroke="#fff" stroke-width="1.6"/>'; });
      [[262, 100], [276, 50], [280, 152], [372, 22], [378, 180], [326, 106], [392, 100]].forEach(function (p) { h += '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="6" fill="#fff" stroke="var(--ink)" stroke-width="1.6"/>'; });
      h += '<circle cx="372" cy="22" r="12" fill="none" stroke="var(--harz)" stroke-width="3"/>';
      s.setAttribute("viewBox", "0 0 400 200"); s.setAttribute("aria-hidden", "true"); s.innerHTML = h;
    });
  }

  /* ---------- zones and small series ---------- */
  function zones(root) {
    root.querySelectorAll("svg.zonen").forEach(function (s) {
      var z = [["LA", 16, 30, 2], ["RL", 50, 96, 3], ["RM", 100, 108, 2], ["RR", 150, 96, 1], ["RA", 174, 36, 9], ["KM", 100, 72, 1]];
      var max = Math.max.apply(null, z.map(function (d) { return d[3]; })), h = half();
      z.forEach(function (d) {
        var r = 6.6 * Math.sqrt(d[3]), top = d[3] === max;
        h += '<circle cx="' + d[1] + '" cy="' + d[2] + '" r="' + r.toFixed(1) + '" fill="' + (top ? "var(--harz)" : "#fff") + '" stroke="var(--ink)" stroke-width="1.6"/>';
        h += '<text x="' + d[1] + '" y="' + (d[2] + 5.2) + '">' + d[3] + "</text>";
      });
      s.setAttribute("viewBox", "0 0 200 124"); s.innerHTML = h;
    });
    root.querySelectorAll("svg.reihe").forEach(function (s) {
      var v = s.dataset.v.split(",").map(Number), signed = s.hasAttribute("data-signed"), n = v.length;
      var W = 150, H = 62, bw = 18, gap = (W - n * bw) / (n - 1), max = Math.max.apply(null, v.map(Math.abs)), c = "";
      var base = signed ? 40 : H, span = signed ? 24 : H - 18;
      if (signed) c += '<line x1="0" x2="' + W + '" y1="' + base + '" y2="' + base + '" stroke="var(--ink)" stroke-width="1.2"/>';
      v.forEach(function (d, i) {
        var x = i * (bw + gap), hgt = Math.max(2, Math.abs(d) / max * span), y = d >= 0 ? base - hgt : base, last = i === n - 1;
        var fill = signed ? (d >= 0 ? "var(--win)" : "var(--loss)") : (last ? "var(--club)" : "var(--floor-area)");
        c += '<rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + bw + '" height="' + hgt.toFixed(1) + '" fill="' + fill + '"/>';
        var ty = d >= 0 ? y - 4 : y + hgt + 12;
        c += '<text x="' + (x + bw / 2).toFixed(1) + '" y="' + ty.toFixed(1) + '"' + (last ? ' class="now"' : "") + ">" + (signed && d > 0 ? "+" : "") + d + "</text>";
      });
      s.setAttribute("viewBox", "0 -8 " + W + " " + (H + 16)); s.innerHTML = c;
    });
  }

  /* ---------- LED ghosts ---------- */
  function leds(root) {
    root.querySelectorAll(".led:not([data-ghost])").forEach(function (el) {
      var t = el.textContent; el.dataset.ghost = t.replace(/[0-9]/g, "8"); el.innerHTML = "<i>" + t + "</i>";
    });
  }

  /* ---------- charts: one scale per chart ---------- */
  function charts(root) {
    root.querySelectorAll("svg.flow").forEach(function (s) {
      var data = [[0, 0], [5, 1], [10, 1], [15, 2], [20, 3], [25, 3], [30, 4], [35, 4], [38, 4], [41, 3], [44, 3], [50, 5], [55, 7], [60, 8]];
      var X0 = 30, X1 = 506, Y0 = 132, Y1 = 16, MIN = -2, MAX = 10;
      function x(m) { return X0 + (X1 - X0) * m / 60; } function y(v) { return Y0 - (Y0 - Y1) * (v - MIN) / (MAX - MIN); }
      var c = '<rect x="' + x(38) + '" y="' + Y1 + '" width="' + (x(44) - x(38)) + '" height="' + (Y0 - Y1) + '" fill="var(--harz)"/>';
      [0, 4, 8].forEach(function (v) { c += '<line x1="' + X0 + '" x2="' + X1 + '" y1="' + y(v) + '" y2="' + y(v) + '" stroke="' + (v ? "var(--rule)" : "var(--ink)") + '" stroke-width="' + (v ? 1 : 1.5) + '"/><text x="' + (X0 - 7) + '" y="' + (y(v) + 4) + '" text-anchor="end">' + (v ? "+" + v : "0") + "</text>"; });
      c += '<line x1="' + x(30) + '" x2="' + x(30) + '" y1="' + Y1 + '" y2="' + Y0 + '" stroke="var(--ink-3)" stroke-width="1" stroke-dasharray="2 4"/>';
      [[0, "Anwurf"], [30, "Halbzeit 13:9"], [60, "Schluss"]].forEach(function (t) { c += '<text x="' + x(t[0]) + '" y="' + (Y0 + 17) + '" text-anchor="' + (t[0] === 0 ? "start" : t[0] === 60 ? "end" : "middle") + '">' + t[1] + "</text>"; });
      var pts = data.map(function (d) { return x(d[0]).toFixed(1) + "," + y(d[1]).toFixed(1); }).join(" ");
      c += '<polyline points="' + pts + '" fill="none" stroke="var(--club)" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>';
      c += '<circle cx="' + x(60) + '" cy="' + y(8) + '" r="5" fill="var(--club)"/><text x="' + (x(60) - 10) + '" y="' + (y(8) - 9) + '" text-anchor="end" class="big">+8</text>';
      c += '<text x="' + x(41) + '" y="' + (Y1 + 13) + '" text-anchor="middle" class="on">38. bis 44.</text>';
      s.setAttribute("viewBox", "0 0 520 156"); s.innerHTML = c;
    });
    root.querySelectorAll("svg.zeitleiste").forEach(function (s) {
      var W = 1000, us = [2, 5, 9, 11, 14, 17, 19, 22, 24, 26, 27, 29, 29.5, 32, 35, 36, 46, 48, 50, 51, 53, 54, 56, 57, 58, 59.5], them = [3, 7, 12, 16, 20, 23, 25, 28, 30, 39, 40, 41, 42, 43, 44, 49, 55, 58.5];
      function x(m) { return (m / 60) * W; }
      var c = '<rect x="' + x(38) + '" y="0" width="' + (x(44) - x(38)) + '" height="64" fill="var(--harz)" opacity=".85"/>';
      c += '<rect x="0" y="52" width="' + x(21) + '" height="8" fill="#5d87a3"/><rect x="' + x(21) + '" y="52" width="' + (x(33) - x(21)) + '" height="8" fill="#8ab4cd"/><rect x="' + x(33) + '" y="52" width="' + (W - x(33)) + '" height="8" fill="#5d87a3"/>';
      c += '<line x1="0" x2="' + W + '" y1="28" y2="28" stroke="var(--night-ink-2)" stroke-width="1"/><line x1="' + x(30) + '" x2="' + x(30) + '" y1="2" y2="50" stroke="var(--night-ink-2)" stroke-width="1" stroke-dasharray="2 4"/>';
      us.forEach(function (m) { c += '<rect x="' + (x(m) - 2.5) + '" y="8" width="5" height="20" fill="var(--club)" stroke="#fff" stroke-width=".8"/>'; });
      them.forEach(function (m) { c += '<rect x="' + (x(m) - 2.5) + '" y="28" width="5" height="17" fill="#eef0ed"/>'; });
      c += '<line x1="' + x(41.2) + '" x2="' + x(41.2) + '" y1="-4" y2="64" stroke="#fff" stroke-width="2.5"/><circle cx="' + x(41.2) + '" cy="-4" r="6" fill="#fff"/>';
      s.setAttribute("viewBox", "-8 -12 1016 80"); s.setAttribute("preserveAspectRatio", "none"); s.innerHTML = c;
    });
  }

  var JERSEY = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M8.5 4 4 6.8l1.8 3.6L8 9.2V20h8V9.2l2.2 1.2L20 6.8 15.5 4c-.6 1.3-1.9 2-3.5 2s-2.9-.7-3.5-2z"/></svg>';
  function extras(root) {
    root.querySelectorAll(".sticker .pic").forEach(function (p) { p.insertAdjacentHTML("afterbegin", JERSEY); });
    root.querySelectorAll(".kits span").forEach(function (k) { k.insertAdjacentHTML("afterbegin", JERSEY.replace('fill="currentColor"', 'fill="' + k.dataset.c + '"')); });
    root.querySelectorAll("svg.qrc").forEach(function (s) {
      var r = rng(4711), h = "", n = 21;
      for (var y = 0; y < n; y++) for (var x = 0; x < n; x++) {
        var eye = (x < 7 && y < 7) || (x > 13 && y < 7) || (x < 7 && y > 13);
        var on = eye ? (x % 6 === 0 || y % 6 === 0 || (x > 13 ? x - 14 : x) % 6 === 0 || (y > 13 ? y - 14 : y) % 6 === 0 || ((x % 14 > 1 && x % 14 < 5) && (y % 14 > 1 && y % 14 < 5))) : r() > 0.52;
        if (on) h += '<rect x="' + x + '" y="' + y + '" width="1.02" height="1.02"/>';
      }
      s.setAttribute("viewBox", "0 0 21 21"); s.setAttribute("fill", "#14171a"); s.setAttribute("aria-hidden", "true"); s.innerHTML = h;
    });
  }
  function dress(root) { root.querySelectorAll(".halle.app").forEach(chrome); leds(root); courts(root); zones(root); charts(root); extras(root); marks(root); }

  /* ---------- frames: one template, shown at desktop and phone width ---------- */
  var W = { desk: 1280, phone: 390 };
  function fit() {
    document.querySelectorAll(".fit").forEach(function (f) {
      var fr = f.firstElementChild, w = fr.offsetWidth, k = Math.min(Number(f.dataset.max || 1), f.clientWidth / w);
      fr.style.transform = "scale(" + k + ")"; f.style.height = Math.ceil(fr.offsetHeight * k) + "px";
    });
  }
  document.querySelectorAll("[data-tpl]").forEach(function (slot) {
    var tpl = document.getElementById(slot.dataset.tpl); if (!tpl) return;
    var kind = slot.dataset.w, node = tpl.content.cloneNode(true), app = node.firstElementChild;
    app.classList.add(kind === "desk" ? "is-desk" : "is-phone");
    var fr = document.createElement("div"); fr.className = "frame " + kind; fr.style.width = W[kind] + "px";
    fr.appendChild(node); slot.classList.add("fit"); slot.appendChild(fr);
  });
  dress(document);
  fit();
  window.addEventListener("resize", fit);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
  window.addEventListener("load", fit);

  /* ---------- club colour switch ---------- */
  document.querySelectorAll("[data-club]").forEach(function (b) {
    b.addEventListener("click", function () {
      var r = document.documentElement.style;
      r.setProperty("--club-pick", b.dataset.club); r.setProperty("--club-ink-pick", b.dataset.on); r.setProperty("--club-text-pick", b.dataset.text);
      document.querySelectorAll("[data-club]").forEach(function (o) { o.setAttribute("aria-pressed", o === b ? "true" : "false"); });
    });
  });
})();
