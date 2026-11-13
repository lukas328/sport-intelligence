# UX-Test Runde 2: neue Befunde

Stand: 13. November 2026. App `claude/trikot-ui` (465efb4), Website `claude/site-anlauf` (ad87ce5).
Aufbau wie in `NACHPRUEFUNG.md`. Gewichte wie in Runde 1: **P1** blockiert eine Aufgabe oder
verliert Daten, **P2** verwirrt, kostet Zeit oder zeigt, was die Daten nicht hergeben, **P3**
Schliff. Die alten Befunde und ihr Stand stehen in `NACHPRUEFUNG.md`.

Lieferung 1: Teil 1 (Nachprüfung) und Teil 2 (erster Eindruck als Hans). Teil 3 (neues Suchen in
allen Aufgaben und auf der Website) folgt als Nachtrag in dieser Datei.

---

## Zusammenfassung

### Was jetzt gut ist

- **Der Weg von aussen trägt.** Hans tippt auf der Website eine Trikotfarbe und seinen Teamnamen,
  landet mit beidem im Einstieg der App, sieht sein Team mit Rang, Serie und letztem Resultat in
  seinen Farben, **bevor** er ein Konto hat, und speichert mit einer E-Mail-Adresse. Kein Passwort,
  kein Häkchen, nichts wird doppelt gefragt.
- **Nutzen vor dem ersten Video**: Der Start zeigt Rang, Tabelle, Torschützen aus den Spielberichten
  und den nächsten Gegner. Kein Zwei-Faktor-Banner, kein Alarm im Team.
- **Die Kernwege von Runde 1 funktionieren**: Szenen zu Punkt 1 als Folge, Suchen mit einer Frage,
  Sammlung bearbeiten und am Bildschirm zeigen, Spieltag behält die Einträge, Prüfen mit
  verschiebbaren Feldecken, geteilte Seite mit «Feld von oben».
- **Ehrlichkeit**: keine erfundenen Läufe mehr, keine Positionen ohne bestätigtes Feld, kein xG,
  keine «40 Minuten». Testphase beim neuen Verein sichtbar, erstes Video wird analysiert, Mail
  kommt.
- **Lesbarkeit**: auf Einstieg, Start und Spiel praktisch nichts mehr unter 14 px.

### Die fünf wichtigsten verbleibenden Probleme

1. **Nach dem ersten eigenen Video sieht Hans das alte Werkzeug** (N04, P2): Tab Video mit
   Unter-Tabs «Ereignisse · Abwehrsysteme», «Ereignis erfassen», «Tastenkürzel», «Anwurf setzen»;
   die Mail «Die drei Dinge … sind da» führt auf ein Spiel ohne drei Dinge (N05).
2. **Spieltag ohne Netz** (N01, P1; N02, P2): Der neue Spieltag registriert keinen Offline-Speicher
   mehr; wird die Seite in der Halle ohne Netz neu geladen, kommt die Fehlerseite des Browsers. Ein
   offline erfasster Eintrag erscheint danach doppelt.
3. **16 Sekunden «…»** beim Antippen des eigenen Teams im Einstieg (N03, P2), dem Moment, in dem
   Hans entscheidet, ob er bleibt.
4. **Was hinter «Mehr» liegt, ist noch das alte Produkt** (B08 teilweise): zweite Drei-Dinge-Liste
   mit «Daran arbeiten», «Ballbesitz im Spielverlauf», «Alle Angriffe», Feedback. Dazu falsche oder
   leere Zahlen: Wurfquote 85 % bei 17 aus 21 (N12), Spalte «Bestätigt» leer bei «42 von 44
   bestätigt».
5. **Kleine Brüche im ersten Eindruck**: Filmanleitung zeigt auf eine Adresse, die die Website
   nicht hat (N06), «Suchen» fehlt am Handy (N08), grosse Schrift schneidet Vereinsnamen und
   E-Mail ab (N11), geteilte Minifelder unlesbar (N07), Anmeldelink nur 15 Minuten gültig (N15).

### Urteil zum ersten Eindruck

