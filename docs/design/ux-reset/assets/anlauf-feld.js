/* ===== Anlauf: graphics =====
   Court geometry in metres and every drawing of the system. Each function fills one <svg> from
   its data attributes; the colours come from the kit of the nearest [data-club] element.
   Port to React components: Bundle, Zones, Flight, Rail, Series, DiffBars, TacticsCamera, Hall.

   Rule for all of them: a line is a measured way. What the analysis does not measure is not
   drawn: no ball flight, no pass lines. Confirmed is solid, estimated is dashed or lighter. */

var NS = ' vector-effect="non-scaling-stroke"';
function kitOf(el) { var a = el.closest("[data-club]"); return a && a._kit; }
function d(pts) { return pts.map(function (p, i) { return (i ? "L" : "M") + p[0].toFixed(2) + " " + p[1].toFixed(2); }).join(""); }
/* Catmull-Rom through measured points, n samples per segment. A display smoothing, nothing added. */
function cr(pts, n) {
  if (pts.length < 2) return pts.slice();
  var out = [], P = [pts[0]].concat(pts, [pts[pts.length - 1]]);
  for (var i = 1; i < P.length - 2; i++) for (var k = 0; k < n; k++) {
    var t = k / n, t2 = t * t, t3 = t2 * t, a = P[i - 1], b = P[i], c = P[i + 1], e = P[i + 2];
    out.push([0, 1].map(function (j) { return 0.5 * (2 * b[j] + (-a[j] + c[j]) * t + (2 * a[j] - 5 * b[j] + 4 * c[j] - e[j]) * t2 + (-a[j] + 3 * b[j] - 3 * c[j] + e[j]) * t3); }));
  }
  out.push(pts[pts.length - 1]);
  return out;
}

/* ---------- court: 40 x 20 m, goals at x = 0 and x = 40 ---------- */
function goalArea(r) {
  var k = Math.sqrt(r * r - 8.5 * 8.5 > 0 ? r * r - 8.5 * 8.5 : 0), y0 = r > 8.5 ? 0 : 8.5 - r, x0 = r > 8.5 ? k : 0;
  return "M" + x0.toFixed(3) + " " + y0.toFixed(3) + " A" + r + " " + r + " 0 0 1 " + r + " 8.5 L" + r + " 11.5 A" + r + " " + r + " 0 0 1 " + x0.toFixed(3) + " " + (20 - y0).toFixed(3);
}
function courtLines(o) {
  var L = o.line, w = o.lw || 1.5, h = "";
  if (o.floor) h += '<rect x="-3" y="-3" width="46" height="26" fill="' + o.floor + '"/>';
  if (o.area) h += '<path d="' + goalArea(6) + ' Z" fill="' + o.area + '"/><path d="' + goalArea(6) + ' Z" fill="' + o.area + '" transform="matrix(-1 0 0 1 40 0)"/>';
  h += '<g fill="none" stroke="' + L + '" stroke-width="' + w + '"><rect x="0" y="0" width="40" height="20"' + NS + '/><path d="M20 0V20"' + NS + "/>";
  [1, -1].forEach(function (s) {
    h += "<g" + (s < 0 ? ' transform="matrix(-1 0 0 1 40 0)"' : "") + '><path d="' + goalArea(6) + '"' + NS + '/><path d="' + goalArea(9) + '" stroke-dasharray="5 4"' + NS + '/><path d="M7 9.5V10.5M4 9.85V10.15"' + NS + "/></g>";
  });
  return h + '</g><rect x="-0.6" y="8.5" width="0.6" height="3" fill="' + L + '"/><rect x="40" y="8.5" width="0.6" height="3" fill="' + L + '"/>';
}
/* views of the full court: camL = our left half wide (desktop stage), halfB = left half turned, goal at the top */
var VIEWS = {
  camL: { box: [-1.2, -1.2, 34, 22.4], m: null, f: function (p) { return p; } },
  halfB: { box: [-0.6, -1.2, 21.2, 17.2], m: "matrix(0 1 1 0 0 0)", f: function (p) { return [p[1], p[0]]; } },
  halfDeep: { box: [-0.6, -0.9, 21.2, 18.6], m: "matrix(0 1 1 0 0 0)", f: function (p) { return [p[1], p[0]]; } }
};
function viewWrap(v, inner) { return v.m ? '<g transform="' + v.m + '">' + inner + "</g>" : inner; }
/* half court in its own coordinates (goal at the top), for bundles and zones */
var HALF_BOX = [-0.6, -1.2, 21.2, 17.2];
function halfCourt(ink) {
  var g = '<g fill="none" stroke="' + ink + '" stroke-width="1.2"><path d="M0 0H20V20H0Z"' + NS + "/>";
  g += '<path d="M2.5 0 A6 6 0 0 0 8.5 6 L11.5 6 A6 6 0 0 0 17.5 0"' + NS + "/>";
  g += '<path d="M0.47 0 A9 9 0 0 0 8.5 9 L11.5 9 A9 9 0 0 0 19.53 0" stroke-dasharray="4 3"' + NS + "/>";
  g += '<path d="M9.5 7H10.5M9.85 4H10.15"' + NS + "/></g>";
  return g + '<rect x="8.5" y="-0.7" width="3" height="0.7" fill="' + ink + '"/>';
}

