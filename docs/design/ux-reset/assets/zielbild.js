/* ===== Zielbild: puts every screen of anlauf-screens.js on the page =====
   Only for this presentation page. The one switch is the club colour (six demo colours);
   the opponent is TSV Thalwil in black, or unknown where a frame says so. */
var ZB = { club: "blau", opp: "thalwil" };

function frame(id, form, fn, opt) {
  var el = document.createElement("div");
  el.className = "app " + form; el.setAttribute("data-shot", id); el.setAttribute("data-club", ZB.club);
  el.innerHTML = fn();
  var k = kit(KITS[ZB.club], opt && opt.opp === null ? null : KITS[ZB.opp]);
  dress(el, k);
  return el;
}
function renderAll() {
  CAMS.length = 0;
  var v = document.getElementById("views"); v.innerHTML = "";
  SCREENS.forEach(function (s) {
    var sec = document.createElement("section"); sec.className = "view"; sec.id = s[0];
    sec.innerHTML = "<header><b>" + s[1] + "</b><span>" + s[2] + '</span></header><div class="pair"></div>';
    sec.querySelector(".pair").append(frame(s[0] + "-desk", "desk", s[3]), frame(s[0] + "-phone", "phone", s[4]));
    v.appendChild(sec);
  });
  var st = document.createElement("section"); st.className = "view"; st.id = "zustaende";
  st.innerHTML = '<header><b>Zustände</b><span>7.13 · Handy 390 · jeder sagt, was los ist, zeigt, was kommt, und bietet eine Handlung an</span></header><div class="grid"></div>';
  STATES.forEach(function (s) {
    var f = document.createElement("figure"); f.innerHTML = "<figcaption>" + s[1] + "</figcaption>";
    f.appendChild(frame(s[0], "phone", s[2], s[3])); st.querySelector(".grid").appendChild(f);
  });
  v.appendChild(st);
  v.querySelectorAll(".app").forEach(drawGraphics);
  v.querySelectorAll("[data-club-pick]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.clubPick === ZB.club)); });
  camInit(v);
  if (/still/.test(location.search)) v.querySelectorAll(".play").forEach(function (e) { e.classList.remove("play"); });
  document.querySelectorAll("[data-c]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.c === ZB.club)); });
}
document.addEventListener("click", function (e) {
  var f = e.target.closest("[data-flip]");
  if (f) {
    var li = f.closest("li"), scene = f.dataset.flip === "s";
    li.querySelectorAll("[data-flip]").forEach(function (x) { x.setAttribute("aria-pressed", String(x === f)); });
    li.querySelector(".fig > svg").hidden = scene; li.querySelector(".scene").hidden = !scene;
    return;
  }
  var b = e.target.closest("[data-c], [data-club-pick]");
  if (b) { ZB.club = b.dataset.c || b.dataset.clubPick; renderAll(); return; }
  if (e.target.closest(".app a")) e.preventDefault();
});
(function () {
  var q = new URLSearchParams(location.search);
  if (q.get("club") && KITS[q.get("club")]) ZB.club = q.get("club");
  renderAll();
})();