Hans versteht auf der Website in zehn Sekunden, worum es geht, und sieht nach etwa einer Minute
und ohne Konto Zahlen über sein eigenes Team: Das ist der grösste Fortschritt seit Runde 1. Er
verliert ihn an zwei Stellen wieder, beim stummen Warten auf sein Team und nach dem ersten Video,
wenn die Mail drei Dinge verspricht und die App ihm stattdessen ein Erfassungswerkzeug zeigt. Wer
diese beiden Stellen schliesst, hat einen Einstieg, den ein skeptischer Trainer durchhält.

### Zahlen

| Gewicht | Neue Befunde (Lieferung 1) |
|---|---|
| P1 | 1 |
| P2 | 16 |
| P3 | 9 |
| **Total** | **26** |

Nachprüfung (Details `NACHPRUEFUNG.md`): 50 bestätigt behoben, 21 teilweise, 0 offen, 1 neu kaputt,
4 nicht geprüft.

---

## Teil 2: Der erste Eindruck, als Hans, ganz von aussen

Gemessen am Handy mit grosser Schrift (390 px bei 130 %, als 300 CSS-Pixel), neues Konto, echter
Verein aus handball.ch (SG Wädenswil/Horgen). Bilder: `shots/e01-hans-website-bis-postfach.jpg`,
`shots/e02-hans-spiele-bis-mail.jpg`.

| # | Screen | Wörter | Felder | Entscheidungen | Warten ohne Satz | Text < 14 px |
|---|---|---|---|---|---|---|
| 1 | Website: Kopf, Farbwahl, «Wie heisst dein Team?» | 520 (ganze Seite; zum Handeln nötig rund 60) | 1 (+ Farbe, ein Tipp) | 1 (Farbe, freiwillig) | – | 0 |
| 2 | App `/einstieg`: Treffer, Suche schon ausgeführt | 160 | 1 (vorbefüllt) | 1 (welches Team) | 7,8 s Seitenwechsel und Suche | 0 |
| 3 | «Dein Team, sofort»: Kopf in Rot, «Rang 4. 4 Siege in Folge.», Trikot vorgewählt, Tabelle | 115 | 0 | 1 («Das ist mein Team. Speichern») | **16,1 s, nur «…»** | 0 |
| 4 | «Wohin dürfen wir den Link schicken?» | 39 | 1 (E-Mail) | 0 | – | 0 |
| 5 | «Schau in dein Postfach.» | 20 | 0 | 0 | – | 0 |
| – | Mail «Dein Anmeldelink», Link antippen | 45 | 0 | 0 | 4,3 s bis Spiele | – |
| 6 | Spiele: «Das letzte Spiel, noch ohne Video.», Rang, Tabelle, Torschützen, nächster Gegner | 269 | 0 | 1 («Video hochladen») | – | 0 |

| | Runde 1 | Bau-Session (Ablaufbogen) | Runde 2, gemessen |
|---|---|---|---|
| Screens bis zur App | 6 | 4 | 5 in der App (Treffer, Team, E-Mail, Postfach, Spiele) plus Website |
| Felder | 6 | 2 + Farbe | 2 (Team, E-Mail) + Farbe mit einem Tipp |
| Entscheidungen | 5 | 2 | 2 bis 3 (Team, Speichern, Farbe freiwillig) |
| Wörter bis zur App | rund 500 | 395 | 334 in der App (Website zusätzlich, aber freiwillig) |
| Warten ohne Satz | 13 s | 0 | **16 s** (N03) |
| Text unter 14 px | 24 auf dem Start | 0 | 0 auf allen sechs Screens |
| Erster Nutzen | Saison, hinter einem Reiter | Screen 2 | **Screen 3, vor dem Konto**: Rang, Serie, letztes Resultat |
| Zeit für Hans (Schätzung) | 4 bis 5 min, ohne Nutzen | – | rund 3 min bis Spiele, Nutzen nach rund 1 min |

**Ausdrücklich geprüft:**