/* ---------- Bundle: every goal of one kind as the scorer's run, then a thin straight line to the goal ----------
   data-b = key in BUNDLES, data-i = one goal only (scene tile), data-w = drawn width in px */
function bundle(svg) {
  var B = BUNDLES[svg.dataset.b], k = kitOf(svg), W = +svg.dataset.w || 360, kk = W / HALF_BOX[2], small = W < 160;
  if (B.opp) k = kit([k.club, k.club2], KITS[B.opp], k.ground);
  var list = B.pick(), rest = B.rest(), col = B.team === "us" ? k.clubLine : k.oppLine, pipe = B.team === "us" ? k.clubPipe : k.oppPipe;
  if (svg.dataset.i != null) { rest = []; list = [list[+svg.dataset.i % list.length]]; } /* one scene: its own run only */
  var h = '<g opacity=".38">' + halfCourt(k.ink) + "</g>";
  rest.forEach(function (g) { h += '<path d="' + d(cr(g.run, 6)) + '" fill="none" stroke="' + k.ink + '" stroke-opacity=".13" stroke-width="1"' + NS + "/>"; });
  list.forEach(function (g, i) {
    var dd = d(cr(g.run, 8)), w = small ? 1.6 : 2.6, est = g.est;
    if (pipe && !est) h += '<path d="' + dd + '" fill="none" stroke="' + pipe + '" stroke-width="' + (w + 2.4) + '" stroke-linecap="round"' + NS + "/>";
    h += '<path class="' + (est ? "ln-e" : "ln") + '" style="--i:' + i + '"' + (est ? "" : ' pathLength="1"') + ' d="' + dd + '" fill="none" stroke="' + col + '" stroke-width="' + w + '" stroke-opacity="' + (est ? 0.6 : 1) + '"' + (est ? ' stroke-dasharray="4 3.5"' : "") + ' stroke-linecap="round"' + NS + "/>";
    h += '<path d="M' + g.shot[0] + " " + g.shot[1] + "L" + g.aim[0] + " " + g.aim[1] + '" stroke="' + k.ink + '" stroke-opacity="' + (est ? 0.3 : 0.55) + '" stroke-width="1"' + NS + "/>";
    h += '<circle cx="' + g.shot[0] + '" cy="' + g.shot[1] + '" r="' + (small ? 2.4 : 3.6) / kk + '" fill="' + (est ? k.ground : col) + '" stroke="' + (pipe || col) + '" stroke-width="' + (est ? 1.5 : 1) + '"' + NS + "/>";
  });
  svg.setAttribute("viewBox", HALF_BOX.join(" ")); svg.innerHTML = h;
}
/* the empty field: no video, analysis running, or nothing found yet */
function emptyField(svg) { var k = kitOf(svg); svg.setAttribute("viewBox", HALF_BOX.join(" ")); svg.innerHTML = '<g opacity=".3">' + halfCourt(k.ink) + "</g>"; }

