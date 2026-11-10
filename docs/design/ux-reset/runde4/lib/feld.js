/* Court, charts and demo data shared by both directions. Colours come from CSS variables:
   --floor --area --line (court), --us --us-edge --them --them-edge (players), --ink, --mark. */
var FELD = (function () {
  function half() {
    return '<rect x="-2" y="-2" width="204" height="130" fill="var(--floor)"/><path d="M40 0A60 60 0 0 0 85 60h30A60 60 0 0 0 160 0z" fill="var(--area)"/>'
      + '<g fill="none" stroke="var(--line)" stroke-width="1.6"><path d="M40 0A60 60 0 0 0 85 60h30A60 60 0 0 0 160 0"/><path d="M10 0A90 90 0 0 0 85 90h30A90 90 0 0 0 190 0" stroke-dasharray="6 4.5"/><path d="M95 70h10"/></g>'
      + '<rect x="84" y="-1" width="32" height="5" fill="var(--ink)"/>';
  }
  function us(p) { return '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="6.4" fill="var(--us)" stroke="var(--us-edge)" stroke-width="1.6"/>'; }
  function them(p) { return '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="5.6" fill="var(--them)" stroke="var(--them-edge)" stroke-width="1.6"/>'; }
  function arrow(a, dash) {
    var dx = a[2] - a[0], dy = a[3] - a[1], l = Math.hypot(dx, dy), ux = dx / l, uy = dy / l, x = a[2], y = a[3];
    var s = '<path d="M' + a[0] + " " + a[1] + "L" + x + " " + y + '" stroke="var(--ink)" stroke-width="' + (dash ? 1.8 : 2.4) + '" fill="none" stroke-linecap="round"' + (dash ? ' stroke-dasharray="1.5 4.5"' : "") + "/>";
    if (!dash) s += '<path d="M' + (x - ux * 9 - uy * 5) + " " + (y - uy * 9 + ux * 5) + "L" + x + " " + y + "L" + (x - ux * 9 + uy * 5) + " " + (y - uy * 9 - ux * 5) + 'z" fill="var(--ink)"/>';
    return s;
  }
  var D60 = [[34, 46], [60, 62], [88, 70], [112, 70], [140, 62], [166, 46]], A = [[100, 104], [52, 92], [150, 92], [14, 26], [187, 22], [104, 64]];
  var SC = {
    ra: { u: D60, t: A, pass: [150, 92, 187, 22], shot: [187, 22, 113, 6] },
    tv: { u: [[156, 104], [118, 116], [58, 108]], t: [[100, 50], [66, 90], [38, 62]], pass: [66, 90, 100, 50], shot: [100, 50, 93, 6] },
    kr: { u: [[100, 104], [52, 92], [150, 92], [14, 26], [187, 22], [97, 64]], t: D60, pass: [52, 92, 97, 64], shot: [97, 64, 90, 6] },
    d60: { u: D60, t: A }
  };
  var SHOTS = [[14, 24, 1], [24, 36, 0], [186, 20, 1], [190, 30, 1], [178, 38, 0], [100, 66, 1], [92, 64, 1], [108, 68, 1], [116, 66, 0], [58, 86, 1], [50, 94, 0], [68, 98, 1], [100, 100, 1], [94, 106, 0], [108, 102, 1], [142, 90, 1], [150, 96, 0], [134, 100, 1], [100, 73, 1], [85, 71, 1], [154, 82, 0], [42, 72, 1], [100, 34, 1], [113, 37, 1], [89, 38, 0], [164, 62, 0]];
  var ZONES = [[16, 30, 2], [50, 96, 3], [100, 108, 2], [150, 96, 1], [174, 36, 9], [100, 72, 1]];
  function courts(root) {
    root.querySelectorAll("svg.mf[data-mf]").forEach(function (s) {
      var c = SC[s.dataset.mf], h = half();
      if (c.pass) h += arrow(c.pass, 1);
      c.t.forEach(function (p) { h += them(p); }); c.u.forEach(function (p) { h += us(p); });
      if (c.shot) h += arrow(c.shot, 0);
      if (s.classList.contains("ghost")) h = '<g opacity=".38">' + h + "</g>";
      s.setAttribute("viewBox", "0 0 200 124"); s.setAttribute("aria-hidden", "true"); s.innerHTML = h;
    });
    root.querySelectorAll("svg.shotmap").forEach(function (s) {
      var h = half();
      SHOTS.forEach(function (d) { h += d[2] ? '<circle cx="' + d[0] + '" cy="' + d[1] + '" r="4.6" fill="var(--us)" stroke="var(--us-edge)" stroke-width="1.3"/>' : '<path d="M' + (d[0] - 3.4) + " " + (d[1] - 3.4) + "l6.8 6.8M" + (d[0] + 3.4) + " " + (d[1] - 3.4) + 'l-6.8 6.8" stroke="var(--ink)" stroke-width="1.8" stroke-linecap="round"/>'; });
      s.setAttribute("viewBox", "0 0 200 124"); s.innerHTML = h;
    });
    root.querySelectorAll("svg.zonen").forEach(function (s) {
      var h = half();
      ZONES.forEach(function (d) {
        var r = Math.max(11, 6.6 * Math.sqrt(d[2])), top = d[2] === 9;
        h += '<circle cx="' + d[0] + '" cy="' + d[1] + '" r="' + r.toFixed(1) + '" fill="' + (top ? "var(--mark)" : "var(--paper)") + '" stroke="var(--ink)" stroke-width="1.6"/><text x="' + d[0] + '" y="' + (d[1] + 5.5) + '" text-anchor="middle" class="zn' + (top ? " on" : "") + '">' + d[2] + "</text>";
      });
      s.setAttribute("viewBox", "0 0 200 124"); s.innerHTML = h;
    });
  }
  /* the hall seen from the gallery, as a stand-in for a video frame */
  function videobild(s, o) {
    o = o || {};
    function P(x, y) { var t = y / 20, sy = 92 + 268 * Math.pow(t, 1.15), hw = 230 + 60 * t; return [+(322 + (x - 28) / 12 * hw).toFixed(1), +sy.toFixed(1)]; }
    function line(pts) { return "M" + pts.map(function (p) { return P(p[0], p[1]).join(" "); }).join("L"); }
    function dee(r) { var pts = []; for (var i = 0; i <= 20; i++) { var t = Math.PI / 2 * i / 20; pts.push([40 - r * Math.sin(t), 8.5 - r * Math.cos(t)]); } pts.push([40 - r, 11.5]); for (var j = 0; j <= 20; j++) { var u = Math.PI / 2 * j / 20; pts.push([40 - r * Math.cos(u), 11.5 + r * Math.sin(u)]); } return pts; }
    var h = '<rect width="640" height="360" fill="#121214"/><rect width="640" height="92" fill="#1d1c20"/>';
    for (var i = 0; i < 32; i++) h += '<rect x="' + (i * 20 + 4) + '" y="' + (36 + (i * 7) % 18) + '" width="11" height="18" fill="#2b2a30"/>';
    var c = [[0, 0], [40, 0], [40, 20], [0, 20]].map(function (p) { return P(p[0], p[1]).join(" "); });
    h += '<path d="M' + c.join("L") + 'Z" fill="' + (o.floor || "#c49a63") + '"/>';
    for (var k = 0; k < 40; k++) { var a = P(k, 0), b = P(k, 20); h += '<path d="M' + a[0] + " " + a[1] + "L" + b[0] + " " + b[1] + '" stroke="#0000001c" stroke-width="1"/>'; }
    h += '<path d="' + line(dee(6)) + 'Z" fill="' + (o.area || "#4f7fa3") + '"/>';
    h += '<g fill="none" stroke="#fff" stroke-width="2.2"><path d="M' + c.join("L") + 'Z"/><path d="' + line([[20, 0], [20, 20]]) + '"/><path d="' + line(dee(6)) + '"/><path d="' + line(dee(9)) + '" stroke-dasharray="9 7"/></g>';
    var g1 = P(40, 8.5), g2 = P(40, 11.5); h += '<path d="M' + g1[0] + " " + g1[1] + "L" + (g1[0] + 10) + " " + (g1[1] - 30) + "L" + (g2[0] + 12) + " " + (g2[1] - 34) + "L" + g2[0] + " " + g2[1] + '" fill="none" stroke="#fff" stroke-width="3"/>';
    var PL = [[34.6, 4.2, 1], [33.2, 7.4, 1], [32.8, 10.8, 1], [33.4, 14, 1], [35, 16.4, 1], [24, 9.4, 1], [26.5, 7, 0], [21, 13.5, 0], [29.5, 3, 0], [37.6, 2.2, 0], [37.4, 18.6, 0], [22.6, 11.8, 0], [39.5, 10, 1]];
    PL.forEach(function (p) { var q = P(p[0], p[1]), sc = 0.55 + p[1] / 22; h += '<ellipse cx="' + q[0] + '" cy="' + (q[1] + 2) + '" rx="' + 9 * sc + '" ry="' + 3 * sc + '" fill="#0006"/><rect x="' + (q[0] - 5 * sc) + '" y="' + (q[1] - 28 * sc) + '" width="' + 10 * sc + '" height="' + 28 * sc + '" rx="' + 4 * sc + '" fill="' + (p[2] ? "var(--club)" : "#f2f2f2") + '" stroke="#121214" stroke-width="1.2"/>'; });
    if (o.ring) { var r = P(37.6, 2.2); h += '<circle cx="' + r[0] + '" cy="' + (r[1] - 12) + '" r="20" fill="none" stroke="' + o.ring + '" stroke-width="3"/>'; }
    s.setAttribute("viewBox", "0 0 640 360"); s.setAttribute("aria-hidden", "true"); s.innerHTML = h;
  }
  /* goal difference over 60 minutes */
  var FLOW = [[0, 0], [5, 1], [10, 1], [15, 2], [20, 3], [25, 3], [30, 4], [35, 4], [38, 4], [41, 3], [44, 3], [50, 5], [55, 7], [60, 8]];
  var TL = { us: [2, 5, 9, 11, 14, 17, 19, 22, 24, 26, 27, 29, 29.5, 32, 35, 36, 46, 48, 50, 51, 53, 54, 56, 57, 58, 59.5], them: [3, 7, 12, 16, 20, 23, 25, 28, 30, 39, 40, 41, 42, 43, 44, 49, 55, 58.5] };
  function zeitleiste(s) {
    var W = 1000; function x(m) { return m / 60 * W; }
    var c = '<rect x="' + x(38) + '" y="0" width="' + (x(44) - x(38)) + '" height="66" fill="var(--att-soft)" stroke="var(--att)" stroke-width="2.5" vector-effect="non-scaling-stroke"/>';
    c += '<rect x="0" y="56" width="' + x(21) + '" height="10" fill="#3f6d8f"/><rect x="' + x(21) + '" y="56" width="' + (x(33) - x(21)) + '" height="10" fill="#86b5d6"/><rect x="' + x(33) + '" y="56" width="' + (W - x(33)) + '" height="10" fill="#3f6d8f"/>';
    c += '<line x1="0" x2="' + W + '" y1="28" y2="28" stroke="var(--tl-axis)"/><line x1="' + x(30) + '" x2="' + x(30) + '" y1="0" y2="52" stroke="var(--tl-axis)" stroke-dasharray="2 4"/>';
    TL.us.forEach(function (m) { c += '<rect x="' + (x(m) - 2.5) + '" y="6" width="5" height="22" fill="var(--tl-us)"/>'; });
    TL.them.forEach(function (m) { c += '<rect x="' + (x(m) - 2.5) + '" y="28" width="5" height="18" fill="var(--tl-them)"/>'; });
    c += '<line x1="' + x(41.2) + '" x2="' + x(41.2) + '" y1="-6" y2="70" stroke="var(--tl-head)" stroke-width="3"/><circle cx="' + x(41.2) + '" cy="-8" r="6" fill="var(--tl-head)"/>';
    s.setAttribute("viewBox", "-8 -16 1016 88"); s.setAttribute("preserveAspectRatio", "none"); s.innerHTML = c;
  }
  var GAMES = [
    { d: "Sa", dt: "31.10.", w: "auswärts", o: "BSV Stäfa", p: "33 Szenen · 2 Dinge · Ballverluste im Aufbau", mf: "tv", r: "19:26", res: "l", best: "graf", bn: "Elias, 6 Tore" },
    { d: "Sa", dt: "24.10.", w: "Heim", o: "HC Meilen", p: "Analyse läuft, noch etwa 25 Minuten", run: 62, r: "23:22", res: "w" },
    { d: "Sa", dt: "17.10.", w: "auswärts", o: "SG Horgen", nov: 1, r: "29:19", res: "w" },
    { d: "Sa", dt: "10.10.", w: "Heim", o: "TV Wädenswil", nov: 1, r: "24:27", res: "l" }];
  var FELDROWS = [["brunner", 7, 10, "70 %", "", 2, "", 1], ["graf", 5, 9, "56 %", "2/2", 3, 1, 1], ["schmid", 4, 8, "50 %", "", 2, "", 1], ["meier", 4, 5, "80 %", "", 1, 1, 0], ["roth", 3, 6, "50 %", "", 1, "", 1], ["baumann", 2, 4, "50 %", "", 1, 1, 0], ["rbrunner", 1, 3, "33 %", "", 1, "", 0]];
  /* fit frames to the window; club switch with buttons and ?club= */
  function frames() {
    document.querySelectorAll(".frame").forEach(function (f) { f.querySelector(".app").classList.add(f.classList.contains("desk") ? "is-desk" : "is-phone"); });
    function fit() { document.querySelectorAll(".fit").forEach(function (f) { var fr = f.firstElementChild, w = fr.offsetWidth, k = Math.min(1, f.clientWidth / w); fr.style.transform = "scale(" + k + ")"; f.style.height = Math.ceil(fr.offsetHeight * k) + "px"; }); }
    fit(); addEventListener("resize", fit); addEventListener("load", fit); if (document.fonts) document.fonts.ready.then(fit);
    var root = document.documentElement, q = (location.search.match(/club=(\w+)/) || [])[1];
    function set(c) { root.dataset.club = c; document.querySelectorAll(".sw button").forEach(function (o) { o.setAttribute("aria-pressed", o.dataset.c === c ? "true" : "false"); }); setTimeout(fit, 30); }
    set(q || root.dataset.club || "rot");
    document.querySelectorAll(".sw button").forEach(function (b) { b.addEventListener("click", function () { set(b.dataset.c); }); });
  }
  return { courts: courts, videobild: videobild, zeitleiste: zeitleiste, FLOW: FLOW, GAMES: GAMES, FELDROWS: FELDROWS, frames: frames, half: half };
})();
