/* ===== Anlauf: screens =====
   Every screen of SPEC.md section 7 as markup, desktop 1280 and phone 390. These functions are
   the reference for the React pages: structure, wording, which graphic sits where. Graphics are
   empty <svg> elements with data attributes, filled by anlauf-feld.js. */

const I = {
  search: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5"/><path d="M13 13l5 5"/></svg>',
  plus: '<svg viewBox="0 0 20 20" stroke="currentColor" stroke-width="2.6" aria-hidden="true"><path d="M10 3v14M3 10h14"/></svg>',
  ok: '<svg viewBox="0 0 18 18" role="img" aria-label="bestätigt"><path d="M3 9.5l4 4 8-9" fill="none" stroke="var(--win)" stroke-width="2.6"/></svg>',
  drag: '<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><rect x="4" y="5" width="12" height="2"/><rect x="4" y="9" width="12" height="2"/><rect x="4" y="13" width="12" height="2"/></svg>',
  err: '<svg viewBox="0 0 28 28" role="img" aria-label="Fehler"><rect x="2" y="2" width="24" height="24" fill="none" stroke="var(--loss)" stroke-width="3"/><path d="M9 9l10 10M19 9L9 19" stroke="var(--loss)" stroke-width="3"/></svg>'
};
const NAV = ["Spiele", "Szenen", "Saison", "Team"];

/* ---------- frame ---------- */
function topD(on) {
  return `<header class="top"><span class="club d"><span class="crest">HCZ</span>HC Zürichsee</span>
    <nav class="nav" aria-label="Hauptnavigation">${NAV.map(n => `<a href="#"${n === on ? ' aria-current="page"' : ""}>${n}</a>`).join("")}</nav>
    <div class="right"><a class="lnk" href="#">Suchen</a><a class="btn" href="#">Video hochladen</a></div></header>`;
}
function topP() { return `<header class="ptop"><span class="club d"><span class="crest">HCZ</span>HC Zürichsee</span><button class="ibtn" aria-label="Suchen">${I.search}</button><button class="ibtn plus" aria-label="Video hochladen">${I.plus}</button></header>`; }
function barP(on) { return `<nav class="tabbar" aria-label="Hauptnavigation">${NAV.map(n => `<a href="#"${n === on ? ' aria-current="page"' : ""}>${n}</a>`).join("")}</nav>`; }
/* full screen without navigation: Prüfen, Spieltag, the shared page, Einstieg */
function bareTop(left, right) { return `<header class="ptop" style="padding:0 ${right && right.desk ? 32 : 16}px"><span class="back">${left}</span>${right ? right.html : ""}</header>`; }

/* ---------- heads ---------- */
function scoreHTML(a, b) { return `<span class="e e2" aria-hidden="true">${a}:${b}</span><span class="e e1" aria-hidden="true">${a}:${b}</span><span>${a}:<u>${b}</u></span>`; }
const TITLE = "Gewonnen. Und drei Dinge zum Mitnehmen.";
function headStart(ph, W, o = {}) {
  const unknown = o.unknown, title = o.title || TITLE;
  return `<section class="wurf big"${ph && unknown ? ' style="height:460px"' : ""}><div><p class="kick">${o.kick || (ph ? "Sa gegen TSV Thalwil · fertig seit So, 9:40" : "Samstag gegen TSV Thalwil · Analyse fertig seit Sonntag, 9:40")}</p><h1 class="d">${title}</h1></div>
    <div><div class="score n" role="img" aria-label="26 zu 18">${scoreHTML(26, 18)}</div><p class="names"><span class="d">HC Zürichsee</span><span class="d"><i class="oc"></i>TSV Thalwil${unknown ? ", Farbe offen" : ph ? "" : ", Rang 5"}</span></p>
    ${unknown ? `<div class="ask">Welche Farbe trägt Thalwil? ${["#17191c", "#ffffff", "#0b7a8a", "#d3202e", "#12804a"].map(c => `<button aria-label="Farbe wählen"><i style="background:${c}"></i></button>`).join("")}</div>` : ""}</div>
    <svg class="fl" data-fl data-w="${W}" data-h="${ph ? 84 : 160}" role="img" aria-label="Verlauf der Tordifferenz aus dem Spielbericht: Halbzeit plus 4, Schluss plus 8, von der 38. bis zur 44. Minute minus 5"></svg></section>`;
}
function headMatch(ph, W) {
  return `<section class="wurf big" style="height:${ph ? 360 : 380}px"><div><p class="kick">Samstag, 7. November · Halle Seefeld</p><h1 class="d" style="font-size:${ph ? 28 : 44}px">HC Zürichsee gegen TSV Thalwil</h1><p class="meta">Halbzeit 13:9 · Time-outs 2 und 3 · Rang 5</p></div>
    <div><div class="score n" role="img" aria-label="26 zu 18"${ph ? ' style="font-size:88px;margin-top:10px"' : ""}>${scoreHTML(26, 18)}</div></div>
    <svg class="fl" data-fl data-w="${W}" data-h="${ph ? 72 : 150}" role="img" aria-label="Verlauf der Tordifferenz aus dem Spielbericht"></svg></section>`;
}
function strip(ph, o = {}) {
  const a = o.a || 26, b = o.b || 18, opp = o.opp || "TSV Thalwil";
  return `<section class="strip"><p class="nm d">HC Zürichsee<small>${o.sub || (ph ? "gegen " + opp : "gegen " + opp + " · Sa., 7. Nov. · Halle Seefeld")}</small></p><div class="score n" role="img" aria-label="${a} zu ${b}"><span class="e" aria-hidden="true">${a}:${b}</span><span>${a}:<u>${b}</u></span></div></section>`;
}
/* the page head without a match: kick line, slanted title, the club wedge underneath */
function kopf(o) { return `<section class="kopf"><p class="kick">${o.kick}</p><h1 class="d">${o.title}</h1>${o.n ? `<p class="side-n"><b class="n">${o.n}</b><span>${o.nl}</span></p>` : ""}${o.acts ? `<div class="acts">${o.acts}</div>` : ""}</section>`; }
function tabs(on, noVideo) {
  return `<nav class="tabs" aria-label="Spiel">${["Spiel", "Video", "Zahlen"].map(t => `<a class="d${noVideo && t === "Video" ? " off" : ""}" href="#"${t === on ? ' aria-current="page"' : ""}${noVideo && t === "Video" ? ' aria-disabled="true"' : ""}>${t}</a>`).join("")}${noVideo ? "" : '<a class="q d" href="#"><em>3</em>Prüfen</a>'}</nav>`;
}