/* ---------- Zones: goals by position, counts at the zones, estimated shot spots as dots ---------- */
function zones(svg) {
  var k = kitOf(svg), W = +svg.dataset.w, kk = W / HALF_BOX[2], us = svg.dataset.who === "us", list = us ? GOALS.us : GOALS.them;
  var col = us ? k.clubLine : k.oppLine, pipe = us ? k.clubPipe : k.oppPipe, h = '<g opacity=".38">' + halfCourt(k.ink) + "</g>", cnt = {};
  list.forEach(function (g) { cnt[g.zone] = (cnt[g.zone] || 0) + 1; h += '<circle cx="' + g.shot[0] + '" cy="' + g.shot[1] + '" r="' + 3 / kk + '" fill="' + (g.est ? k.ground : col) + '" stroke="' + (pipe || col) + '" stroke-width="1.2"' + NS + "/>"; });
  var at = { la: [3.2, 4.4], ra: [16.8, 4.4], rl: [4.2, 13.6], rm: [10, 14.4], rr: [15.8, 13.6], kr: [10, 3.2], m7: [13.4, 7.6], gs: [10, 11.8] }, names = { la: "LA", ra: "RA", rl: "RL", rm: "RM", rr: "RR", kr: "Kreis", m7: "7 m", gs: "Gegenstoss" };
  var max = Math.max.apply(null, Object.keys(cnt).map(function (z) { return cnt[z]; }));
  Object.keys(cnt).forEach(function (z) {
    var p = at[z], big = cnt[z] === max;
    h += '<text x="' + p[0] + '" y="' + p[1] + '" text-anchor="middle" style="font-size:' + (big ? 26 : 17) / kk + 'px" class="zc' + (big ? " big" : "") + '">' + cnt[z] + "</text>";
    h += '<text x="' + p[0] + '" y="' + (p[1] + 13 / kk) + '" text-anchor="middle" style="font-size:' + 11 / kk + 'px" class="zl">' + names[z] + "</text>";
  });
  svg.setAttribute("viewBox", HALF_BOX.join(" ")); svg.innerHTML = h;
}

/* ---------- Flight: the run of the match in the Wurf head, goal difference, ours up ---------- */
function flight(svg) {
  var data = FLOW[svg.dataset.flow || "thalwil"], W = +svg.dataset.w, H = +svg.dataset.h, pad = W < 500 ? 16 : 32, U = (H - 34) / 10, base = H - 18, small = W < 500;
  function x(m) { return pad + (W - 2 * pad - 14) * m / 60; } function y(v) { return base - v * U; }
  function at(m) { var v = 0; data.forEach(function (p) { if (p[0] <= m) v = p[1]; }); return v; }
  var pts = []; data.forEach(function (p, i) { if (i) pts.push([x(p[0]), y(data[i - 1][1])]); pts.push([x(p[0]), y(p[1])]); });
  var o = '<line x1="' + pad + '" x2="' + (W - pad) + '" y1="' + base + '" y2="' + base + '" stroke="var(--club-ink)" stroke-opacity=".3" stroke-dasharray="2 5"/>';
  o += '<path d="' + d(pts) + '" fill="none" stroke="var(--club-ink)" stroke-width="' + (small ? 2 : 2.6) + '" stroke-linejoin="round" stroke-opacity=".9"/>';
  var end = at(60), e = [x(60), y(end)], half = at(30);
  o += '<circle cx="' + e[0] + '" cy="' + e[1] + '" r="' + (small ? 4 : 6) + '" fill="var(--club-ink)"/>';
  if (!small) o += '<text x="' + x(30) + '" y="' + (y(half) - 10) + '" text-anchor="middle" class="fw">Halbzeit ' + (half > 0 ? "+" : "") + half + '</text><text x="' + (e[0] + 4) + '" y="' + (e[1] + 24) + '" text-anchor="end" class="fw">Schluss ' + (end > 0 ? "+" : "") + end + "</text>";
  svg.setAttribute("viewBox", "0 0 " + W + " " + H); svg.innerHTML = o;
}