| Punkt | Ergebnis |
|---|---|
| Versteht er in zehn Sekunden, was es ist? | Ja: «Dein Spiel. Und drei Dinge zum Mitnehmen.» und darunter ein Satz; das Feld «Wie heisst dein Team?» steht im ersten Bild. |
| q, farbe, lang kommen an | Ja (`/einstieg?q=Wädenswil&farbe=rot`, Sprache als Cookie). |
| Neuer Verein in der Testphase, erstes Video analysiert | Ja: «Team · Testphase bis 13.12.2026»; das Testvideo lief durch, Mail nach 13 s. |
| Kein Zwei-Faktor-Banner beim ersten Besuch | Ja. |
| Team ohne Alarm | Vor dem ersten Video ja; danach «Bei 20 fehlt noch etwas» mit 20 gelben Aufnähern. |
| Nichts doppelt gefragt oder erklärt | Ja für Team und Farbe. Der nächste Gegner steht auf dem Start zweimal (B40). |
| Filmanleitung der Website aus dem Upload erreichbar | Link da, Ziel `https://handball-ai.ch/aufnahme/` gibt es auf der Website nicht (N06). |
| Wörter der Liste aus H10 | Grossteils weg; geblieben siehe NACHPRUEFUNG H10. |
| «Analyse läuft» | «Die Analyse läuft.», drei Schritte, «Du kannst die Seite schliessen» rund 4 s sichtbar. |
| Mail «Die drei Dinge … sind da» | Kam, auch ohne gefundene drei Dinge (N05). |

**Ränder des neuen Einstiegs:**

| Fall | Ergebnis |
|---|---|
| Team nicht beim Verband | «Kein Team gefunden für «Xyzabc Handball».» und «Dein Team ist nicht dabei? Mit dem Teamnamen weiter» › Teamname › E-Mail. Gut. |
| Tippfehler («Wädenswill», «Thalwill») | «Kein Team gefunden», keine Vorschläge (N10). |
| Team schon von jemand anderem belegt | Vorschau und «Das ist mein Team. Speichern» wie für einen freien Verein; erst nach Mail und Link «Anfrage gesendet. Die Leute im Verein melden sich in der App.» ohne Knopf weiter (N09). |
| Link abgelaufen oder ungültig | «Der Link ist ungültig oder abgelaufen.» mit «Anmelden»; die Teamwahl ist weg, man beginnt von vorn (N22). |
| Link am anderen Gerät | funktioniert (Team und Farbe stehen im Link). |
| Link zweimal geöffnet | zweites Mal «ungültig oder abgelaufen», obwohl man schon angemeldet ist (N22). |
| Zweimal speichern mit derselben Adresse | legt einen zweiten Verein an und wechselt hinein, ohne Hinweis (N21). |
| Viele Suchen schnell | nach 20 Anfragen HTTP 429; die Seite sagt «handball.ch antwortet gerade nicht …» (N19). |

---

## Befunde

### P1

**N01 · Spieltag lässt sich ohne Netz nicht wieder öffnen**
- Route: `{m}/matchday`. Gerät: Handy.
- Nachstellen: Spieltag öffnen (10 s warten), Netz aus, Seite neu laden (oder Handy sperren, der
  Browser lädt neu).
- Erwartet: Spieltag mit den bisherigen Einträgen («funktioniert auch ohne Netz» steht oben).
- Passiert: Browser-Fehlerseite `ERR_INTERNET_DISCONNECTED`. Es ist kein Service Worker registriert
  (`navigator.serviceWorker.getRegistrations()` leer); die Registrierung steht nur noch in der alten
  Detail-Erfassung (`live/live-view.tsx`), nicht im neuen Spieltag. In Runde 1 (alte Erfassung) ging
  das.
- Screenshot: `shots/n01-spieltag-offline.jpg`
- Vorschlag: `/sw.js` auch im neuen Spieltag registrieren; e2e: öffnen, offline, neu laden,
  Einträge da.

### P2

**N02 · Offline erfasster Eintrag erscheint doppelt**
- Route: `{m}/matchday`. Gerät: Handy.
- Nachstellen: online «Tor wir», «Tor Gegner»; Netz aus, «Gute Aktion»; Netz an, neu laden.
- Erwartet: ein «Gute Aktion».
- Passiert: «Gute Aktion» zweimal in «Bisher» (beim nächsten Öffnen wieder zweimal, also auf dem
  Server). Wer in der Halle schlechtes Netz hat, bekommt doppelte Szenen.
- Screenshot: `shots/v22-spieltag.jpg` (Spieltag), Ablauf im Text
- Vorschlag: Einträge mit einer Kennung vom Gerät senden und auf dem Server nicht doppelt anlegen.

**N03 · Einstieg: 16 Sekunden nur «…»**
- Route: `/einstieg?q=…` › Team antippen. Gerät: Handy.
- Erwartet: sofort ein Satz, was passiert («Wir holen Spiele, Tabelle und Kader von handball.ch»).
- Passiert: Leere Seite mit «…» und den Sprachen, 16,1 s (SG Wädenswil/Horgen). Die Bau-Session
  misst «0 s ohne Satz»; das stimmt nur, wenn die Daten schon im Zwischenspeicher liegen.
