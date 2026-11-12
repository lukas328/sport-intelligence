/* ===== Anlauf: demo data =====
   Stand-in for what the analysis and the match report deliver. Shapes, not values, are the
   contract: every array here names the API field it stands for (see ANLAUF.md, section 10).
   Nothing in here is drawn that the analysis does not measure: no ball flight, no passes. */

function rng(seed) { var s = seed >>> 0 || 1; return function () { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; }; }

/* ---------- goals: zone, estimated shot spot, the scorer's run before it ----------
   API: goals[] = { team, minute, scorer_track, run: [[u, v], ...] (metres, 8 to 10 per second,
   the last 2 to 4 seconds before the shot), shot: [u, v] (estimated: point nearest the goal in the
   10 s before the goal), confirmed: bool }. Half-court coordinates with the goal at the top:
   u across (0 to 20 m), v away from the goal line. */
var ZN = {
  la: { u: [0.7, 2.8], v: [0.8, 3.0] }, ra: { u: [17.2, 19.3], v: [0.8, 3.0] },
  rl: { u: [3.8, 7.6], v: [8.6, 11.2] }, rm: { u: [8.4, 11.6], v: [8.8, 11.8] }, rr: { u: [12.4, 16.2], v: [8.6, 11.2] },
  kr: { u: [8.0, 12.0], v: [6.0, 7.0] }, m7: { u: [10, 10], v: [7, 7] }, gs: { u: [6.5, 13.5], v: [4.5, 7.5] }
};
function goals(seed, spec, estN, phase) {
  var R = rng(seed), out = [];
  Object.keys(spec).forEach(function (z) {
    for (var i = 0; i < spec[z]; i++) {
      var Z = ZN[z], u = Z.u[0] + R() * (Z.u[1] - Z.u[0]), v = Z.v[0] + R() * (Z.v[1] - Z.v[0]), pts;
      if (z === "la" || z === "ra") { var side = z === "la" ? -1 : 1; pts = [[u + side * (0.2 + R() * 0.6), v + 6 + R() * 4], [u + side * (0.6 + R()), v + 3 + R() * 1.5], [u - side * R() * 0.6, v + 1.2], [u, v]]; }
      else if (z === "gs") { var u0 = 3 + R() * 14; pts = [[u0, 19.6], [u0 + (u - u0) * 0.35 + (R() - 0.5) * 2, 14 + R() * 2], [u + (R() - 0.5) * 1.5, v + 3.5], [u, v]]; }
      else if (z === "kr") { var s = R() < 0.5 ? -1 : 1; pts = [[u + s * (2.5 + R() * 2), v + 0.4 + R() * 0.6], [u + s * (1.2 + R()), v + 0.2 + R() * 0.5], [u + s * 0.4, v + 0.1], [u, v]]; }
      else if (z === "m7") { pts = [[u, v + 2.2], [u, v + 1.1], [u, v]]; }
      else { var dx = (R() - 0.5) * 7; pts = [[u + dx, v + 4.5 + R() * 3], [u + dx * 0.55, v + 2.6 + R()], [u + dx * 0.15, v + 0.9], [u, v]]; }
      pts = pts.map(function (p) { return [Math.max(0.3, Math.min(19.7, p[0])), Math.max(0.3, Math.min(19.8, p[1]))]; });
      out.push({ zone: z, run: pts, shot: [u, v], aim: [8.8 + R() * 2.4, 0], est: false, t: phase && i < 3 ? 38 + R() * 6 : R() * 60 });
    }
  });
  for (var e = 0; e < estN; e++) out[Math.floor(R() * out.length)].est = true;
  return out;
}
var GOALS = {
  them: goals(31, { ra: 9, rl: 3, rm: 2, la: 2, rr: 1, kr: 1 }, 3),
  us: goals(47, { kr: 7, la: 3, ra: 3, rl: 3, rm: 3, rr: 3, m7: 2, gs: 2 }, 3),
  themGs: goals(53, { gs: 6 }, 2, true),
  staefa: goals(61, { gs: 4, rl: 3 }, 1), rheinau: goals(71, { rl: 5, kr: 3 }, 1),
  season: goals(83, { ra: 10 }, 2) /* rechts aussen in the two matches before Thalwil */
};
/* which goals a bundle shows, and in whose colour. key = the thing it belongs to */
var BUNDLES = {
  ra: { team: "them", pick: function () { return GOALS.them.filter(function (g) { return g.zone === "ra"; }); }, rest: function () { return GOALS.them.filter(function (g) { return g.zone !== "ra"; }); } },
  gs: { team: "them", pick: function () { return GOALS.themGs; }, rest: function () { return GOALS.them; } },
  kr: { team: "us", pick: function () { return GOALS.us.filter(function (g) { return g.zone === "kr"; }); }, rest: function () { return GOALS.us.filter(function (g) { return g.zone !== "kr"; }); } },
  staefa: { team: "them", opp: "staefa", pick: function () { return GOALS.staefa.filter(function (g) { return g.zone === "gs"; }); }, rest: function () { return GOALS.staefa.filter(function (g) { return g.zone !== "gs"; }); } },
  rheinau: { team: "them", opp: "rheinau", pick: function () { return GOALS.rheinau.filter(function (g) { return g.zone === "rl"; }); }, rest: function () { return GOALS.rheinau.filter(function (g) { return g.zone !== "rl"; }); } },
  saison: { team: "them", pick: function () { return GOALS.them.filter(function (g) { return g.zone === "ra"; }).concat(GOALS.season); }, rest: function () { return []; } }
};