/* ---------- Rail: the timeline under the video. Goals from the report, ours up, theirs down, the marked phase ---------- */
function rail(svg) {
  var k = kitOf(svg), W = 1000, base = 36, R = RAIL;
  function x(m) { return (m / 60) * W; }
  var c = '<rect x="' + x(R.phase[0]) + '" y="0" width="' + (x(R.phase[1]) - x(R.phase[0])) + '" height="72" fill="#ffd23c"/>';
  c += '<line x1="0" x2="' + W + '" y1="' + base + '" y2="' + base + '" stroke="' + k.ink + '" stroke-width="1.5"/><line x1="' + x(30) + '" x2="' + x(30) + '" y1="2" y2="70" stroke="' + k.ink + '" stroke-dasharray="2 4"/>';
  R.us.forEach(function (m) { c += '<rect x="' + (x(m) - 2.5) + '" y="' + (base - 26) + '" width="5" height="24" fill="' + k.clubLine + '"' + (k.clubPipe ? ' stroke="' + k.clubPipe + '" stroke-width="1"' : "") + "/>"; });
  R.them.forEach(function (m) { c += '<rect x="' + (x(m) - 2.5) + '" y="' + (base + 2) + '" width="5" height="24" fill="' + k.oppLine + '"' + (k.oppPipe ? ' stroke="' + k.oppPipe + '" stroke-width="1"' : "") + "/>"; });
  c += '<line x1="' + x(R.at) + '" x2="' + x(R.at) + '" y1="-6" y2="78" stroke="' + k.ink + '" stroke-width="2.5"/><path d="M' + (x(R.at) - 7) + ' -10h14l-7 9z" fill="' + k.ink + '"/>';
  svg.setAttribute("viewBox", "-10 -12 1020 92"); svg.setAttribute("preserveAspectRatio", "none"); svg.innerHTML = c;
}

/* ---------- Series: one bar per match with video, the last one in the team's colour ---------- */
function series(svg) {
  var k = kitOf(svg), T = SEASON.themes[+svg.dataset.theme], W = 132, H = 64, n = T.series.length, bw = 30, gap = (W - n * bw) / (n - 1), max = Math.max.apply(null, T.series);
  var col = T.who === "us" ? k.clubLine : k.oppLine, pipe = T.who === "us" ? k.clubPipe : k.oppPipe, o = "";
  T.series.forEach(function (v, i) {
    var h = 40 * v / max, x = i * (bw + gap), last = i === n - 1;
    o += '<rect x="' + x + '" y="' + (H - 4 - h) + '" width="' + bw + '" height="' + h + '" fill="' + (last ? col : k.ink) + '" fill-opacity="' + (last ? 1 : 0.18) + '"' + (last && pipe ? ' stroke="' + pipe + '" stroke-width="1.5"' : "") + "/>";
    o += '<text x="' + (x + bw / 2) + '" y="' + (H - 10 - h) + '" text-anchor="middle" class="zc" style="font-size:17px">' + v + "</text>";
  });
  o += '<line x1="0" x2="' + W + '" y1="' + (H - 3) + '" y2="' + (H - 3) + '" stroke="' + k.ink + '" stroke-width="1.5"/>';
  svg.setAttribute("viewBox", "0 0 " + W + " " + H); svg.innerHTML = o;
}
/* goal difference per match, wins up in the club colour, losses down as an ink outline; the label says which */
function diffBars(svg) {
  var k = kitOf(svg), D = SEASON.diff, W = +svg.dataset.w || 700, H = 190, mid = 96, U = 7, bw = Math.min(64, W / D.length - 22), step = W / D.length, o = "";
  o += '<line x1="0" x2="' + W + '" y1="' + mid + '" y2="' + mid + '" stroke="' + k.ink + '" stroke-width="1.5"/>';
  D.forEach(function (m, i) {
    var v = m[2], x = i * step + (step - bw) / 2, h = Math.abs(v) * U, up = v > 0;
    o += '<rect x="' + x + '" y="' + (up ? mid - h : mid) + '" width="' + bw + '" height="' + h + '" fill="' + (up ? k.clubLine : "none") + '" stroke="' + (up ? k.clubPipe || k.clubLine : k.ink) + '" stroke-width="1.5"' + (up ? "" : ' stroke-dasharray="4 3"') + "/>";
    o += '<text x="' + (x + bw / 2) + '" y="' + (up ? mid - h - 8 : mid + h + 22) + '" text-anchor="middle" class="zc" style="font-size:20px">' + (up ? "+" : "") + v + "</text>";
    o += '<text x="' + (x + bw / 2) + '" y="' + (up ? mid + 20 : mid - 10) + '" text-anchor="middle" class="zl" style="font-size:13px">' + m[1] + "</text>";
  });
  svg.setAttribute("viewBox", "0 0 " + W + " " + H); svg.innerHTML = o;
}