- Screenshot: `shots/n03-einstieg-warten.jpg`
- Vorschlag: den Satz aus dem alten «Übernehmen» hier zeigen; Kopf mit Name und Farbe sofort
  zeichnen (beides ist aus der Trefferliste bekannt), Zahlen nachladen.

**N04 · Nach dem ersten eigenen Video zeigt der Tab Video die alte Erfassung**
- Route: `{m}?tab=video` eines neu analysierten Spiels. Gerät: Handy (grosse Schrift).
- Nachstellen: Hans' Weg bis «Video hochladen», Datei wählen, warten bis fertig.
- Erwartet: Bühne mit Video, offene Fragen in Prüfen (SPEC 7.3).
- Passiert: «Analyse fertig. Statistik und Szenen stehen bereit.», darunter Unter-Tabs «Ereignisse ·
  Abwehrsysteme · Ko…», der Link «Einrichten von Hand: Feld, Anwurf, Tore, Personen», ein leerer
  Bereich, «Spieler/in · ohne Spieler», «Ereignis erfassen» mit Tor, Parade, Fehlwurf, Pfosten,
  «Wurfposition und Torecke», «Torhüter und Import», «Tastenkürzel», «Ohne Anwurf liegt das Video
  noch nicht auf der Spielzeit. Anwurf setzen». Das Video klebt über dem Inhalt.
- Screenshot: `shots/n04-tab-video-nach-erstem-video.jpg`
- Vorschlag: die alte Werkbank nur nach «Einrichten von Hand» zeigen; ohne Ergebnisse die Bühne mit
  dem Video und einem Satz «Noch keine Tore gefunden. Prüfen hilft» und dem Link auf Prüfen.

**N05 · Mail «Die drei Dinge … sind da», das Spiel hat keine drei Dinge**
- Route: Mail, `{m}`. Gerät: Handy.
- Passiert: Mail «Die drei Dinge gegen TSV Fortitudo Gossau 2 sind da … Die drei Dinge und die
  Szenen warten». Tab Spiel zeigt nur Kopf, Telegramm und «Mehr zum Spiel»; der Start titelt
  «Gewonnen.» ohne Rest. (Testvideo ohne Tore; bei echten Videos kann es ebenso vorkommen.)
- Screenshot: `shots/n05-spiel-ohne-drei-dinge.jpg`
- Vorschlag: Mail und Start nach dem Ergebnis formulieren («Die Analyse ist fertig. Wir haben keine
  Tore erkannt. Prüfen dauert zwei Minuten.»).

**N06 · «Ausführliche Filmanleitung» zeigt auf eine Seite, die es nicht gibt**
- Route: Upload-Block. Gerät: beide.
- Passiert: Link auf `https://handball-ai.ch/aufnahme/`. Die neue Website liefert die Seite unter
  `/de/aufnahme/` (geprüft lokal: `/aufnahme/` 404, `/de/aufnahme/` 200; es ist ein statischer
  Export ohne Weiterleitungen). Ob das Hosting `/aufnahme/` umleitet, kann ich nicht prüfen.
- Vorschlag: Link mit Sprache (`/de/aufnahme/`, `/fr/…`) bauen, oder auf der Website eine
  Weiterleitung anlegen und testen.

**N07 · Geteilte Seite: Minifelder in der Liste unlesbar**
- Route: `/s/<token>`. Gerät: Handy (auch Desktop).
- Passiert: Jede Zeile zeigt eine blaue Fläche mit schwarzen Bögen; die Spielerpunkte sind offenbar
  im Massstab des grossen Felds gezeichnet und füllen das kleine Feld.
- Screenshot: `shots/n07-geteilt-minifelder.jpg`
- Vorschlag: Punkte und Linien im Minifeld in eigenem Massstab; Test mit einem Bildvergleich.

**N08 · Am Handy fehlt «Suchen» in der Kopfzeile**
- Route: alle App-Seiten. Gerät: Handy.
- Passiert: Kopfzeile: Wappen, Team, Glocke, «+ Video», Konto. Die Lupe von Runde 1 ist weg; Suchen
  geht nur noch über den Reiter Szenen (SPEC 6: Suche in der Handy-Kopfzeile).