/* ---------- the three things ---------- */
const THINGS = [
  { v: "9", unit: "von 18", p: "Gegentore über rechts aussen", s: "Saison bisher: jedes dritte über diese Seite", b: "ra", sc: "9 Szenen", t: "2:40", drill: "Abwehr gegen Flügel" },
  { v: "6", unit: "Gegenstösse", p: "Tore nach eigenem Ballverlust", s: "3 davon zwischen der 38. und 44. Minute", b: "gs", sc: "6 Szenen", t: "1:55", drill: "Rückzug in die 5:1" },
  { v: "7", unit: "von 26", p: "Tore vom Kreis", s: "bester Wert der Saison", up: 1, b: "kr", sc: "7 Szenen", t: "2:10" }
];
function stage(o) {
  return `<div class="stage"${o.style ? ` style="${o.style}"` : ""}><svg data-cam="${o.cam || "ra"}" data-view="${o.view}" data-w="${o.w}" data-r="${o.r}"${o.labels ? " data-labels" : ""} role="img" aria-label="${o.aria || "Taktikkamera 39:49 bis 39:55: Thalwil trifft über rechts aussen"}"></svg>${o.cap || ""}<div class="bar"><button class="pause" aria-pressed="false">Pause</button>${o.mode ? '<div class="mode" role="group" aria-label="Ansicht"><button aria-pressed="false">Video</button><button aria-pressed="true">Taktik</button></div>' : ""}${o.bar ? `<span>${o.bar}</span>` : ""}<span class="clk">${o.clk || "39:55"}</span></div>${o.capBelow || ""}</div>`;
}
function things(ph, o = {}) {
  const W = ph ? 132 : 380;
  return `<ol class="things play">${THINGS.map((t, i) => {
    const sw = o.preview && i === 0 && !ph;
    return `<li><div class="no"><em>${i + 1} von 3</em><b class="n">${t.v}</b><span class="d">${t.unit}</span></div><p>${t.p}</p><small class="${t.up ? "up" : ""}">${t.s}</small>
      ${o.drill && t.drill ? `<small>Dazu üben: <a class="lnk" href="#">${t.drill}</a></small>` : ""}
      ${sw ? '<div class="flip" role="group" aria-label="Ansicht von Punkt 1"><button aria-pressed="true" data-flip="b">Alle 9</button><button aria-pressed="false" data-flip="s">Szene 39:55</button></div>' : ""}
      <div class="fig"><svg data-b="${t.b}" data-w="${W}" role="img" aria-label="${t.v} ${t.unit}: jeder Anlauf bis zur Wurfposition, dann der Strich zum Tor"></svg>${sw ? `<div class="scene" hidden>${stage({ view: "halfB", w: W, r: 8, bar: "Taktikkamera" })}</div>` : ""}</div>
      <a class="btn s" href="#">${t.sc} <small>${t.t}</small></a></li>`;
  }).join("")}</ol>`;
}
function keyLine() { return '<p class="key"><span><i></i>Anlauf bis zur Wurfposition, von dir bestätigt</span><span><i class="est"></i>geschätzt</span><span>dünner Strich: zum Tor</span></p>'; }
function camKey(ball = true) { return `<p class="camkey"><span><i class="us"></i>Zürichsee</span><span><i class="them"></i>Thalwil</span><span><i class="ref"></i>Schiri</span>${ball ? '<span><i class="ball"></i>Ball, nur wo erkannt</span>' : ""}<span>Nummer nur, wo sie gelesen wurde</span></p>`; }
function balls(cam = "ra", ph) {
  const S = CAM[cam], t0 = S.from[0] + ":" + S.from[1], t1 = clock(S, 1);
  return `<div class="balls" data-balls data-cam="${cam}" role="img" aria-label="${S.ball.length ? "Ball erkannt: 39:49 bei der 14, 39:50 bei der 9, ab 39:53 bei der 5; dazwischen nicht erkannt" : "Ball in dieser Szene nicht erkannt"}"></div><p class="ballkey"><span>${t0}</span><span>${ph ? "Ball bei" : "Wer den Ball hat, wo er im Bild erkannt wurde"}</span><span>${t1}</span></p>`;
}

/* ---------- lists ---------- */
const GAMES = [
  { d: "31.10.", w: "auswärts", o: "BSV Stäfa", st: "done", r: [19, 26], sub: "2 Dinge · 33 Szenen", b: "staefa", first: "Gegenstösse" },
  { d: "24.10.", w: "Heim", o: "HC Meilen", st: "run", r: [23, 22], sub: "Analyse läuft, noch etwa 25 Minuten" },
  { d: "17.10.", w: "auswärts", o: "SG Horgen", st: "none", r: [29, 19] },
  { d: "10.10.", w: "Heim", o: "TV Wädenswil", st: "none", r: [24, 27] }
];
function mini(g, w) {
  if (g.st === "done") return `<span class="mfz"><svg data-b="${g.b}" data-w="${w}" role="img" aria-label="Punkt 1 dieses Spiels: ${g.first}"></svg></span>`;
  return `<span class="mfz"><svg data-empty data-w="${w}" aria-hidden="true"></svg><em>${g.st === "run" ? "Analyse läuft" : "kein Video"}</em></span>`;
}
function gameList(ph) {
  return GAMES.map(g => {
    const win = g.r[0] > g.r[1], res = `<div class="res ${win ? "w" : "l"}"><b class="n">${g.r[0]}:${g.r[1]}</b><small>${win ? "Sieg" : "Niederlage"}</small></div>`;
    if (ph) return `<div class="pgame">${mini(g, 84)}<div><h4 class="d">${g.o}</h4><p>${g.d} · ${g.st === "none" ? '<a class="lnk" href="#">Video hochladen</a>' : g.st === "run" ? "Analyse läuft" : "33 Szenen"}</p></div>${res}</div>`;
    const sub = g.st === "none" ? 'Nur Spielbericht · <a class="lnk" href="#">Video hochladen</a>' : g.sub + (g.st === "done" ? " · Punkt 1: " + g.first : "");
    return `<div class="game"><div class="when">Sa<b class="d">${g.d}</b>${g.w}</div>${mini(g, 128)}<div><h4 class="d">${g.o}</h4><p>${sub}</p>${g.st === "run" ? '<div class="pbar"><i style="width:62%"></i></div>' : ""}</div>${res}</div>`;
  }).join("");
}
function table(rows = 3) {
  const T = [["1 TV Talwiese", 6, "+21", 10], ["2 HC Zürichsee", 6, "+14", 8, 1], ["3 HSG Rheinau", 6, "+9", 8], ["4 SG Horgen", 6, "+2", 6], ["5 TSV Thalwil", 6, "-4", 5]];
  return `<table class="st"><thead><tr><th>Rang</th><th>Sp.</th><th>Diff.</th><th>Pkt.</th></tr></thead><tbody>${T.slice(0, rows).map(r => `<tr${r[4] ? ' class="me"' : ""}><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td></tr>`).join("")}</tbody></table>`;
}
function sideStart() {
  return `<aside class="side"><section class="next"><p class="k">Nächster Gegner · So, 17:30</p><h3 class="d">bei HSG Rheinau</h3><div class="mfz" style="width:100%"><svg data-b="rheinau" data-w="340" role="img" aria-label="Hinspiel: 5 Tore aus dem Rückraum links"></svg></div><ul class="facts"><li>Hinspiel 24:27, 5 Tore aus dem Rückraum links</li><li><span>Rang 3, zuletzt drei Siege</span><a class="lnk" href="#">12 Szenen</a></li></ul></section>
    <section><div class="hh"><b class="d">Tabelle</b><span>3. Liga, Gruppe 2</span></div>${table(3)}</section></aside>`;
}

/* ===================== 7.1 Spiele, the start ===================== */
function startDesk() {
  return topD("Spiele") + headStart(false, 1280)
    + '<div class="actrow"><a class="btn" href="#">Spiel öffnen</a><a class="btn line" href="#">Fürs Team zusammenstellen</a><span class="tag">Prüfen</span><a class="lnk" href="#">3 Fragen offen, 1 Minute</a></div>'
    + '<div style="height:28px"></div>' + things(false, { preview: true }) + keyLine()
    + `<div class="cols"><section><div class="hh"><b class="d">Alle Spiele</b><span>2 von 6 ohne Video</span></div>${gameList(false)}</section>${sideStart()}</div>`;
}
function startPhone(o = {}) {
  return topP() + headStart(true, 390, o)
    + '<div class="actrow"><a class="btn" href="#">Spiel öffnen</a><a class="lnk" href="#">3 Fragen offen, 1 Minute</a></div><div style="height:24px"></div>'
    + things(true) + keyLine()
    + `<section style="padding:28px 16px 0"><div class="hh"><b class="d">Szene aus Punkt 1</b><span>39:55</span></div>${stage({ view: "halfDeep", w: 358, r: 9, bar: "Taktikkamera" })}</section>`
    + `<section style="padding:32px 16px 24px"><div class="hh"><b class="d">Alle Spiele</b><span>2 ohne Video</span></div>${gameList(true)}</section>` + barP("Spiele");
}

