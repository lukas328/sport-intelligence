/* Profile portraits: every person as a cut-paper head in profile, facing the play (to the right).
   No photo, no consent problem; each person keeps the same head everywhere. */
var PROFIL = (function () {
  var SKIN = ["#f2cfae", "#e2b088", "#c98d62", "#9a6544", "#6a432c"];
  var HAIR = ["#2a1d15", "#5d371c", "#b98a4e", "#161616", "#8c8378", "#7a2f1a"];
  /* hair shapes, drawn over the head (viewBox 0 0 100 120, face to the right) */
  var CUT = {
    kurz: "M27 52 C22 30 34 14 52 12 C66 11 74 18 75 28 C70 24 62 24 57 26 C52 28 46 30 42 36 C40 40 39 46 37 52 Z",
    seite: "M26 54 C21 30 33 12 53 11 C68 11 77 20 76 30 C68 22 56 22 48 28 C41 33 38 42 36 54 Z",
    zopf: "M27 54 C22 30 34 13 52 12 C67 11 75 19 75 29 C68 24 58 25 50 28 C44 31 40 40 37 54 Z M30 40 C20 42 12 52 10 66 C9 74 14 78 18 74 C20 66 24 56 32 50 Z",
    dutt: "M27 54 C22 30 34 13 52 12 C67 11 75 19 75 29 C68 24 58 25 50 28 C44 31 40 40 37 54 Z M30 24 a10 10 0 1 0 0.1 0 Z",
    lang: "M28 54 C22 30 34 12 52 11 C67 11 76 19 75 30 C68 24 58 25 50 28 C43 31 40 40 39 52 C38 64 40 78 44 92 L24 94 C20 80 22 66 28 54 Z",
    locken: "M28 56 c-8-4-8-14-2-18 c-4-8 2-16 10-16 c2-8 12-12 20-8 c6-4 16-2 18 6 c4 2 4 8 0 10 c-6-4-14-4-20-1 c-8 3-14 10-16 20 c-2 4-6 8-10 7 Z",
    glatze: "M30 50 C29 44 30 40 32 37 C34 42 35 47 37 53 Z",
    bart: "M70 64 C72 70 70 76 62 80 C54 82 46 80 42 74 C46 72 52 70 58 70 C62 70 66 68 70 64 Z"
  };
  var HEAD = "M30 50 C28 30 40 14 54 13 C66 13 74 22 75 34 L77 40 L83 50 C84 52 82 53 79 53 L76 54 C77 56 77 57 75 58 C76 60 76 61 74 62 L76 66 C76 71 72 75 66 77 C60 80 52 81 46 79 C42 78 38 74 36 70 C32 64 30 58 30 50 Z";
  function head(p, o) {
    o = o || {};
    var skin = SKIN[p.s || 0], hair = HAIR[p.h || 0], shirt = o.shirt || (p.gk ? "var(--keeper,#6a4bc4)" : "var(--club)"), num = o.num !== false, ink = p.gk && !o.shirt ? "#fff" : "var(--club-ink)";
    var s = '<svg class="pf" viewBox="0 0 100 120" role="img" aria-label="' + (p.n || "") + '">';
    s += '<path d="M6 120 C8 104 20 96 34 94 L66 94 C82 96 94 104 96 120 Z" fill="' + shirt + '" stroke="var(--pf-edge,transparent)" stroke-width="2"/>';
    s += '<path d="M40 92 L44 76 L58 76 L62 92 C56 98 46 98 40 92 Z" fill="' + skin + '"/>';
    s += '<path d="M38 94 C44 102 58 102 64 94" fill="none" stroke="' + ink + '" stroke-width="3" opacity=".55"/>';
    if (p.cap && o.cap !== false) s += '<path d="M70 99 L88 103 L86 111 L68 107 Z" fill="#f4f4f4" stroke="#0003"/><text x="78" y="109.5" text-anchor="middle" transform="rotate(12 78 106)" style="font:800 8px sans-serif;fill:#222">C</text>';
    s += '<path d="' + HEAD + '" fill="' + skin + '"/>';
    s += '<ellipse cx="44" cy="52" rx="4.6" ry="6.2" fill="' + skin + '" stroke="#0002" stroke-width="1.5"/>';
    if (p.c) p.c.split(" ").forEach(function (c) { CUT[c].split(/ (?=M)/).forEach(function (d) { s += '<path d="' + d + '" fill="' + hair + '"/>'; }); });
    s += '<circle cx="67" cy="43" r="1.8" fill="#2a1d15"/>';
    if (num && p.no) s += '<text x="62" y="114" text-anchor="middle" style="font:800 16px var(--disp,sans-serif);fill:' + ink + '">' + p.no + "</text>";
    return s + "</svg>";
  }
  /* the squad of HC Zürichsee, Herren 1 (demo), and the coach */
  var P = {
    brunner: { n: "Levin Brunner", f: "Levin", no: 4, cap: 1, s: 0, h: 2, c: "seite" },
    graf: { n: "Elias Graf", f: "Elias", no: 10, s: 1, h: 0, c: "kurz bart" },
    schmid: { n: "Jonas Schmid", f: "Jonas", no: 11, s: 3, h: 3, c: "locken" },
    meier: { n: "Nico Meier", f: "Nico", no: 8, s: 2, h: 1, c: "kurz" },
    roth: { n: "Luca Roth", f: "Luca", no: 7, s: 0, h: 5, c: "lang" },
    baumann: { n: "Jana Baumann", f: "Jana", no: 13, s: 1, h: 2, c: "zopf" },
    rbrunner: { n: "Rafael Brunner", f: "Rafael", no: 6, s: 2, h: 0, c: "seite" },
    mia: { n: "Mia Meier", f: "Mia", no: 1, gk: 1, s: 0, h: 1, c: "dutt" },
    keller: { n: "Tim Keller", f: "Tim", no: 3, s: 4, h: 3, c: "glatze bart" },
    frei: { n: "Noah Frei", f: "Noah", no: 9, s: 1, h: 4, c: "kurz" },
    huber: { n: "Lea Huber", f: "Lea", no: 14, s: 3, h: 0, c: "dutt" },
    wyss: { n: "Sven Wyss", f: "Sven", no: 5, s: 0, h: 2, c: "kurz" },
    kaya: { n: "Deniz Kaya", f: "Deniz", no: 12, s: 2, h: 3, c: "seite bart" },
    zeller: { n: "Mara Zeller", f: "Mara", no: 16, s: 1, h: 5, c: "zopf" },
    coach: { n: "Demo Trainerin", f: "Trainerin", s: 1, h: 4, c: "lang" }
  };
  return { head: head, P: P };
})();