- Screenshot: `shots/vh02-start-echter-verein.jpg` (Kopfzeile)
- Vorschlag: Lupe mit Wort «Suchen» zurück, notfalls ins Kontomenü.

**N09 · Team schon belegt: kein Hinweis vorher, Sackgasse danach**
- Route: `/einstieg` › belegtes Team › Speichern › Link. Gerät: Handy.
- Passiert: Vorschau und «Das ist mein Team. Speichern» wie bei einem freien Team; erst nach Mail und
  Link: «Anfrage gesendet. Die Leute im Verein melden sich in der App.», kein Knopf, kein Weg in die
  App, kein Name, wer gefragt wurde.
- Screenshot: `shots/n09-team-belegt.jpg`
- Vorschlag: Schon in der Vorschau «Dieses Team nutzt Handball Intelligence schon. Speichern
  schickt eine Anfrage an …»; danach eine Seite mit «Zur App» und dem Stand der Anfrage.

**N10 · Tippfehler finden nichts**
- Route: `/einstieg`. Gerät: beide.
- Passiert: «Wädenswill» und «Thalwill» ergeben «Kein Team gefunden». Hans tippt am Handy mit
  grosser Schrift oft daneben.
- Screenshot: `shots/n10-tippfehler.jpg`
- Vorschlag: unscharfe Suche (ein Zeichen Abstand) oder «Meintest du Wädenswil?».

**N11 · Grosse Schrift: Namen und E-Mail laufen aus dem Bild, Name überlappt Resultat**
- Route: `/einstieg` (Team, Postfach), `{m}` (Kopf und Streifen). Gerät: Handy 130 %.
- Passiert: «SG Wädenswil/Horgen» endet ausserhalb des Kopfs («…/Horge»); im Streifen des Tabs Video
  überlappt der Name das Resultat «28:26»; im Postfach-Satz ist die E-Mail rechts abgeschnitten.
- Screenshot: `shots/n11-grosse-schrift-team.jpg`, `shots/n11b-grosse-schrift-postfach.jpg`,
  `shots/n04-tab-video-nach-erstem-video.jpg`
- Vorschlag: Silbentrennung und Umbruch nach «/» erlauben (`overflow-wrap: anywhere`), im Streifen
  den Namen unter das Resultat setzen, wenn der Platz fehlt.

**N12 · Spielerseite und Zahlen: falsche oder leere Werte**
- Route: `{t}/players/<id>`, `{m}?tab=zahlen`. Gerät: Desktop.
- Passiert: Tim Baumann: 17 Tore aus 21 Würfen, Wurfquote **85 %** (richtig 81 %); Spalte «7 m» mit
  «0/0» in jeder Zeile. Tab Zahlen: Spalte «Bestätigt» bei allen leer, Quellenzeile «42 von 44 Toren
  von dir bestätigt».
- Screenshot: `shots/v34-spielerseite.jpg`, `shots/n12-zahlen-bestaetigt.jpg`
- Vorschlag: Quote aus denselben Summen wie die angezeigten Zahlen; nie erfasste 7 m leer; Häkchen
  nach derselben Regel wie die Quellenzeile.

**N13 · «1 Frage offen, 1 Minute» wird zu sechs Fragen**
- Route: Start › «1 Frage offen» › «Passt». Gerät: beide.
- Passiert: Nach der Feldfrage kommen «Frage 1 von 6 · Wer ist das?». Die Zusage auf dem Start
  stimmt nicht; dazu ein erklärender Absatz «Die Personen mit der längsten Zeit im Bild kommen zuerst.
  Jede Antwort ist sofort gespeichert und macht die Zahlen genauer.»
- Screenshot: `shots/n13-pruefen-sechs-fragen.jpg`
- Vorschlag: Auf dem Start die Fragen zählen, die nach der Feldfrage folgen («1 Frage, danach etwa 6
  mehr»), oder nach «Passt» sagen, warum es mehr werden.

**N14 · Spieltag: Uhr, Rückgängig, kleine Tasten**
- Route: `{m}/matchday`. Gerät: Handy.
- Passiert: Die Uhr zeigt die Uhrzeit des Handys («05:00 · 1. Halbzeit»), nicht die Spielzeit; es
  gibt kein «zurücknehmen» für den letzten Eintrag; «2 Minuten» und «Time-out» fehlen (nur
  «Halbzeit»); «Link teilen» fehlt (SPEC 7.11).