/* ===================== 7.2 Spiel ===================== */
function spielDesk() {
  return topD("Spiele") + headMatch(false, 1280) + tabs("Spiel")
    + '<p class="src"><span>Quellen: Video (60 von 60 Minuten) · Spielbericht von handball.ch · 21 von 24 Toren von dir bestätigt</span><a class="lnk" href="#">Wie gerechnet?</a></p>'
    + things(false, { drill: true }) + keyLine()
    + '<div class="actrow"><a class="btn" href="#">Fürs Team zusammenstellen</a><a class="lnk" href="#">Highlights teilen</a><a class="lnk" href="#">Als Bild für den Chat</a></div>'
    + `<div class="sp"><div class="col"><section><div class="hh"><b class="d">Punkt 1, geöffnet</b><span>Szene 3 von 9 auf der Taktikkamera</span></div>${stage({ view: "camL", w: 852, r: 11, labels: 1, bar: "Thalwil trifft über rechts aussen" })}${balls("ra")}${camKey()}</section>
      <section><div class="hh"><b class="d">Telegramm</b><a class="lnk" href="#">Kopieren</a></div><p class="telegramm"><b>HC Zürichsee gegen TSV Thalwil 26:18 (13:9).</b> Halle Seefeld. Torfolge: 2:1, 5:4, 9:6, 13:9; 15:12, 17:15, 21:16, 26:18. Strafen: 3-mal 2 Minuten gegen Zürichsee, 4-mal 2 Minuten gegen Thalwil. Beste Werfer: Brunner 7, Graf 5/2, Schmid 4. Im Tor: Meier, 11 Paraden.</p></section></div>
      <aside class="side"><section class="zf"><div class="hh"><b class="d">Gegentore</b><span>nach Position</span></div><svg data-zones data-who="them" data-w="340" role="img" aria-label="Gegentore nach Position: rechts aussen 9, Rückraum links 3, Rückraum Mitte 2, links aussen 2, Rückraum rechts 1, Kreis 1"></svg><p class="foot">Punkt: geschätzte Wurfposition, leer: noch nicht bestätigt.</p></section>
      <section class="zf"><div class="hh"><b class="d">Eigene Tore</b><span>nach Position</span></div><svg data-zones data-who="us" data-w="340" role="img" aria-label="Eigene Tore nach Position: Kreis 7, je 3 von den Flügeln und aus dem Rückraum, 2 Siebenmeter, 2 Gegenstösse"></svg></section>
      <div class="kpis"><div class="kpi"><b class="n">11</b><span>Paraden Meier, von dir markiert</span></div><div class="kpi"><b class="n">11</b><span>Ballverluste, aus dem Spielbericht</span></div><div class="kpi"><b class="n">58<small>%</small></b><span>Wurfquote, 26 von 45, Würfe von dir markiert</span></div></div></aside></div>`;
}
function spielPhone() {
  return topP() + headMatch(true, 390) + tabs("Spiel") + '<p class="src">Video 60 von 60 Minuten · Spielbericht von handball.ch · 21 von 24 Toren bestätigt</p>'
    + things(true, { drill: true }) + keyLine()
    + '<div class="actrow" style="flex-direction:column;align-items:stretch"><a class="btn" href="#">Fürs Team zusammenstellen</a><div style="display:flex;gap:16px;flex-wrap:wrap"><a class="lnk" href="#">Highlights teilen</a><a class="lnk" href="#">Als Bild für den Chat</a></div></div>'
    + '<section class="zf" style="padding:32px 16px 0"><div class="hh"><b class="d">Gegentore</b><span>nach Position</span></div><svg data-zones data-who="them" data-w="358" role="img" aria-label="Gegentore nach Position: rechts aussen 9"></svg></section>'
    + '<div class="kpis" style="margin:24px 16px 28px"><div class="kpi"><b class="n">11</b><span>Paraden, von dir markiert</span></div><div class="kpi"><b class="n">11</b><span>Ballverluste, Spielbericht</span></div><div class="kpi"><b class="n">58<small>%</small></b><span>Wurfquote, 26 von 45</span></div></div>' + barP("Spiele");
}

/* ===================== 7.3 Video ===================== */
const SCN = [["38:40", "Ballverlust, Fehlpass", "danach Gegenstoss, Tor Thalwil"], ["39:55", "Tor Thalwil über rechts aussen", "läuft gerade"], ["41:05", "Ballverlust, Schrittfehler", ""], ["42:30", "Parade Meier", "von dir markiert"], ["43:48", "Ballverlust, Stürmerfoul", "danach Gegenstoss, Tor Thalwil"]];
const SCN_KR = [["11:20", "Tor Zürichsee vom Kreis", "Nummer 8 gelesen"], ["18:02", "Tor Zürichsee vom Kreis", "läuft gerade"], ["24:47", "Tor Zürichsee vom Kreis", "Wurfposition von dir bestätigt"]];
function sceneList(on = 1, list = SCN) { return `<ul class="scn">${list.map((s, i) => `<li${i === on ? ' class="on" aria-current="true"' : ""}><b class="n">${s[0]}</b><span>${s[1]}${s[2] ? `<small>${s[2]}</small>` : ""}</span></li>`).join("")}</ul>`; }
function videoDesk() {
  return topD("Spiele") + strip(false) + tabs("Video")
    + `<div class="sp" style="grid-template-columns:minmax(0,1fr) 320px"><div style="min-width:0">${stage({ view: "camL", w: 848, r: 12, labels: 1, mode: 1, bar: "Positionen aus dem Video, 10 pro Sekunde", cap: '<p class="cap">Thalwil trifft über rechts aussen<small>Punkt 1 · Szene 3 von 9</small></p>' })}
      ${balls("ra")}${camKey()}
      <div class="rail" style="margin-top:20px"><svg data-rail role="img" aria-label="Zeitleiste: Tore aus dem Spielbericht, Zürichsee oben, Thalwil unten, markierte Phase 38. bis 44. Minute"></svg><div class="ax"><span>Anwurf</span><span>Halbzeit</span><span>Schluss</span></div></div>
      <div class="tools" style="margin-top:18px"><a class="btn" href="#">Szene merken</a><a class="btn line" href="#">Zeichnen</a><a class="btn line" href="#">Spielerin hervorheben</a><a class="btn line" href="#">Teilen</a></div></div>
      <aside class="side"><section><div class="hh"><b class="d">38. bis 44.</b><span>5 Szenen</span></div>${sceneList()}</section>
      <section><div class="hh"><b class="d">Notizen</b></div><p class="note">39:55 Unsere 7 tritt heraus, die Lücke geht auf.</p><p class="k" style="margin-top:8px">Nur für dich, bis du die Szene teilst</p></section></aside></div>`;
}
function videoPhone(o = {}) {
  const cam = o.cam || "ra", kr = cam === "kr";
  return topP() + strip(true) + tabs("Video")
    + stage({ cam, view: "halfDeep", w: 390, r: 10, labels: 1, mode: 1, clk: kr ? "18:02" : "39:55", style: "margin-top:12px", aria: kr ? "Taktikkamera 17:56 bis 18:02: Tor vom Kreis, Ball nicht erkannt" : undefined,
      capBelow: `<p class="cap">${kr ? "Tor Zürichsee vom Kreis<small>Punkt 3 · Szene 2 von 7</small>" : "Thalwil trifft über rechts aussen<small>Punkt 1 · Szene 3 von 9</small>"}</p>` })
    + `<div style="padding:0 16px">${balls(cam, true)}</div>`
    + `<div style="padding:0 16px">${kr ? '<p class="camkey"><span><i class="us"></i>Zürichsee</span><span><i class="them"></i>Thalwil</span><span>Anlauf gestrichelt: Wurfposition geschätzt</span></p>' : '<p class="camkey"><span><i class="us"></i>Zürichsee</span><span><i class="them"></i>Thalwil</span><span><i class="ref"></i>Schiri</span><span><i class="ball"></i>Ball, wo erkannt</span></p>'}</div>`
    + (kr ? "" : '<div class="rail" style="padding:16px 16px 0"><svg data-rail role="img" aria-label="Zeitleiste"></svg><div class="ax"><span>Anwurf</span><span>Halbzeit</span><span>Schluss</span></div></div>')
    + `<section style="padding:24px 16px 28px"><div class="hh"><b class="d">${kr ? "Tore vom Kreis" : "38. bis 44."}</b><span>${kr ? "Punkt 3 · 7 Szenen" : "5 Szenen"}</span></div>${kr ? sceneList(1, SCN_KR) : sceneList()}<a class="btn" href="#" style="width:100%;margin-top:16px">Szene merken</a></section>` + barP("Spiele");
}

