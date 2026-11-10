/* Runde 4: shared code for both directions.
   - frames: one template shown at desktop (1280) and phone (390) width, scaled to fit
   - club colours: six kits, contrast-derived variables, clash rule for opponents
   - match data: goal minutes for both teams (the demo match 26:18)
   Each direction draws its own pictures from window.R4. */
(function () {
  "use strict";

  /* ---------- colour ---------- */
  function rgb(h) { h = h.replace("#", ""); return [0, 2, 4].map(function (i) { return parseInt(h.substr(i, 2), 16); }); }
  function lum(h) { return rgb(h).map(function (c) { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }).reduce(function (a, c, i) { return a + c * [0.2126, 0.7152, 0.0722][i]; }, 0); }
  function contrast(a, b) { var x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); }
  function hsl(h) {
    var c = rgb(h).map(function (v) { return v / 255; }), mx = Math.max.apply(null, c), mn = Math.min.apply(null, c), l = (mx + mn) / 2, d = mx - mn, s = 0, hue = 0;
    if (d) { s = d / (1 - Math.abs(2 * l - 1)); hue = mx === c[0] ? ((c[1] - c[2]) / d) % 6 : mx === c[1] ? (c[2] - c[0]) / d + 2 : (c[0] - c[1]) / d + 4; hue *= 60; if (hue < 0) hue += 360; }
    return [hue, s, l];
  }
  function mix(a, b, t) { var x = rgb(a), y = rgb(b); return "#" + x.map(function (v, i) { return Math.round(v + (y[i] - v) * t).toString(16).padStart(2, "0"); }).join(""); }
  var INK = "#111214", WHITE = "#ffffff";
  /* two kit colours clash when both are grey-ish and close in lightness, or close in hue and lightness */
  function clash(a, b) {
    var x = hsl(a), y = hsl(b), grey = x[1] < 0.18 || x[2] > 0.92 || x[2] < 0.1, grey2 = y[1] < 0.18 || y[2] > 0.92 || y[2] < 0.1;
    if (grey || grey2) return grey && grey2 && Math.abs(x[2] - y[2]) < 0.3;
    var dh = Math.abs(x[0] - y[0]); dh = Math.min(dh, 360 - dh);
    return dh < 40 && Math.abs(x[2] - y[2]) < 0.2;
  }
  /* text on a fill, a line colour that holds 3:1 on white, a text colour that holds 4.5:1 on white */
  function on(c) { return contrast(c, WHITE) >= 3 ? WHITE : INK; }
  function line(a, b) { return contrast(a, WHITE) >= 3 ? a : contrast(b, WHITE) >= 3 ? b : INK; }
  function text(a, b) { if (contrast(a, WHITE) >= 4.5) return a; if (contrast(a, WHITE) >= 3) { var t = a; for (var k = 0; k < 10 && contrast(t, WHITE) < 4.5; k++) t = mix(t, INK, 0.12); return t; } return contrast(b, WHITE) >= 4.5 ? b : INK; }
  function edge(c) { return contrast(c, WHITE) < 1.25 ? "rgb(17 18 20 / 0.55)" : "transparent"; }

  var CLUBS = {
    rot: { name: "Rot", a: "#d3202e", b: "#ffffff" },
    blau: { name: "Blau", a: "#1f4fbf", b: "#ffffff" },
    gelb: { name: "Gelb", a: "#f6c500", b: "#15171a" },
    schwarz: { name: "Schwarz", a: "#15171a", b: "#ffffff" },
    weiss: { name: "Weiss", a: "#ffffff", b: "#15171a" },
    gruen: { name: "Grün", a: "#0f7a46", b: "#ffffff" }
  };
  var OPP = { a: "#0e7c8a", b: "#ffffff" }; /* TSV Thalwil: petrol, second kit white */
  function pick(home, o) { if (!clash(home, o.a)) return o.a; if (!clash(home, o.b)) return o.b; return "#646b73"; }

  function setClub(key) {
    var k = CLUBS[key] || CLUBS.rot, r = document.documentElement.style, opp = pick(k.a, OPP), opp2 = opp === OPP.a ? OPP.b : OPP.a;
    var v = {
      "--home": k.a, "--home-2": k.b, "--home-ink": on(k.a), "--home-line": line(k.a, k.b), "--home-text": text(k.a, k.b), "--home-edge": edge(k.a), "--home-pipe": contrast(k.a, WHITE) < 3 ? (contrast(k.b, WHITE) >= 3 ? k.b : INK) : "transparent",
      "--opp": opp, "--opp-ink": on(opp), "--opp-line": line(opp, opp2), "--opp-text": text(opp, INK), "--opp-edge": edge(opp), "--opp-pipe": contrast(opp, WHITE) < 3 ? (contrast(opp2, WHITE) >= 3 ? opp2 : INK) : "transparent"
    };
    Object.keys(v).forEach(function (n) { r.setProperty(n, v[n]); });
    document.documentElement.dataset.club = key;
    /* other opponents in lists: data-o and data-o2 on the row */
    document.querySelectorAll("[data-o]").forEach(function (el) {
      var c = pick(k.a, { a: el.dataset.o, b: el.dataset.o2 || "#ffffff" });
      el.style.setProperty("--o", c); el.style.setProperty("--o-edge", edge(c)); el.style.setProperty("--o-line", line(c, el.dataset.o2 || INK)); el.style.setProperty("--o-ink", on(c));
    });
    document.querySelectorAll("[data-club-pick]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.clubPick === key)); });
    document.dispatchEvent(new CustomEvent("club"));
  }

  /* ---------- match data: goal minutes ---------- */
  var US = [2, 5, 9, 11, 14, 17, 19, 22, 24, 26, 27, 29, 29.5, 32, 35, 36, 46, 48, 50, 51, 53, 54, 56, 57, 58, 59.5];
  var THEM = [3, 7, 12, 16, 20, 23, 25, 28, 30, 39, 40, 41, 42, 43, 44, 49, 55, 58.5];
  /* goals that belong to the three things: 9 of Thalwil's over the right wing, 7 own from the pivot */
  var RA = [3, 12, 20, 25, 30, 39.9, 43, 49, 55];
  var KM = [9, 17, 24, 29, 46, 51, 57];
  function flow() {
    var ev = US.map(function (m) { return [m, 1]; }).concat(THEM.map(function (m) { return [m, -1]; })).sort(function (a, b) { return a[0] - b[0]; });
    var d = 0, pts = [[0, 0]];
    ev.forEach(function (e) { d += e[1]; pts.push([e[0], d]); });
    pts.push([60, d]);
    return pts;
  }

  /* ---------- frames ---------- */
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

  var ICONS = {
    suche: '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    play: '<path d="M8 5.5v13l10.5-6.5z" fill="currentColor" stroke="none"/>',
    spiele: '<rect x="3" y="6" width="18" height="12"/><path d="M12 6v12"/>',
    szenen: '<rect x="3" y="5" width="18" height="14"/><path d="M10 9.2v5.6l5-2.8z" fill="currentColor"/>',
    saison: '<path d="M4 19.5h16"/><path d="M6.5 16v-4M11 16V7.5M15.5 16v-6M20 16V5"/>',
    team: '<path d="M8.5 4 4 6.8l1.8 3.6L8 9.2V20h8V9.2l2.2 1.2L20 6.8 15.5 4c-.6 1.3-1.9 2-3.5 2s-2.9-.7-3.5-2z"/>'
  };
  function icons(root) {
    root.querySelectorAll("i[data-ic]").forEach(function (el) {
      el.outerHTML = '<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">' + ICONS[el.dataset.ic] + "</svg>";
    });
  }

  window.R4 = { US: US, THEM: THEM, RA: RA, KM: KM, flow: flow, CLUBS: CLUBS, setClub: setClub, fit: fit, contrast: contrast, mix: mix };

  icons(document);
  document.querySelectorAll("[data-club-pick]").forEach(function (b) { b.addEventListener("click", function () { setClub(b.dataset.clubPick); }); });
  var q = new URLSearchParams(location.search).get("club");
  window.addEventListener("DOMContentLoaded", function () { setClub(CLUBS[q] ? q : "rot"); fit(); });
  window.addEventListener("resize", fit);
  window.addEventListener("load", fit);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
})();