/* ---------- goal difference minute by minute, from the goal sequence of the match report ----------
   API: report.goals[] = { minute, team } ; the line is the running difference. */
var FLOW = {
  thalwil: [[0, 0], [2, 1], [3, 0], [5, 1], [7, 0], [9, 1], [11, 2], [12, 1], [14, 2], [16, 1], [17, 2], [19, 3], [20, 2], [22, 3], [23, 2], [24, 3], [25, 2], [26, 3], [27, 4], [28, 3], [29, 4], [30, 4], [32, 5], [35, 6], [36, 7], [38.6, 6], [39.9, 5], [41, 4], [42, 3], [43.8, 2], [46, 3], [48, 4], [49, 3], [50, 4], [51, 5], [53, 6], [54, 7], [55, 6], [56, 7], [57, 8], [58, 9], [58.5, 8], [60, 8]],
  horgen: [[0, 0], [6, 1], [12, 3], [18, 4], [24, 4], [30, 6], [36, 7], [42, 8], [48, 9], [54, 10], [60, 10]]
};
/* goals of the Thalwil match for the timeline under the video (minutes) */
var RAIL = {
  us: [2, 5, 9, 11, 14, 17, 19, 22, 24, 26, 27, 29, 29.5, 32, 35, 36, 46, 48, 50, 51, 53, 54, 56, 57, 58, 59.5],
  them: [3, 7, 12, 16, 20, 23, 25, 28, 30, 39, 40, 41, 42, 43, 44, 49, 55, 58.5],
  phase: [38, 44], at: 39.9
};

/* ---------- scenes for the tactics camera ----------
   API: scene.tracks[] = { team: own | opp | keeper | ref, number (only where read), xy: [[x, y], ...]
   in court metres (40 x 20, goals at x = 0 and 40), 8 to 10 per second }.
   ball[] = the player who holds the ball, only for the stretches where the ball was found in the
   picture: [from s, to s, team, number]. Between them nothing is drawn. */