/* ===================== 7.4 Zahlen ===================== */
const ROWS = [[4, "Levin Brunner", 7, "", "", 10, 1], [10, "Elias Graf", 5, "2/2", 1, 9, 1], [11, "Jonas Schmid", 4, "", "", 8, 1], [8, "Nico Meier", 4, "", 1, 5, 0], [7, "Luca Roth", 3, "", "", 6, 1], [13, "Jana Baumann", 2, "", 1, 4, 0], [6, "Rafael Brunner", 1, "", "", 3, 0]];
const L = v => v === "" ? "" : `<a href="#">${v}</a>`;
function phases(ph) {
  const P = [[ph ? "Überzahl, 8 Min." : "Überzahl, 8 Minuten", 5, 1, "aus den 2-Minuten-Strafen"], [ph ? "Unterzahl, 6 Min." : "Unterzahl, 6 Minuten", 2, 3, "aus den 2-Minuten-Strafen"], ["Gegenstösse", 2, 6, "aus dem Video geschätzt"]];
  return `<ul class="phs">${P.map(r => `<li><span>${r[0]}<small>${r[3]}</small></span><b class="n">${r[1]}:${r[2]}</b><span class="pb" aria-hidden="true"><i class="us" style="flex:${r[1]}"></i><i class="them" style="flex:${r[2]}"></i></span></li>`).join("")}</ul>`;
}
function zahlenDesk() {
  const feld = ROWS.map(r => `<tr><td><b class="n">${r[0]}</b>${r[1]}</td><td>${L(r[2])}</td><td>${L(r[3])}</td><td>${L(r[4])}</td><td class="mk">${L(r[5])}</td><td class="mk">${Math.round(r[2] / r[5] * 100)} %</td><td class="ok">${r[6] ? I.ok : ""}</td></tr>`).join("");
  return topD("Spiele") + strip(false) + tabs("Zahlen") + '<p class="src">Jede Zahl führt zu ihren Szenen. Tore, 7 m und 2 Minuten aus dem Spielbericht; Würfe und Paraden von dir markiert; ein Haken heisst: Person von dir bestätigt.</p>'
    + `<div class="sp" style="gap:64px"><div class="col" style="gap:48px"><section><div class="hh"><b class="d">Feld</b><span>nach Toren</span></div><table class="tb"><thead><tr><th>Nr. Name</th><th>Tore</th><th>7 m</th><th>2 Min</th><th>Würfe, markiert</th><th>Quote</th><th>Bestätigt</th></tr></thead><tbody>${feld}</tbody></table><p class="foot">Vier weitere ohne Tor. <a class="lnk" href="#">Alle zeigen</a></p></section>
      <section><div class="hh"><b class="d">Tor</b></div><table class="tb"><thead><tr><th>Nr. Name</th><th>Gegentore</th><th>Paraden, markiert</th><th>7 m gehalten</th><th>Bestätigt</th></tr></thead><tbody><tr><td><b class="n">1</b>Mia Meier</td><td>${L(18)}</td><td class="mk">${L(11)}</td><td>${L("1 von 3")}</td><td class="ok">${I.ok}</td></tr></tbody></table></section></div>
      <aside class="side" style="gap:40px"><section class="zf"><div class="hh"><b class="d">Gegentore nach Position</b></div><svg data-zones data-who="them" data-w="340" role="img" aria-label="Gegentore nach Position: rechts aussen 9, Rückraum links 3"></svg><p class="foot">Aus den Positionen vor jedem Tor geschätzt, 15 von 18 bestätigt.</p></section>
      <section><div class="hh"><b class="d">Ziel im Tor</b><span>von dir markiert</span></div><div class="torg" role="img" aria-label="Von dir markiert, 12 von 18 Toren: unten links 4">${[2, 1, 1, 1, 0, 1, 4, 0, 2].map(v => `<span class="n"${v ? "" : ' style="color:var(--ink-2)"'}>${v}</span>`).join("")}</div><p class="foot">12 von 18 Toren markiert. <a class="lnk" href="#">Weiter markieren</a></p></section>
      <section><div class="hh"><b class="d">Phasen</b></div>${phases(false)}</section></aside></div>`;
}
function zahlenPhone() {
  const feld = ROWS.map(r => `<tr><td><b class="n">${r[0]}</b>${r[1].split(" ")[0]} ${r[1].split(" ")[1][0]}.</td><td>${L(r[2])}</td><td>${L(r[3])}</td><td>${L(r[4])}</td><td class="ok">${r[6] ? I.ok : ""}</td></tr>`).join("");
  return topP() + strip(true) + tabs("Zahlen") + '<p class="src">Tore, 7 m und 2 Minuten aus dem Spielbericht.</p>'
    + `<section style="padding:4px 16px 0"><div class="hh"><b class="d">Feld</b><span>nach Toren</span></div><table class="tb" style="font-size:15px"><thead><tr><th>Nr. Name</th><th>Tore</th><th>7 m</th><th>2 Min</th><th aria-label="Bestätigt">Best.</th></tr></thead><tbody>${feld}</tbody></table></section>`
    + '<section class="zf" style="padding:36px 16px 0"><div class="hh"><b class="d">Gegentore</b><span>nach Position</span></div><svg data-zones data-who="them" data-w="358" role="img" aria-label="Gegentore nach Position"></svg></section>'
    + `<section style="padding:36px 16px 28px"><div class="hh"><b class="d">Phasen</b></div>${phases(true)}</section>` + barP("Spiele");
}

/* ===================== 7.5 Prüfen ===================== */
const WHO = [[13, "Jana Baumann"], [11, "Jonas Schmid"], [4, "Levin Brunner"], [6, "Rafael Brunner"], [12, "Lara Moser"], [5, "Ben Zürcher"]];
function checkBody(ph) {
  return `<div class="check"><div><div class="frame"><svg data-hall="ra" data-mode="who" data-who="us:13" role="img" aria-label="Ausschnitt aus dem Video, die Person ist gelb umrahmt"></svg><p class="cap">39:52 · 60 Sekunden im Bild, Nummer nie gelesen</p></div>
    ${ph ? "" : '<p class="why">Die Personen mit der längsten Zeit im Bild kommen zuerst. Du kannst jederzeit aufhören, jede Antwort ist sofort gespeichert und macht die Zahlen genauer.</p>'}</div>
    <div><p class="k">Frage 5 von 36</p><h2 class="d">Wer ist das?</h2><div class="keys">${WHO.map((w, i) => `<button${i === 0 ? ' class="first"' : ""}><b class="n">${w[0]}</b>${ph ? w[1].split(" ")[0] : w[1]}</button>`).join("")}
      <button class="plain">Andere</button><button class="plain">Gegner</button><button class="plain wide">Weiss nicht</button></div>
      ${ph ? "" : '<p class="foot" style="margin-top:16px">Tasten: Rückennummer tippen, Leertaste für «weiss nicht», U nimmt die letzte Antwort zurück.</p>'}
      <div class="progress" role="img" aria-label="4 von 36 beantwortet">${Array.from({ length: 36 }, (_, i) => `<i${i < 4 ? ' class="done"' : ""}></i>`).join("")}</div>
      <p class="foot">Fünf Antworten reichen für die Zahlen der Stammsieben.</p></div></div>`;
}
function pruefenDesk() { return bareTop("Prüfen · HC Zürichsee gegen TSV Thalwil", { desk: 1, html: '<a class="btn line" href="#">Später weiter</a>' }) + strip(false, { sub: "gegen TSV Thalwil · 3 Fragen zu Toren, 33 zu Personen" }) + checkBody(false); }
function pruefenPhone() { return bareTop("Prüfen", { html: '<a class="btn line s" href="#">Später weiter</a>' }) + strip(true, { sub: "gegen TSV Thalwil · Frage 5 von 36" }) + checkBody(true); }