- Screenshot: `shots/v22-spieltag.jpg`
- Vorschlag: Spieluhr mit Start/Pause, «zurücknehmen» am letzten Eintrag, die drei kleinen Tasten.

**N15 · Anmeldelink nur 15 Minuten gültig**
- Route: Mail «Dein Anmeldelink». Gerät: beide.
- Passiert: «Er ist 15 Minuten gültig und funktioniert nur einmal». Hans liest Mails oft später; dann
  ist auch die Teamwahl verloren (N22).
- Vorschlag: für den ersten Einstieg mindestens 24 Stunden, oder ein 6-stelliger Code daneben.

**N16 · Spiel in der Zukunft verlangt schon das Video**
- Route: `{m}` des nächsten Spiels. Gerät: beide.
- Passiert: Öffnet im Tab Video mit «Lad das Video hoch. Du bekommst eine Mail …», obwohl das Spiel
  erst am 17. November ist. SPEC 7.2: vor dem Spiel die Gegnerfakten und «Spieltag starten».
- Screenshot: `shots/v42-naechstes-spiel.jpg`
- Vorschlag: vor dem Anpfiff Tab Spiel mit den Fakten zum Gegner, Upload erst ab dem Spieltag.

**N17 · Feldecken-Griffe zu klein**
- Route: `{m}/check` («Passt das Spielfeld?»). Gerät: Handy.
- Passiert: Griffe 22 × 22 px; mit dem Daumen schwer zu treffen, verdeckt beim Ziehen die Ecke.
- Screenshot: `shots/n19-ecken-handy.jpg`
- Vorschlag: Trefferfläche 44 px (sichtbar klein lassen), beim Ziehen eine Lupe oder versetzten Punkt.

### P3

**N18 · App-404 antwortet mit HTTP 200**: `{o}/gibtsnicht`, `{m}` mit unbekannter ID. Für
Suchmaschinen und Überwachung unsichtbar.

**N19 · Drosselung schiebt die Schuld auf handball.ch**: Nach 20 schnellen Suchen sagt der Einstieg
«handball.ch antwortet gerade nicht. Versuch es gleich nochmals …», obwohl die eigene Drosselung
(HTTP 429) greift. `shots/n21-drosselung.jpg`

**N20 · Mail-Anrede mit dem Teil vor dem @**: «Hallo hans.p130.1794543325907». Ohne Namen besser
«Hallo».

**N21 · Gleiche Adresse zweimal: zweiter Verein ohne Hinweis**: Speichern eines zweiten Teams mit
derselben E-Mail legt einen zweiten Verein an und wechselt hinein.

**N22 · Abgelaufener oder doppelt geöffneter Link**: «Der Link ist ungültig oder abgelaufen.» mit
«Anmelden»; die Teamwahl ist weg. Beim zweiten Öffnen sagt die Seite das, obwohl man schon
angemeldet ist. `shots/n24-link-ungueltig.jpg`. Vorschlag: «Neuen Link schicken» mit derselben
Adresse und Teamwahl; angemeldet direkt weiter in die App.

**N23 · Szenenfolge beginnt anders als die Liste**: «Alle 24 abspielen» startet mit «TV Rüti · 0:15»
(Videozeit), die Liste mit «8.11. Thalwil 56:55».

**N24 · Alte Sätze nach der Analyse**: «Analyse fertig. Statistik und Szenen stehen bereit.»;
«Du kannst die Seite schliessen …» nur rund 4 Sekunden sichtbar.

**N25 · Fachwörter auf Start und im Telegramm**: «Tabelle · Hauptrunde - M1-01», «Frei 3/1»
(3 Tore, davon 1 Siebenmeter).

**N26 · Unbekannte Gegnerfarbe: leeres Kästchen statt Frage**: Echter Verein, Kopf zeigt ein leeres
Kästchen und «Farbe von TSV Fortitudo Gossau 2 ändern»; SPEC 7.13 will «Welche Farbe trägt …?» mit
fünf Trikots im Kopf. `shots/n05-spiel-ohne-drei-dinge.jpg`

---

## Teil 3: neues Suchen

Folgt als Nachtrag.