var CAM = {
  ra: {
    from: [39, 49], dur: 6,
    us: [[1, [[1.0, 11.2], [0.9, 10.4], [0.8, 9.6], [0.7, 9.1]], 1], [7, [[5.4, 2.0], [5.8, 2.4], [6.6, 3.2], [7.6, 4.2], [8.4, 5.0]], 1], [13, [[6.6, 7.4], [6.9, 7.1], [7.4, 7.0], [7.9, 7.3]], 0], [4, [[7.0, 10.8], [7.2, 10.2], [7.5, 9.8], [7.6, 9.6]], 0], [10, [[6.8, 12.6], [7.0, 11.8], [7.3, 11.1], [7.4, 10.8]], 0], [11, [[6.8, 15.0], [7.0, 14.2], [7.2, 13.5], [7.3, 13.1]], 0], [8, [[5.8, 17.8], [5.9, 17.2], [6.2, 16.6], [6.4, 16.2]], 0]],
    them: [[5, [[1.4, 0.5], [0.8, 0.8], [1.1, 1.2], [2.0, 1.6], [3.0, 2.2], [3.9, 2.9]], 1], [9, [[15.6, 9.0], [14.6, 7.8], [13.2, 6.5], [11.8, 5.6], [10.5, 5.0]], 1], [14, [[14.8, 12.8], [14.0, 11.6], [13.0, 10.6], [12.1, 10.0]], 0], [22, [[13.2, 17.4], [12.6, 16.4], [11.6, 15.3], [10.9, 14.6]], 1], [3, [[0.8, 19.5], [1.0, 19.2], [1.3, 18.9], [1.6, 18.6]], 0], [18, [[6.2, 12.6], [6.3, 11.4], [6.6, 9.8], [6.7, 8.4], [6.6, 7.4]], 0]],
    ref: [[12.0, 1.6], [10.8, 1.4], [9.6, 1.5]],
    ball: [[0, 1.3, "them", 14], [1.5, 2.6, "them", 9], [4.6, 6, "them", 5]],
    scorer: 5, shot: [3.9, 2.9], aim: [0.15, 8.9], est: false, label: "Tor Thalwil 39:55"
  },
  /* our goal from the circle, 18:02: here the ball was not found in the picture */
  kr: {
    from: [17, 56], dur: 6,
    us: [[8, [[7.4, 12.6], [7.0, 12.0], [6.6, 11.2], [6.2, 10.4], [5.9, 9.9]], 0], [10, [[10.8, 13.4], [10.4, 12.4], [10.2, 11.6], [10.1, 11.2]], 1], [4, [[11.2, 6.4], [10.6, 6.8], [10.0, 7.4], [9.6, 7.8]], 0], [11, [[10.6, 16.6], [10.2, 16.0], [9.8, 15.4], [9.6, 15.0]], 0], [3, [[2.4, 1.0], [2.6, 1.4], [2.8, 1.8], [3.0, 2.0]], 1], [7, [[2.6, 19.0], [2.8, 18.6], [3.0, 18.2], [3.1, 18.0]], 0]],
    them: [[1, [[0.9, 10.6], [1.0, 10.4], [1.1, 10.2], [1.2, 10.1]], 1], [6, [[4.0, 3.0], [4.1, 3.4], [4.2, 3.7], [4.2, 3.9]], 0], [12, [[6.2, 6.6], [6.4, 7.2], [6.4, 7.6], [6.3, 7.9]], 0], [15, [[6.7, 9.0], [6.6, 9.6], [6.4, 10.0], [6.3, 10.2]], 0], [17, [[6.6, 11.8], [6.6, 11.6], [6.5, 11.6], [6.5, 11.7]], 1], [19, [[6.3, 13.8], [6.3, 13.6], [6.3, 13.5], [6.3, 13.4]], 0], [21, [[4.4, 16.4], [4.4, 16.3], [4.4, 16.2], [4.4, 16.1]], 0]],
    ref: [[13.0, 18.6], [12.0, 18.8], [11.2, 18.8]],
    ball: [],
    scorer: 8, scorerTeam: "us", shot: [5.9, 9.9], aim: [0.15, 9.4], est: true, label: "Tor Zürichsee 18:02"
  }
};

/* ---------- the season ---------- */
var SEASON = {
  diff: [["3.10.", "Rüti", 5], ["10.10.", "Wädenswil", -3], ["17.10.", "Horgen", 10], ["24.10.", "Meilen", 1], ["31.10.", "Stäfa", -7], ["7.11.", "Thalwil", 8]],
  /* matches with a finished analysis: Rüti, Stäfa, Thalwil */
  themes: [
    { t: "Gegentore über rechts aussen", s: "In jedem Spiel mit Video die häufigste Seite.", n: "19 Szenen", series: [5, 5, 9], of: [22, 26, 18], who: "them" },
    { t: "Ballverluste", s: "Stäfa war der Ausreisser, sonst um 10.", n: "36 Szenen", series: [10, 15, 11], of: null, who: "us" },
    { t: "Tore vom Kreis", s: "Von 3 auf 7 in drei Spielen.", n: "14 Szenen", series: [3, 4, 7], of: [27, 19, 26], who: "us" }
  ]
};