/* ===================== 7.6 Szenen ===================== */
const TILES = [["7.11. Thalwil", "39:55", "Tor, Nummer 5 gelesen", "0:18"], ["7.11. Thalwil", "27:10", "Tor, Nummer nicht gelesen", "0:14"], ["7.11. Thalwil", "12:45", "Tor, Nummer 5 gelesen", "0:21"], ["7.11. Thalwil", "8:02", "Tor, Wurfposition geschätzt", "0:16"], ["31.10. Stäfa", "51:02", "Tor in Unterzahl", "0:16"], ["31.10. Stäfa", "33:40", "Tor, Nummer 11 gelesen", "0:19"], ["31.10. Stäfa", "20:15", "Tor, Nummer nicht gelesen", "0:15"], ["3.10. Rüti", "44:31", "Tor, Nummer 7 gelesen", "0:17"]];
function tiles(n, w) { return `<div class="tiles">${TILES.slice(0, n).map((t, i) => `<a class="tile" href="#"><span class="mfz"><svg data-b="saison" data-i="${i}" data-w="${w}" role="img" aria-label="Anlauf vor dem Tor ${t[1]}"></svg></span><b class="n">${t[1]}</b><span>${t[0]} · ${t[2]}</span><span class="dur">${t[3]}</span></a>`).join("")}</div>`; }
const COLLS = [["Rückzug nach Ballverlust", "5 Szenen, 1 Spielzug · geteilt am Sonntag · 17-mal geöffnet"], ["Gegner Rheinau", "6 Szenen, 1 Spielzug · noch nicht geteilt"], ["Abwehr 5:1, so wollen wir es", "11 Szenen, 6:30 · gezeigt am 3.11."]];
function collList() { return `<ul class="coll">${COLLS.map(c => `<li><h4 class="d">${c[0]}</h4><p>${c[1]}</p><a class="lnk" href="#">Öffnen</a></li>`).join("")}</ul>`; }
function searchBlock(ph) {
  return `<div class="search" role="search">${I.search}<span>Gegentore rechts aussen, letzte 3 Spiele</span></div>
    <div class="chips"><span class="on">Gegentor</span><span class="on">rechts aussen</span><span class="on">letzte 3 Spiele</span>${ph ? "" : '<button>Halbzeit</button><button>Spielerin</button><button>Abwehrsystem</button>'}</div>
    <div class="answer"><b class="n">19</b><p>von 66 Gegentoren über rechts aussen<span>29 Prozent. Gegen Thalwil waren es 9 von 18.</span></p></div>
    <div class="actrow" style="padding:18px 0 28px"><a class="btn" href="#">Alle 19 abspielen</a><a class="btn line" href="#">In eine Sammlung</a>${ph ? "" : '<a class="lnk" href="#">Als Tabelle</a>'}</div>`;
}
function szenenDesk() {
  return topD("Szenen") + kopf({ kick: "Szenen · 3 Spiele mit Video", title: "152 Szenen aus drei Spielen." })
    + `<div class="sp"><div style="min-width:0">${searchBlock(false)}<div class="hh"><b class="d">19 Szenen</b><span>neueste zuerst</span></div>${tiles(8, 200)}<p class="foot" style="margin-top:18px"><a class="lnk" href="#">11 weitere zeigen</a></p></div>
      <aside class="side"><section><div class="hh"><b class="d">Sammlungen</b><a class="lnk" href="#">Neue Sammlung</a></div>${collList()}</section>
      <section><div class="hh"><b class="d">Highlights</b><span>nach jedem Spiel</span></div><ul class="coll"><li><h4 class="d">Die Tore gegen Thalwil</h4><p>1:20 · quer und hochkant · ohne Personen ohne Einwilligung</p><a class="lnk" href="#">Teilen</a></li></ul></section></aside></div>`;
}
function szenenPhone() {
  return topP() + kopf({ kick: "Szenen · 3 Spiele mit Video", title: "152 Szenen aus drei Spielen." })
    + `<section style="padding:0 16px">${searchBlock(true)}<div class="hh"><b class="d">19 Szenen</b><span>neueste zuerst</span></div>${tiles(4, 172)}<p class="foot" style="margin-top:14px"><a class="lnk" href="#">15 weitere zeigen</a></p></section>`
    + `<section style="padding:32px 16px 28px"><div class="hh"><b class="d">Sammlungen</b><a class="lnk" href="#">Neue</a></div>${collList()}</section>` + barP("Szenen");
}

/* ===================== 7.7 Sammlung ===================== */
const FLOWS = [["38:40", "Ballverlust, Gegenstoss, Tor", "Fehlpass in der Mitte", "0:22", 0], ["41:05", "Ballverlust, Gegenstoss, Tor", "Nur zwei laufen zurück!", "0:19", 1], ["43:48", "Ballverlust, Gegenstoss, Tor", "Stürmerfoul", "0:24", 2]];
function flowList(ph) {
  const sc = (f, i) => `<li><b class="n ix">${i}</b><span class="mfz"><svg data-b="gs" data-i="${f[4]}" data-w="112" role="img" aria-label="Anlauf vor dem Tor ${f[0]}"></svg></span><div><h4>${f[0]} ${f[1]}</h4><p>${f[2]}</p></div><span class="dur">${f[3]}</span></li>`;
  return `<ol class="flow">${FLOWS.map((f, i) => sc(f, i + 1)).join("")}
    <li class="play-it"><b class="n ix">4</b><div><h4>Spielzug: Rückzug in die 5:1</h4><p>Der Vorgezogene stört den ersten Pass. So wollen wir stehen.</p></div><span class="dur">gezeichnet</span></li>
    <li class="txt"><b class="n ix">5</b><p class="note">So geht es: alle sechs zurück, 52:10, Ballgewinn und eigener Gegenstoss.</p></li></ol>`;
}
function chatPreview() {
  return `<div class="chat"><div class="bubble"><div class="og"><b class="d">Rückzug nach Ballverlust</b></div><div class="meta"><b>Rückzug nach Ballverlust</b>HC Zürichsee Herren 1 · 5 Szenen, 2:35</div><p class="msg">Schaut euch das bis Dienstag an.</p><p class="tm">21:14</p></div></div>`;
}
function sammlungDesk() {
  return topD("Szenen") + kopf({ kick: "Sammlung · aus Punkt 2 vom Samstag", title: "Rückzug nach Ballverlust", acts: '<a class="btn" href="#">Link teilen</a><a class="btn line" href="#">Am Bildschirm zeigen</a>' })
    + `<div class="sp"><section style="min-width:0"><div class="hh"><b class="d">Ablauf</b><span>5 Szenen, 1 Spielzug · 2:35</span></div><p class="note" style="margin-bottom:16px">Abwehr war stark. Ein Thema: der Rückzug.</p>${flowList(false)}<div class="addrow"><a class="btn line s" href="#">Szene dazu</a><a class="btn line s" href="#">Spielzug dazu</a><a class="btn line s" href="#">Notiz dazu</a></div></section>
      <aside class="side"><section><div class="hh"><b class="d">So kommt es im Chat an</b></div>${chatPreview()}<p class="foot">Den Text schreibst du im Chat. Wer den Link öffnet, sieht die Sammlung ohne Anmeldung. <a class="lnk" href="#">Link kopieren</a></p></section>
      <section class="opened"><div class="hh"><b class="d">Geöffnet</b></div><b class="n">17</b><p>Zuletzt heute um 12:40. Der Link gilt 30 Tage. <a class="lnk" href="#">Link sperren</a></p></section></aside></div>`;
}
function sammlungPhone() {
  return topP() + kopf({ kick: "Sammlung · aus Punkt 2", title: "Rückzug nach Ballverlust", acts: '<a class="btn" href="#">Link teilen</a><a class="btn line" href="#">Zeigen</a>' })
    + `<section style="padding:0 16px"><div class="hh"><b class="d">Ablauf</b><span>2:35</span></div>${flowList(true)}</section>`
    + `<section style="padding:32px 16px 0"><div class="hh"><b class="d">So kommt es im Chat an</b></div>${chatPreview()}</section>`
    + '<section class="opened" style="padding:32px 16px 28px"><div class="hh"><b class="d">Geöffnet</b></div><b class="n">17</b><p>Zuletzt heute um 12:40. Der Link gilt 30 Tage. <a class="lnk" href="#">Link sperren</a></p></section>' + barP("Szenen");
}