/* ---------- Tactics camera: positions from the video, ways of the last two seconds, the scorer's whole way ----------
   The ball: no flight is drawn. Where the analysis found the ball in the picture it knows who holds
   it; only then a small ball sits at that player. data-cam = scene, data-view, data-w, data-r = dot radius in px */
function samplePath(pts, t) { var s = cr(pts, 10), n = s.length - 1, f = Math.max(0, Math.min(1, t)) * n, i = Math.floor(f), r = f - i; if (i >= n) return s[n]; return [s[i][0] + (s[i + 1][0] - s[i][0]) * r, s[i][1] + (s[i + 1][1] - s[i][1]) * r]; }
function trailOf(pts, t, back) { var o = []; for (var j = 0; j <= 14; j++) { var tt = t - back + back * j / 14; if (tt >= 0) o.push(samplePath(pts, tt)); } return o; }
function clock(S, t) { var s = S.from[1] + Math.min(S.dur, Math.floor(t * S.dur)), m = S.from[0] + Math.floor(s / 60); s = s % 60; return m + ":" + (s < 10 ? "0" : "") + s; }
function carrier(S, t) { var sec = t * S.dur, hit = null; S.ball.forEach(function (b) { if (sec >= b[0] && sec <= b[1]) hit = b; }); return hit; }
function camFrame(svg, t) {
  var S = CAM[svg.dataset.cam], V = VIEWS[svg.dataset.view], W = +svg.dataset.w, kk = W / V.box[2], r = (+svg.dataset.r || 12) / kk, k = kitOf(svg);
  var ring = !k.oppKnown || k.camClash, scorerUs = S.scorerTeam === "us";
  var h = viewWrap(V, courtLines({ floor: COURT, area: "rgb(255 255 255 / .06)", line: "rgb(226 236 244 / .5)", lw: 1.3 }));
  function trail(pts, col, whole) {
    var s = (whole ? trailOf(pts, t, t) : trailOf(pts, t, 0.33)).map(V.f), n = s.length - 1, o = "";
    for (var i = 0; i < n; i++) { var a = Math.pow((i + 1) / n, 1.4); o += '<path d="' + d([s[i], s[i + 1]]) + '" stroke="' + col + '" stroke-opacity="' + ((whole ? 0.5 : 0.12) + (whole ? 0.5 : 0.7) * a).toFixed(2) + '" stroke-width="' + ((whole ? 2.4 : 1.2) + (whole ? 1.6 : 2) * a).toFixed(2) + '" stroke-linecap="round" fill="none"' + (whole && S.est ? ' stroke-dasharray="5 4"' : "") + NS + "/>"; }
    return o;
  }
  S.them.forEach(function (p) { h += trail(p[1], "var(--opp-cam-trail)", !scorerUs && p[0] === S.scorer); });
  S.us.forEach(function (p) { h += trail(p[1], "var(--club-cam)", scorerUs && p[0] === S.scorer); });
  var done = t >= 1;
  if (done) {
    var a = V.f(S.shot), b = V.f(S.aim);
    h += '<path d="' + d([a, b]) + '" stroke="#fff" stroke-opacity=".75" stroke-width="1.4"' + NS + "/>";
    h += '<circle cx="' + a[0] + '" cy="' + a[1] + '" r="' + r * 1.9 + '" fill="none" stroke="#fff" stroke-width="1.6"' + (S.est ? ' stroke-dasharray="3 3"' : "") + NS + "/>";
  }
  var rf = V.f(samplePath(S.ref, t));
  h += '<rect x="' + (rf[0] - r * 0.5) + '" y="' + (rf[1] - r * 0.5) + '" width="' + r + '" height="' + r + '" fill="#8d97a1" transform="rotate(45 ' + rf[0] + " " + rf[1] + ')"/>';
  var hold = carrier(S, t), ballAt = null;
  function dot(p, us, n, read) {
    var e = V.f(samplePath(p, t)), o = "";
    if (us) o += '<circle cx="' + e[0] + '" cy="' + e[1] + '" r="' + r + '" fill="var(--club-cam)" stroke="' + INK_DARK + '" stroke-width="1.4"' + NS + "/>";
    else o += '<circle cx="' + e[0] + '" cy="' + e[1] + '" r="' + r * 0.92 + '" fill="var(--opp-cam)" stroke="var(--opp-cam-edge)" stroke-width="2.2"' + NS + "/>";
    if (read) o += '<text x="' + e[0] + '" y="' + (e[1] + r * 0.38) + '" text-anchor="middle" class="cn ' + (us ? "us" : "them") + '" style="font-size:' + (r * 1.04).toFixed(3) + 'px">' + n + "</text>";
    if (hold && hold[2] === (us ? "us" : "them") && hold[3] === n) ballAt = e;
    return o;
  }
  S.them.forEach(function (p) { h += dot(p[1], false, p[0], p[2]); });
  S.us.forEach(function (p) { h += dot(p[1], true, p[0], p[2]); });
  /* the ball, at the player who holds it: white with a seam, upper right of the dot */
  if (ballAt) { var bx = ballAt[0] + r * 0.95, by = ballAt[1] - r * 0.95, br = r * 0.6; h += '<g class="ball"><circle cx="' + bx + '" cy="' + by + '" r="' + br + '" fill="#fff" stroke="' + INK_DARK + '" stroke-width="1.3"' + NS + '/><path d="M' + (bx - br * 0.86) + " " + (by - br * 0.3) + "Q" + bx + " " + (by + br * 0.5) + " " + (bx + br * 0.86) + " " + (by - br * 0.3) + '" fill="none" stroke="' + INK_DARK + '" stroke-width="1"' + NS + "/></g>"; }
  if (done && svg.hasAttribute("data-labels")) { var q = V.f(S.shot); h += '<g class="ctag"><rect x="' + (q[0] + r * 2.4) + '" y="' + (q[1] - 11 / kk) + '" width="' + 140 / kk + '" height="' + 22 / kk + '" fill="' + INK_DARK + '"/><text x="' + (q[0] + r * 2.4 + 8 / kk) + '" y="' + (q[1] + 4.5 / kk) + '" style="font-size:' + 13 / kk + 'px">' + S.label + "</text></g>"; }
  svg.setAttribute("viewBox", V.box.join(" ")); svg.innerHTML = h;
  var box = svg.closest(".stage"); if (box) { var clk = box.querySelector(".clk"); if (clk) clk.textContent = clock(S, t); var bl = box.parentElement.querySelector(".balls"); if (bl) bl.style.setProperty("--t", t); }
}
/* the ball line under the stage: who held the ball, only where it was found; gaps say so */
function ballLine(el) {
  var S = CAM[el.dataset.cam], h = "", at = 0;
  if (!S.ball.length) { el.innerHTML = '<span class="gap" style="flex:1">Ball in dieser Szene nicht erkannt</span>'; return; }
  S.ball.forEach(function (b) {
    if (b[0] > at) h += '<span class="gap" style="flex:' + (b[0] - at) + '">' + (b[0] - at >= 1.5 ? "nicht erkannt" : "") + "</span>";
    h += '<span class="seg ' + b[2] + '" style="flex:' + (b[1] - b[0]) + '">' + b[3] + "</span>"; at = b[1];
  });
  if (at < S.dur) h += '<span class="gap" style="flex:' + (S.dur - at) + '">' + (S.dur - at >= 1.5 ? "nicht erkannt" : "") + "</span>";
  el.innerHTML = h + '<i class="head" aria-hidden="true"></i>';
}
/* the player: plays each camera once (6 s), holds, plays again. Pause key; reduced motion shows the last frame */
var CAMS = [];
function camInit(root) {
  root.querySelectorAll("svg[data-cam]").forEach(function (svg) {
    var st = { svg: svg, t0: null, paused: false, t: 1 }, btn = svg.closest(".stage").querySelector(".pause");
    var still = /still/.test(location.search) || window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (still) { st.paused = true; if (btn) { btn.textContent = "Abspielen"; btn.setAttribute("aria-pressed", "true"); } }
    if (btn) btn.onclick = function () { st.paused = !st.paused; btn.textContent = st.paused ? "Abspielen" : "Pause"; btn.setAttribute("aria-pressed", String(st.paused)); if (!st.paused) st.t0 = null; };
    camFrame(svg, 1); CAMS.push(st);
  });
}
function camLoop(ts) {
  CAMS.forEach(function (st) {
    if (st.paused || !st.svg.isConnected) return;
    if (st.t0 == null) st.t0 = ts - (st.t >= 1 ? 0 : st.t * 6000);
    var e = ((ts - st.t0) / 1000) % 7.6; st.t = Math.min(1, e / 6);
    camFrame(st.svg, st.t);
  });
  requestAnimationFrame(camLoop);
}
requestAnimationFrame(camLoop);

