/* ===== Anlauf: colour model =====
   Two teams, two colours, everything else ink on cloth. This file turns a club colour and an
   opponent colour into the CSS variables the screens use. Port it to lib/color.ts.

   Inputs:  club  = [first colour, second colour]   (from the club settings)
            opp   = [first colour, second colour] or null when the opponent's colour is unknown
   Output:  an object with every derived value, and dress(el, k) sets them as CSS variables. */

var INK = "#15171a", INK_DARK = "#0a0d11", GREY_UNKNOWN = "#646b73", COURT = "#0f2333";

function hex2rgb(h) { h = h.replace("#", ""); return [0, 2, 4].map(function (i) { return parseInt(h.substr(i, 2), 16); }); }
function rgb2hex(c) { return "#" + c.map(function (v) { v = Math.max(0, Math.min(255, Math.round(v))); return (v < 16 ? "0" : "") + v.toString(16); }).join(""); }
function lum(h) { return hex2rgb(h).map(function (v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }).reduce(function (a, v, i) { return a + v * [0.2126, 0.7152, 0.0722][i]; }, 0); }
function contrast(a, b) { var x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); }
function mix(a, b, t) { var p = hex2rgb(a), q = hex2rgb(b); return rgb2hex(p.map(function (v, i) { return v + (q[i] - v) * t; })); }
/* shift a colour towards `to` until it reaches the contrast it needs on a ground */
function reach(c, ground, need, to) { for (var t = 0; t <= 1.0001; t += 0.02) { var m = mix(c, to, t); if (contrast(m, ground) >= need) return m; } return to; }
/* hue in degrees, -1 for greys, black and white */
function hue(h) { var c = hex2rgb(h).map(function (v) { return v / 255; }), mx = Math.max.apply(null, c), mn = Math.min.apply(null, c), dd = mx - mn; if (dd < 0.15) return -1; var x = mx === c[0] ? ((c[1] - c[2]) / dd) % 6 : mx === c[1] ? (c[2] - c[0]) / dd + 2 : (c[0] - c[1]) / dd + 4; return (x * 60 + 360) % 360; }
/* two colours a spectator would mix up: hues closer than 45 degrees, or two greys of similar lightness */
function near(a, b) { var ha = hue(a), hb = hue(b); if (ha < 0 || hb < 0) return ha < 0 && hb < 0 && Math.abs(lum(a) - lum(b)) < 0.25; return Math.min(Math.abs(ha - hb), 360 - Math.abs(ha - hb)) < 45; }
function inkOn(c) { return contrast(c, "#ffffff") >= contrast(c, INK) ? "#ffffff" : INK; }

/* the six club colours of the demo, and the opponents of the demo season */
var KITS = {
  blau: ["#1f4fd6", "#ffffff"], rot: ["#d3202e", "#ffffff"], gelb: ["#f6c500", "#17191c"],
  schwarz: ["#17191c", "#ffffff"], weiss: ["#ffffff", "#17191c"], gruen: ["#12804a", "#ffffff"],
  orange: ["#e2731c", "#ffffff"], violett: ["#5b2d8e", "#ffffff"],
  thalwil: ["#17191c", "#ffffff"], staefa: ["#5b2d8e", "#ffffff"], meilen: ["#e2731c", "#ffffff"],
  horgen: ["#0b7a8a", "#ffffff"], waedenswil: ["#1d3a8a", "#ffffff"], rheinau: ["#6b2fa3", "#ffffff"]
};

/* everything colour-related for one club against one opponent on the cloth ground */
function kit(club, opp, ground) {
  ground = ground || "#eceae5";
  var c = club, k = { ground: ground, ink: INK };
  k.club = c[0]; k.club2 = c[1];
  /* text on the club colour: white or ink, whichever is stronger (both reach 4.5:1 for all six) */
  k.clubInk = inkOn(c[0]);
  /* a club colour that vanishes on the ground gets an ink edge (white) */
  k.clubEdge = contrast(c[0], ground) < 1.3 ? INK : c[0];
  /* lines on the ground: the colour itself, with a piping in the second colour or ink when it is too light */
  var low = contrast(c[0], ground) < 2.4;
  k.clubLine = c[0]; k.clubPipe = low ? (contrast(c[1], ground) >= 3 ? c[1] : INK) : "";
  /* the club colour as text (numerals, names): shifted to 4.5:1 on the ground; greys fall back to ink */
  k.clubText = contrast(c[0], ground) >= 4.5 ? c[0] : hue(c[0]) < 0 ? INK : reach(c[0], ground, 4.5, "#000000");
  if (!opp) {
    /* unknown: grey, and the screens ask. Never guess. */
    k.oppKnown = false; k.opp = GREY_UNKNOWN; k.opp2 = "#ffffff";
    if (lum(c[0]) < 0.05) k.opp = "#8b9198"; /* a black club would swallow the grey */
  } else {
    k.oppKnown = true;
    /* clash rule, as with real away kits: too close to the club, the opponent plays its second colour, else ink */
    var oc = near(opp[0], c[0]) ? (near(opp[1], c[0]) ? INK : opp[1]) : opp[0];
    k.opp = oc; k.opp2 = oc === opp[0] ? opp[1] : opp[0];
  }
  k.oppInk = inkOn(k.opp);
  k.oppLine = k.opp; k.oppPipe = contrast(k.opp, ground) < 2.4 ? INK : "";
  k.oppEdge = contrast(k.opp, ground) < 1.3 ? INK : k.opp;

  /* on the tactics camera (dark court): a colour that vanishes plays in its second colour */
  var cc = contrast(c[0], COURT) >= 2.2 ? c[0] : c[1], ocam = contrast(k.opp, COURT) >= 2.2 ? k.opp : k.opp2;
  /* two teams must never look alike on the court: the opponent steps back to grey rings */
  k.camClash = k.oppKnown && (contrast(cc, ocam) < 1.6 || near(cc, ocam));
  k.clubCam = cc; k.clubCamInk = contrast(cc, "#ffffff") >= 3 ? "#ffffff" : INK_DARK;
  var ring = !k.oppKnown || k.camClash;
  k.oppCam = ring ? COURT : ocam;
  k.oppCamInk = ring ? "#ffffff" : lum(ocam) > 0.4 ? INK_DARK : "#ffffff";
  k.oppCamEdge = ring ? "#a3aeb8" : lum(ocam) > 0.5 ? "#e9eef2" : reach(ocam, COURT, 3, "#ffffff");
  k.oppCamTrail = ring ? "#a3aeb8" : reach(ocam, COURT, 3, "#ffffff");
  return k;
}

function dress(el, k) {
  var s = el.style;
  [["--club", k.club], ["--club-2", k.club2], ["--club-ink", k.clubInk], ["--club-edge", k.clubEdge], ["--club-text", k.clubText],
   ["--club-line", k.clubLine], ["--club-pipe", k.clubPipe || "transparent"],
   ["--opp", k.opp], ["--opp-ink", k.oppInk], ["--opp-edge", k.oppEdge], ["--opp-line", k.oppLine], ["--opp-pipe", k.oppPipe || "transparent"],
   ["--club-cam", k.clubCam], ["--club-cam-ink", k.clubCamInk],
   ["--opp-cam", k.oppCam], ["--opp-cam-ink", k.oppCamInk], ["--opp-cam-edge", k.oppCamEdge], ["--opp-cam-trail", k.oppCamTrail]
  ].forEach(function (p) { s.setProperty(p[0], p[1]); });
  el._kit = k;
}