/* ===================== 7.8 the shared page ===================== */
function sharedList() { return `<ol class="flow">${FLOWS.map((f, i) => `<li${i === 1 ? ' style="background:var(--attn);margin:0 -12px;padding:14px 12px"' : ""}><b class="n ix">${i + 1}</b><span class="mfz"><svg data-b="gs" data-i="${f[4]}" data-w="112" aria-hidden="true"></svg></span><div><h4>${f[0]} ${f[1]}</h4><p${i === 1 ? ' style="color:#15171a"' : ""}>${i === 0 ? "gesehen" : i === 1 ? "läuft" : "&nbsp;"}</p></div><span class="dur"${i === 1 ? ' style="color:#15171a"' : ""}>${f[3]}</span></li>`).join("")}</ol>`; }
function sharedHead(ph) { return `<header class="ptop" style="padding:0 ${ph ? 16 : 32}px"><span class="club d"><span class="crest">HCZ</span>HC Zürichsee Herren 1</span><span class="k">${ph ? "von Sandra Frei" : "geteilt von Sandra Frei"}</span></header>`; }
function geteiltDesk() {
  return sharedHead(false) + kopf({ kick: "Sammlung · 5 Szenen, 2:35", title: "Rückzug nach Ballverlust" })
    + `<div class="sp"><div style="min-width:0"><div class="stage"><svg data-hall="ra" data-mode="video" role="img" aria-label="Video der Szene 41:05"></svg><p class="cap">41:05 · Szene 2 von 5<small>Ballverlust, Gegenstoss, Tor</small></p><div class="bar"><button class="pause" aria-pressed="false">Pause</button><div class="mode" role="group" aria-label="Ansicht"><button aria-pressed="true">Video</button><button aria-pressed="false">Taktik</button></div><span>Personen ohne Einwilligung unkenntlich</span><span class="clk">41:05</span></div></div>
      <p class="note" style="margin-top:18px">Nur zwei laufen zurück!</p><div class="actrow" style="padding:20px 0 0"><a class="btn" href="#">Nächste Szene</a><a class="btn line" href="#">Alle 5 Szenen</a></div></div>
      <aside class="side"><section><div class="hh"><b class="d">Ablauf</b><span>Abwehr war stark. Ein Thema: der Rückzug.</span></div>${sharedList()}</section><p class="foot">Nur über diesen Link sichtbar, noch 28 Tage. Kein Konto nötig.</p></aside></div>`;
}
function geteiltPhone() {
  return sharedHead(true) + kopf({ kick: "Sammlung · 5 Szenen, 2:35", title: "Rückzug nach Ballverlust" })
    + `<div class="stage"><svg data-hall="ra" data-mode="video" role="img" aria-label="Video der Szene 41:05"></svg><div class="bar"><button class="pause" aria-pressed="false">Pause</button><div class="mode" role="group" aria-label="Ansicht"><button aria-pressed="true">Video</button><button aria-pressed="false">Taktik</button></div><span class="clk">41:05</span></div><p class="cap">Szene 2 von 5<small>Ballverlust, Gegenstoss, Tor</small></p></div>`
    + `<section style="padding:18px 16px 0"><p class="note">Nur zwei laufen zurück!</p><div style="display:flex;gap:10px;margin-top:16px;flex-wrap:wrap"><a class="btn" href="#">Nächste Szene</a><a class="btn line" href="#">Alle 5</a></div></section>`
    + `<section style="padding:32px 16px 0"><div class="hh"><b class="d">Ablauf</b></div>${sharedList()}</section><p class="foot" style="padding:8px 16px 28px">Nur über diesen Link sichtbar, noch 28 Tage. Kein Konto nötig.</p>`;
}

/* ===================== 7.9 Saison ===================== */
function themeList() {
  return `<ol class="themes">${SEASON.themes.map((t, i) => `<li><h3 class="d">${t.t}</h3><p>${t.s}${t.of ? ` ${t.series.reduce((a, b) => a + b, 0)} von ${t.of.reduce((a, b) => a + b, 0)}.` : ""}</p><a class="lnk" href="#">${t.n}</a><svg data-series data-theme="${i}" role="img" aria-label="${t.t} pro Spiel: Rüti ${t.series[0]}, Stäfa ${t.series[1]}, Thalwil ${t.series[2]}"></svg><span class="lab" aria-hidden="true"><span>Rüti</span><span>Stäfa</span><span>Thalwil</span></span></li>`).join("")}</ol>`;
}
const SCORERS = [[4, "Levin Brunner", 6, 37, "6,2", ""], [10, "Elias Graf", 6, 29, "4,8", "11/13"], [11, "Jonas Schmid", 5, 21, "4,2", ""], [8, "Nico Meier", 6, 17, "2,8", ""], [7, "Luca Roth", 6, 15, "2,5", ""]];
function scorers(ph) {
  return `<table class="tb"${ph ? ' style="font-size:15px"' : ""}><thead><tr><th>Nr. Name</th>${ph ? "" : "<th>Spiele</th>"}<th>Tore</th><th>pro Spiel</th><th>7 m</th></tr></thead><tbody>${SCORERS.map(r => `<tr><td><b class="n">${r[0]}</b>${ph ? r[1].split(" ")[0] + " " + r[1].split(" ")[1][0] + "." : r[1]}</td>${ph ? "" : `<td>${r[2]}</td>`}<td>${L(r[3])}</td><td>${r[4]}</td><td>${L(r[5])}</td></tr>`).join("")}</tbody></table>`;
}
const SEASON_TITLE = { kick: "Saison 2026/27 · 3. Liga, Gruppe 2 · nach sechs Spielen", title: "Rang 2. Und rechts aussen bleibt offen." };
function saisonDesk() {
  return topD("Saison") + kopf(SEASON_TITLE)
    + `<div class="sp"><div class="col"><section><div class="hh"><b class="d">Was sich wiederholt</b><span>aus 3 Spielen mit Video</span></div>${themeList()}</section>
      <section class="diff"><div class="hh"><b class="d">Verlauf</b><span>Tordifferenz pro Spiel</span></div><svg data-diff data-w="852" role="img" aria-label="Tordifferenz pro Spiel: Rüti plus 5, Wädenswil minus 3, Horgen plus 10, Meilen plus 1, Stäfa minus 7, Thalwil plus 8"></svg><p class="foot">4 Siege, 2 Niederlagen · 148:134 Tore. Zwei Spiele ohne Video: <a class="lnk" href="#">hochladen</a></p></section>
      <section><div class="hh"><b class="d">Wer trifft</b><span>aus den Spielberichten</span></div>${scorers(false)}<p class="foot"><a class="lnk" href="#">Ganzer Kader</a></p></section></div>
      <aside class="side"><section><div class="hh"><b class="d">Rechts aussen</b><span>19 Anläufe, 3 Spiele</span></div><div class="mfz play" style="width:100%"><svg data-b="saison" data-w="340" role="img" aria-label="Alle 19 Gegentore über rechts aussen als Anläufe"></svg></div></section>
      <section><div class="hh"><b class="d">Tabelle</b><span>handball.ch, gestern</span></div>${table(5)}</section>
      <section><div class="hh"><b class="d">Gegner</b></div><ul class="facts"><li><span>HSG Rheinau, Sonntag</span><a class="lnk" href="#">12 Szenen</a></li><li><span>TV Talwiese, 22.11.</span><span class="k">noch kein Spiel</span></li><li><span>BSV Stäfa, 29.11.</span><a class="lnk" href="#">33 Szenen</a></li></ul></section></aside></div>`;
}
function saisonPhone() {
  return topP() + kopf(SEASON_TITLE)
    + `<section style="padding:0 16px"><div class="hh"><b class="d">Was sich wiederholt</b><span>3 Spiele mit Video</span></div>${themeList()}</section>`
    + '<section class="diff" style="padding:32px 16px 0"><div class="hh"><b class="d">Verlauf</b><span>pro Spiel</span></div><svg data-diff data-w="358" role="img" aria-label="Tordifferenz pro Spiel"></svg><p class="foot">4 Siege, 2 Niederlagen · 148:134 Tore</p></section>'
    + `<section style="padding:32px 16px 28px"><div class="hh"><b class="d">Wer trifft</b></div>${scorers(true)}</section>` + barP("Saison");
}