/* ---------- Hall: the video picture (stand-in for the real frame) ----------
   data-hall = scene; data-mode: "video" (players), "check" (detected field and four corner handles,
   no players: before the field is confirmed there are no positions), "who" (crop around one player
   for Prüfen, boxed in yellow; data-who = "them:14") */
function hall(svg) {
  var S = CAM[svg.dataset.hall || "ra"], mode = svg.dataset.mode || "video", C = [13, -15, 10.5], T = [12, 9, 0];
  function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
  function norm(a) { var l = Math.hypot(a[0], a[1], a[2]); return [a[0] / l, a[1] / l, a[2] / l]; }
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
  var f = norm(sub(T, C)), rr = norm([f[1], -f[0], 0]), u = [rr[1] * f[2] - rr[2] * f[1], rr[2] * f[0] - rr[0] * f[2], rr[0] * f[1] - rr[1] * f[0]]; if (u[2] < 0) u = u.map(function (v) { return -v; });
  function P(x, y, z) { var v = sub([x, y, z || 0], C), dz = dot(v, f); return [500 + 760 * dot(v, rr) / dz, 562 * 0.42 - 760 * dot(v, u) / dz]; }
  function poly(pts, close) { return pts.map(function (p, i) { var q = P(p[0], p[1], p[2]); return (i ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1); }).join("") + (close ? "Z" : ""); }
  function arcPts(cx, cy, r, a0, a1) { var o = []; for (var i = 0; i <= 24; i++) { var a = a0 + (a1 - a0) * i / 24; o.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]); } return o; }
  function area(r) { return arcPts(0, 8.5, r, -Math.PI / 2, 0).filter(function (p) { return p[1] >= 0; }).concat(arcPts(0, 11.5, r, 0, Math.PI / 2).filter(function (p) { return p[1] <= 20; })); }
  var h = '<rect x="-200" y="-200" width="1400" height="962" fill="#3a3d40"/>';
  h += '<path d="' + poly([[-6, 23, 0], [46, 23, 0], [46, 23, 4], [-6, 23, 4]], 1) + '" fill="#2f3235"/>';
  h += '<path d="' + poly([[-4, -4], [44, -4], [44, 22.4], [-4, 22.4]], 1) + '" fill="#8a6f55"/><path d="' + poly([[0, 0], [40, 0], [40, 20], [0, 20]], 1) + '" fill="#a8865f"/>';
  h += '<path d="' + poly(area(6).concat([[0, 17.5], [0, 2.5]]), 1) + '" fill="#2f6e93"/>';
  h += '<g fill="none" stroke="#f4f1ea" stroke-opacity=".9" stroke-width="1.6"><path d="' + poly([[0, 0], [40, 0], [40, 20], [0, 20]], 1) + '"/><path d="' + poly([[20, 0], [20, 20]]) + '"/><path d="' + poly(area(6)) + '"/><path d="' + poly(area(9)) + '" stroke-dasharray="7 6"/></g>';
  h += '<path d="' + poly([[0, 8.5, 0], [0, 8.5, 2], [0, 11.5, 2], [0, 11.5, 0]]) + '" fill="none" stroke="#f3f3f0" stroke-width="3"/>';
  var box = null;
  if (mode !== "check") {
    var pl = [], t = mode === "who" ? 0.55 : 0.8;
    S.us.forEach(function (p) { pl.push([samplePath(p[1], t), "var(--club)", "us:" + p[0]]); });
    S.them.forEach(function (p) { pl.push([samplePath(p[1], t), "var(--opp)", "them:" + p[0]]); });
    pl.sort(function (a, b) { return b[0][1] - a[0][1]; });
    pl.forEach(function (q) {
      var x = q[0][0], y = q[0][1], ft = P(x, y, 0), hd = P(x, y, 1.6), w = Math.abs(P(x + 0.5, y, 0)[0] - ft[0]), kn = P(x, y, 0.85), sh = P(x, y, 1.5);
      h += '<ellipse cx="' + ft[0] + '" cy="' + ft[1] + '" rx="' + w * 0.9 + '" ry="' + w * 0.3 + '" fill="#000" opacity=".28"/>';
      h += '<path d="M' + (ft[0] - w * 0.18) + " " + ft[1] + "L" + (kn[0] - w * 0.12) + " " + kn[1] + "M" + (ft[0] + w * 0.18) + " " + ft[1] + "L" + (kn[0] + w * 0.12) + " " + kn[1] + '" stroke="#2a2c30" stroke-width="' + w * 0.26 + '" stroke-linecap="round"/>';
      h += '<path d="M' + kn[0] + " " + kn[1] + "L" + sh[0] + " " + sh[1] + '" stroke="' + q[1] + '" stroke-width="' + w * 0.62 + '" stroke-linecap="round"/>';
      h += '<circle cx="' + hd[0] + '" cy="' + (hd[1] - w * 0.1) + '" r="' + w * 0.2 + '" fill="#b88b6c"/>';
      if (q[2] === svg.dataset.who) box = [ft[0] - w * 1.3, hd[1] - w * 0.8, w * 2.6, ft[1] - hd[1] + w * 1.4];
    });
  }
  if (mode === "check") {
    var cs = [[0, 0], [20, 0], [20, 20], [0, 20]].map(function (p) { return P(p[0], p[1]); });
    h += '<path d="M' + cs.map(function (p) { return p[0].toFixed(1) + " " + p[1].toFixed(1); }).join("L") + 'Z" fill="#ffd23c" fill-opacity=".1" stroke="#ffd23c" stroke-width="3.5" stroke-dasharray="12 7"/>';
    cs.forEach(function (p) { h += '<rect x="' + (p[0] - 13) + '" y="' + (p[1] - 13) + '" width="26" height="26" fill="#ffd23c" stroke="#15171a" stroke-width="3"/>'; });
    svg.setAttribute("viewBox", "-56 -31 1112 625"); /* a slightly wider lens, all four corners inside */
  } else if (mode === "who" && box) {
    h += '<rect x="' + box[0] + '" y="' + box[1] + '" width="' + box[2] + '" height="' + box[3] + '" fill="none" stroke="#ffd23c" stroke-width="3"/>';
    var cx = box[0] + box[2] / 2, cy = box[1] + box[3] / 2, cw = box[3] * 3.2, ch = cw * 0.5625;
    svg.setAttribute("viewBox", (cx - cw / 2).toFixed(1) + " " + (cy - ch / 2).toFixed(1) + " " + cw.toFixed(1) + " " + ch.toFixed(1));
  } else svg.setAttribute("viewBox", "0 0 1000 562");
  svg.innerHTML = h;
}

/* fill every graphic inside one screen */
function drawGraphics(root) {
  root.querySelectorAll("svg[data-b]").forEach(bundle);
  root.querySelectorAll("svg[data-empty]").forEach(emptyField);
  root.querySelectorAll("svg[data-zones]").forEach(zones);
  root.querySelectorAll("svg[data-fl]").forEach(flight);
  root.querySelectorAll("svg[data-rail]").forEach(rail);
  root.querySelectorAll("svg[data-series]").forEach(series);
  root.querySelectorAll("svg[data-diff]").forEach(diffBars);
  root.querySelectorAll("svg[data-hall]").forEach(hall);
  root.querySelectorAll("[data-balls]").forEach(ballLine);
}