/* ===================== 7.10 Team ===================== */
const SQUAD = [
  ["Tor", [[1, "Mia Meier", "TW", "38 % Paraden, markiert"], [9, "Jan Bühler", "TW", "", "Einwilligung fehlt"]]],
  ["Rückraum", [[4, "Levin Brunner", "RL", "37 Tore"], [5, "Ben Zürcher", "RM", "9 Tore"], [6, "Rafael Brunner", "RR", "8 Tore"], [10, "Elias Graf", "RL", "29 Tore"], [11, "Jonas Schmid", "RM", "", "Einwilligung fehlt"], [12, "Lara Moser", "RR", "6 Tore"]]],
  ["Flügel und Kreis", [[3, "Tim Huber", "LA", "11 Tore"], [7, "Luca Roth", "RA", "15 Tore"], [13, "Jana Baumann", "LA", "7 Tore"], [8, "Nico Meier", "KM", "17 Tore"], [15, "Jan Steiner", "KM", "5 Tore"], [null, "Sara Steiner", "RA", "", "Nummer fehlt"]]]
];
function squad() {
  return `<div class="squad">${SQUAD.map(g => `<section><p class="grp-h d">${g[0]} <span>${g[1].length}</span></p>${g[1].map(p => `<div class="pl"><b class="n${p[0] == null ? " miss" : ""}">${p[0] == null ? "?" : p[0]}</b><h4 class="d">${p[1]}</h4><p>${p[4] ? `<span class="tag">${p[4]}</span>` : p[3]}</p><span class="pos">${p[2]}</span></div>`).join("")}</section>`).join("")}</div>`;
}
function teamSide() {
  return `<section class="consent"><div class="hh"><b class="d">Einwilligungen</b></div><b class="n">12 <small>von 14</small></b><p class="foot" style="font-size:16px;color:var(--ink)">Ein Link für den Teamchat. Jede Person bestätigt für sich, ohne Konto. Ohne Einwilligung bleibt sie im Video unkenntlich.</p><a class="btn" href="#" style="margin-top:14px">Link kopieren</a></section>
    <section><div class="hh"><b class="d">Trainerbank</b></div><ul class="bench"><li><b>Sandra Frei</b><span>Trainerin</span></li><li><b>Marco Keller</b><span>Assistent</span></li></ul><p style="margin-top:12px"><a class="lnk" href="#">Jemand fürs Filmen oder Prüfen einladen</a></p></section>`;
}
const TEAM_TITLE = { kick: "Herren 1 · Kader von handball.ch, abgeglichen gestern", title: "14 im Kader. Bei dreien fehlt noch etwas." };
function teamDesk() { return topD("Team") + kopf(TEAM_TITLE) + `<div class="sp" style="gap:64px"><div style="min-width:0">${squad()}</div><aside class="side" style="gap:40px">${teamSide()}</aside></div>`; }
function teamPhone() { return topP() + kopf(TEAM_TITLE) + `<div style="padding:0 16px">${squad()}</div><div class="side" style="padding:32px 16px 28px;gap:36px">${teamSide()}</div>` + barP("Team"); }

/* ===================== 7.11 Spieltag ===================== */
function mkeys() {
  return `<div class="mkeys"><button class="us"><b class="d">Tor wir</b><span>14 bisher</span></button><button class="them"><b class="d">Tor Thalwil</b><span>11 bisher</span></button>
    <button><b class="d">Gute Aktion</b><span>merken</span></button><button><b class="d">Fehler</b><span>merken</span></button>
    <button><b class="d">Abwehr anschauen</b><span>später im Video</span></button><button><b class="d">Später anschauen</b><span>später im Video</span></button></div>
    <div class="mrow"><div class="mkeys" style="display:contents"><button class="small">2 Minuten</button><button class="small">Time-out</button><button class="small">Halbzeit</button></div></div>`;
}
const LOG = [["23:12", "Tor wir", "us"], ["22:40", "Tor Thalwil", "them"], ["21:05", "Abwehr anschauen", ""], ["19:48", "Tor wir", "us"], ["18:30", "2 Minuten gegen Thalwil", ""]];
function liveStrip(ph) { return `<section class="strip live"><div class="nm d">HC Zürichsee<small>gegen TSV Thalwil · Halle Seefeld</small><span class="clock"><b>23:41</b>1. Halbzeit, Uhr läuft</span></div><div class="score n" role="img" aria-label="14 zu 11"><span class="e" aria-hidden="true">14:11</span><span>14:<u>11</u></span></div></section>`; }
function spieltagPhone() {
  return bareTop("Spieltag", { html: '<a class="btn line s" href="#">Beenden</a>' }) + liveStrip(true)
    + `<section style="padding:16px 16px 0">${mkeys()}<div class="last"><b class="n">23:12</b><span>Tor wir</span><a class="lnk" href="#">zurücknehmen</a><a class="lnk" href="#" style="margin-left:auto">Pro Spielerin erfassen</a></div></section>`
    + '<p class="foot" style="padding:0 16px 28px">Du coachst selbst? Gib den Link jemandem auf der Bank. <a class="lnk" href="#">Link teilen</a></p>';
}
function spieltagDesk() {
  return bareTop("Spieltag · funktioniert auch ohne Netz", { desk: 1, html: '<a class="btn line" href="#">Beenden</a>' }) + liveStrip(false)
    + `<div class="sp" style="grid-template-columns:minmax(0,1fr) 380px"><section style="min-width:0">${mkeys()}<div class="last"><b class="n">23:12</b><span>Tor wir</span><a class="lnk" href="#">zurücknehmen</a><a class="lnk" href="#" style="margin-left:auto">Pro Spielerin erfassen</a></div></section>
      <aside class="side"><section><div class="hh"><b class="d">Bisher</b><span>neueste zuerst</span></div><ul class="log">${LOG.map(l => `<li><b class="n">${l[0]}</b><span>${l[2] ? `<i style="background:var(--${l[2] === "us" ? "club" : "opp"});box-shadow:inset 0 0 0 1px var(--${l[2] === "us" ? "club" : "opp"}-edge)"></i>` : ""}${l[1]}</span><a class="lnk" href="#">ändern</a></li>`).join("")}</ul></section>
      <p class="foot">Du coachst selbst? Gib den Link jemandem auf der Bank, ohne Konto. <a class="lnk" href="#">Link teilen</a></p></aside></div>`;
}

/* ===================== 7.12 Einstieg ===================== */
const SWATCH = [["blau", "#1f4fd6"], ["rot", "#d3202e"], ["gelb", "#f6c500"], ["schwarz", "#17191c"], ["weiss", "#ffffff"], ["gruen", "#12804a"], ["orange", "#e2731c"], ["violett", "#5b2d8e"]];
function found() {
  return `<div class="found"><p class="k">Von handball.ch</p><h3 class="d">HC Zürichsee Herren 1</h3><p class="sub">3. Liga, Gruppe 2 · Halle Seefeld</p><ul>${["14 Spielerinnen und Spieler, mit Nummern", "22 Spiele im Spielplan, 6 gespielt", "Tabelle: Rang 2"].map(t => `<li>${I.ok}${t}</li>`).join("")}</ul></div>`;
}
function swatches() { return `<div class="hh" style="margin-top:32px"><b class="d">Welche Farbe hat euer Trikot?</b></div><div class="swatches" role="group" aria-label="Trikotfarbe">${SWATCH.map(s => `<button data-club-pick="${s[0]}" aria-label="${s[0]}" aria-pressed="false"><i style="background:${s[1]}"></i></button>`).join("")}</div><p class="foot">Das Wappen könnt ihr später hochladen.</p>`; }
function einstiegPreview(ph) {
  return `<div class="preview"><p class="k" style="margin-bottom:8px">So sieht euer letztes Spiel aus</p><section class="wurf big"><div><p class="kick">Samstag gegen TSV Thalwil</p><h1 class="d">Gewonnen.</h1></div><div><div class="score n" aria-hidden="true">${scoreHTML(26, 18)}</div></div></section>
    <div style="margin-top:12px">${[[4, "Levin Brunner", "RL", "6 Spiele"], [10, "Elias Graf", "RL", "6 Spiele"]].map(p => `<div class="pl"><b class="n">${p[0]}</b><h4 class="d">${p[1]}</h4><p>${p[3]}</p><span class="pos">${p[2]}</span></div>`).join("")}</div></div>`;
}
const EIN = { kick: "Schritt 2 von 2", title: "Das seid ihr, oder?" };
function einstiegDesk() {
  return bareTop("Handball AI · Einstieg", { desk: 1, html: '<a class="lnk" href="#">Abbrechen</a>' }) + kopf(EIN)
    + `<div class="sp" style="grid-template-columns:minmax(0,1fr) 460px;gap:64px"><section>${found()}${swatches()}<div class="actrow" style="padding:28px 0 0"><a class="btn" href="#">Stimmt, weiter</a><a class="btn line" href="#">Das ist nicht mein Team</a></div><p class="foot" style="margin-top:18px">Als Nächstes: das erste Video hochladen oder das Demo-Spiel ansehen.</p></section>
      <aside>${einstiegPreview(false)}</aside></div>`;
}
function einstiegPhone() {
  return bareTop("Einstieg", { html: '<a class="lnk" href="#" style="font-size:15px">Abbrechen</a>' }) + kopf(EIN)
    + `<section style="padding:0 16px">${found()}${swatches()}</section><section style="padding:28px 16px 0">${einstiegPreview(true)}</section>`
    + '<div class="actrow" style="flex-direction:column;align-items:stretch;padding-bottom:28px"><a class="btn" href="#">Stimmt, weiter</a><a class="btn line" href="#">Das ist nicht mein Team</a></div>';
}

/* ===================== 7.13 states ===================== */
function stateNoVideo() {
  return topP() + `<section class="wurf big" style="height:340px"><div><p class="kick">Samstag, 17. Oktober · auswärts</p><h1 class="d" style="font-size:28px">HC Zürichsee bei SG Horgen</h1></div><div><div class="score n" style="font-size:88px;margin-top:4px" role="img" aria-label="29 zu 19">${scoreHTML(29, 19)}</div></div><svg class="fl" data-fl data-flow="horgen" data-w="390" data-h="56" style="bottom:26px" role="img" aria-label="Verlauf aus dem Spielbericht: von Anfang an vorn, am Schluss plus 10"></svg></section>`
    + tabs("Spiel", true) + '<p class="src">Quelle: Spielbericht von handball.ch. Der Verlauf kommt aus der Torfolge.</p>'
    + '<div class="state"><div style="display:grid;grid-template-columns:120px minmax(0,1fr);gap:14px;align-items:center"><span class="mfz" style="width:120px"><svg data-empty data-w="120" aria-hidden="true"></svg><em>kein Video</em></span><p>Lad das Video hoch. Nach etwa 40 Minuten bekommst du die drei Dinge und alle Szenen.</p></div><div class="btns"><a class="btn" href="#">Video wählen</a><a class="btn line" href="#">Link einfügen</a></div></div>'
    + '<section style="padding:28px 16px"><div class="hh"><b class="d">Telegramm</b><a class="lnk" href="#">Kopieren</a></div><p class="telegramm" style="font-size:15px"><b>SG Horgen gegen HC Zürichsee 19:29 (8:14).</b> Torfolge: 1:2, 4:5, 6:9, 8:14; 11:18, 14:22, 16:26, 19:29. Beste Werfer: Brunner 8, Graf 6/3. Im Tor: Meier.</p></section>' + barP("Spiele");
}
function stateRunning() {
  return topP() + headStart(true, 390, { kick: "Sa gegen TSV Thalwil · Spielbericht ist da", title: "Die Analyse läuft." })
    + '<section style="padding:24px 16px 0"><div class="hh"><b class="d">Noch etwa 25 Minuten</b></div><div class="pbar" style="max-width:none;height:8px;margin:0 0 12px"><i style="width:55%"></i></div>'
    + '<ol class="steps"><li class="done"><span>fertig</span>Video geladen, 58 Minuten</li><li class="done"><span>fertig</span>Spielfeld erkannt</li><li class="now"><span>läuft</span>Spielerinnen und Spieler verfolgen</li><li class="next"><span>danach</span>Szenen schneiden</li><li class="next"><span>danach</span>Drei Dinge schreiben</li></ol>'
    + '<p style="margin-top:14px;font-size:16px">Du bekommst eine Mitteilung. In der Zwischenzeit: <a class="lnk" href="#">Kader bestätigen</a>, das macht die Zahlen genauer.</p></section>'
    + `<section style="padding:28px 16px 28px"><div class="hh"><b class="d">Drei Dinge</b><span>nach der Analyse</span></div><div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px">${[1, 2, 3].map(() => '<span class="mfz" style="width:100%"><svg data-empty data-w="110" aria-hidden="true"></svg></span>').join("")}</div></section>` + barP("Spiele");
}
function stateField() {
  return topP() + strip(true) + tabs("Video")
    + '<div class="stage" style="margin-top:12px"><svg data-hall="ra" data-mode="check" role="img" aria-label="Videobild mit erkanntem Spielfeld, die vier Ecken sind markiert"></svg><p class="cap">Stimmt das Feld?<small>Die Taktikkamera braucht die Ecken.</small></p></div>'
    + '<section style="padding:18px 16px 28px"><p style="font-size:16px">Wir haben die gelben Linien als Spielfeld erkannt. Erst wenn sie stimmen, rechnen wir die Positionen in Meter um und zeigen die Taktikkamera.</p><div style="display:flex;gap:10px;margin-top:14px;flex-wrap:wrap"><a class="btn" href="#">Ja, stimmt</a><a class="btn line" href="#">Ecken verschieben</a></div><p class="k" style="margin-top:12px">Bis dahin zeigt das Video nur das Video, ohne Wege und Positionen.</p></section>' + barP("Spiele");
}
function stateEmpty() {
  return topP() + kopf({ kick: "Szenen", title: "Noch keine Szenen." })
    + '<section class="over" style="padding:0 16px 28px"><div class="ghost" aria-hidden="true"><div class="search">' + I.search + '<span>Gegentore rechts aussen</span></div><div style="height:20px"></div>' + tiles(4, 172) + '</div>'
    + '<div class="msg"><h3 class="d">Hier landen eure Szenen.</h3><p>Sobald das erste Spiel analysiert ist, kannst du sie suchen, sammeln und dem Team zeigen.</p><div style="display:flex;gap:10px;margin-top:14px;flex-wrap:wrap"><a class="btn" href="#">Video hochladen</a><a class="btn line" href="#">Demo-Spiel ansehen</a></div></div></section>' + barP("Szenen");
}
function stateError() {
  return topP() + headStart(true, 390, { kick: "Sa gegen TSV Thalwil · Spielbericht ist da", title: "Gestern war Spiel." })
    + '<section style="padding:24px 16px 0"><div class="err">' + I.err + '<div><h3 class="d">Der Upload ist abgebrochen.</h3><p>Bei 64 Prozent ist die Verbindung abgerissen. Was schon oben ist, bleibt: du machst dort weiter, wo es aufgehört hat.</p></div></div>'
    + '<div style="display:flex;gap:10px;margin-top:16px;flex-wrap:wrap"><a class="btn" href="#">Weiter hochladen</a><a class="btn line" href="#">Andere Datei wählen</a></div><p class="k" style="margin-top:12px">Am besten im WLAN. Der Upload läuft weiter, wenn du die App schliesst.</p></section>'
    + `<section style="padding:32px 16px 28px"><div class="hh"><b class="d">Alle Spiele</b></div>${gameList(true)}</section>` + barP("Spiele");
}

/* the list of frames: id, title, note, form, function, options for the frame */
const SCREENS = [
  ["start", "Spiele, der Start", "7.1 · Wurf-Kopf mit dem Resultat, die drei Dinge mit ihren Anläufen, Punkt 1 schaltet auf die Taktikkamera", startDesk, startPhone],
  ["spiel", "Spiel", "7.2 · Tab «Spiel», Punkt 1 geöffnet, darunter die Ball-Linie", spielDesk, spielPhone],
  ["video", "Video", "7.3 · Taktikkamera als Bühne; der Ball sitzt bei der Spielerin, nur wo er erkannt wurde", videoDesk, videoPhone],
  ["zahlen", "Zahlen", "7.4 · ruhig, aufrecht, viel Luft", zahlenDesk, zahlenPhone],
  ["pruefen", "Prüfen", "7.5 · Vollbild mit Streifen, grosse Tasten", pruefenDesk, pruefenPhone],
  ["szenen", "Szenen", "7.6 · Seitenkopf statt Wurf; jede Szene als ihr eigener Anlauf", szenenDesk, szenenPhone],
  ["sammlung", "Sammlung", "7.7 · Ablauf, Vorschau im Chat, wie oft geöffnet", sammlungDesk, sammlungPhone],
  ["geteilt", "Geteilte Seite", "7.8 · ohne Navigation, ohne Anmeldung", geteiltDesk, geteiltPhone],
  ["saison", "Saison", "7.9 · was sich wiederholt, aus wie vielen Spielen", saisonDesk, saisonPhone],
  ["team", "Team", "7.10 · Kader nach Position, was fehlt in Gelb und als Wort", teamDesk, teamPhone],
  ["spieltag", "Spieltag", "7.11 · Vollbild, grosse Tasten, die Uhr im Streifen", spieltagDesk, spieltagPhone],
  ["einstieg", "Einstieg", "7.12 · die Trikotfarbe färbt die Vorschau sofort", einstiegDesk, einstiegPhone]
];
const STATES = [
  ["zustand-ohne-video", "Kein Video", stateNoVideo],
  ["zustand-analyse", "Analyse läuft", stateRunning],
  ["zustand-feld", "Feld nicht bestätigt", stateField],
  ["zustand-gegner", "Gegnerfarbe unbekannt", () => startPhone({ unknown: true }), { opp: null }],
  ["zustand-ball", "Ball nicht erkannt", () => videoPhone({ cam: "kr" })],
  ["zustand-leer", "Leer", stateEmpty],
  ["zustand-fehler", "Fehler", stateError]
];
