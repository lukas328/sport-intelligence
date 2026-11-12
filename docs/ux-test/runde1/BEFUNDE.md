# UX-Test Runde 1: Handball Intelligence im Aussehen «Anlauf»

Stand: 12. November 2026, Branch `claude/trikot-ui` (Commit f78f8e8), getestet auf `claude/ux-test`.
Testerin: unabhängig, hat die Oberfläche nicht gebaut. Nichts in `apps/` oder `packages/` geändert.

Aufbau: lokaler Stack nach `docs/runbooks/local-stack-without-docker.md` (Produktions-Build von
`apps/web`, `next start`), Demo-Daten mit `make seed`, Demo-Konto `demo@handball-demo.ch`. Dazu
eigene Konten über die Registrierung: zwei Vereine aus handball.ch (Handball Stäfa, Pfadi
Winterthur) und ein Verein von Hand ohne Daten («FC Leer»). Playwright mit Chromium, Desktop
1280 × 800 und Handy 390 × 844 (Touch). Personen: (A) Sandra am Laptop, (B) Sandra am Handy in der
Halle, (C) Spieler ohne Konto über geteilten Link und Einwilligungs-Link.

Schweregrade: **P1** blockiert eine Aufgabe oder verliert Daten, **P2** verwirrt oder kostet Zeit
(auch: zeigt etwas, das die Daten nicht hergeben), **P3** Schliff.

---

## Zusammenfassung

Das neue Aussehen trägt auf den Seiten, die neu gebaut wurden: Start (Wurf-Kopf, drei Dinge mit
Bündeln, Spielliste), Saison, Team, der Einwilligungs-Link und der Prüfen-Screen sehen nach
«Anlauf» aus und sind ohne Erklärung lesbar. Sobald Sandra aber einen Schritt tiefer geht, landet
sie fast überall im alten Produkt: im Tab Spiel unterhalb der drei Dinge, im ganzen Tab Zahlen,
im Spieltag, nach dem Upload, hinter «Suchen», «Als Tabelle», «Mehr» und in vierzehn alten Routen.
Die Kernversprechen des Zielbilds (Szenen zu Punkt 1 ansehen, Frage stellen, Sammlung mit Notiz,
am Bildschirm zeigen) sind im Moment nicht einlösbar.

### Die fünf wichtigsten Probleme

1. **Die Szenen zu Punkt 1 sind nicht zu finden (B01, P1).** «9 Szenen» unter «Gegentore über
   rechts aussen» öffnet den Tab Video mit einer Liste «4. bis 11. · 5 Szenen», einem Zeitfenster,
   in dem eigene Tore, ein Gegenstoss und ein Gegentor über rechts aussen gemischt sind. Die neun
   Gegentore nacheinander zu sehen, geht nirgends. Das ist der Kern des Produkts.
2. **Eine Frage stellen endet in einer Sackgasse (B02, P1).** «Suchen» öffnet eine Schnellsuche
   («Gehe zu», «Spielzüge», «Tabelle»). Die Frage «Wie viele Gegentore über rechts aussen in den
   letzten drei Spielen?» ergibt «Nichts gefunden»; Enter führt auf die alte Assistenten-Seite mit
   «Der Assistent ist in dieser Installation nicht eingerichtet.» Die Frage ist dabei weg.
3. **Der Spieltag zeigt nach Neu laden nichts mehr (B03, P1).** Einträge werden an den Server
   geschickt («Alles gespeichert»), nach einem Neu laden stehen Resultat 0:0 und «Noch nichts
   erfasst» da, der Spielkopf zeigt «-:-». Wer in der Halle neu lädt, erfasst doppelt; die doppelten
   Tore landen in der Saison («Wer trifft»). Dazu ist der Spieltag noch die alte Detail-Erfassung
   statt der sechs grossen Tasten (B22).
4. **Der Tab Spiel und der Tab Zahlen sind im Kern das alte Produkt (B08, B23), und die App zeigt
   dort Dinge, die die Daten nicht hergeben (B07, B12, B39).** Unter den drei Dingen folgen eine
   zweite Liste «Drei Dinge» (Stärke / Baustelle / Belege anzeigen), xG, «Ballbesitz 41 % zu 59 %»,
   ein zweiter Spielverlauf, Gegentore nach Position doppelt. Bei Spielen nur mit Spielbericht
   erfindet die App «Lauf von 29 Toren in Folge» und «Bester Lauf 29:0», weil die Tore keine Zeiten
   haben. Die Taktikkamera zeigt Positionen, obwohl das Feld nicht bestätigt ist und Prüfen genau
   das Gegenteil verspricht; auf der Kamera tragen zwei eigene Spieler die Nummer 15.
5. **Fürs Team zusammenstellen ist halb gebaut (B04, B05, B15, B16, B17).** Der Entwurf enthält
   nicht die drei Dinge, sondern andere Szenen mit Duplikaten; eine Notiz kann man nicht hinzufügen,
   nichts entfernen, nichts umbenennen. Nach dem Teilen steht weiter «Noch nicht geteilt», der Link
   ist «nur jetzt sichtbar». «Am Bildschirm zeigen» führt auf dieselbe Seite zurück. Die geteilte
   Seite für Spieler ist eine nüchterne Liste «1. Szene … 12. Szene» mit Produktkopf und «Anmelden».

### Was gut funktioniert

- **Start-Screen bei einem analysierten Spiel**: Titel «Gewonnen. Und drei Dinge zum Mitnehmen.»,
  Resultat, Verlauf, drei Dinge mit Zahl, Basis und Bündel sind auf einen Blick klar. «1 Frage
  offen, 1 Minute» ist eine sehr gute Einladung.
- **Prüfen**: ruhige Vollbildseite, grosse Antworttasten, sichtbarer Tastaturfokus, sofort
  gespeichert, klarer Abschluss («Alles geprüft.»).
- **Saison und Team**: Titel aus den Daten («Fünf Spiele. Und rechts aussen bleibt offen.»,
  «15 im Kader. Bei dreien fehlt noch etwas.»), gelbe Wörter für Fehlendes, Serien pro Spiel.
- **Einwilligung ohne Konto**: in unter einer Minute erledigt, klarer Dank, das Team zählt sofort
  (13 → 14 von 15). «Link kopieren» meldet «Link kopiert».
- **Onboarding mit handball.ch**: «Das seid ihr, oder?» mit Haken, Trikotfarbe und Vorschau ist
  verständlich; die gewählte Farbe zieht sofort durch die App. Vereinsfarbe ändern wirkt sofort.
- **Offline im Spieltag**: «Offline: 1 ausstehend» ist eine ehrliche Anzeige.
- **Sprachen**: fr und en sind auf den neuen Screens vollständig übersetzt.
- **Handwerk**: kein horizontaler Überlauf bei 390 px auf allen 60 geprüften Routen; Kopfzeile und
  Tab-Leiste am Handy sauber; Link-Vorschau (Open-Graph-Bild) entspricht dem Zielbild.

### Zahlen

| Gewicht | Anzahl |
|---|---|
| P1 | 6 |
| P2 | 33 |
| P3 | 15 |
| **Total** | **54** |

---

## Aufgaben

Schritte = Klicks oder Eingaben ab dem ersten sinnvollen Screen, auf dem schnellsten Weg, den eine
Trainerin ohne Hilfe findet.

### Aufgabe 1: Erster Besuch bis zum ersten sinnvollen Screen (`shots/a01-einstieg.jpg`)

| | Desktop | Handy |
|---|---|---|
| Geschafft | mit Mühe | mit Mühe |
| Schritte | 9 (Jetzt starten, 4 Felder, Konto erstellen, Suche, Übernehmen, Stimmt weiter) | 9 |
| Zeit allein fürs «Übernehmen» | 12,6 s | 13,6 s |

Stolperstellen: Fehlermeldungen beim leeren Formular auf Englisch (B25); Nutzungsbedingungen
nicht verlinkt (B25); nach «Übernehmen» drehen 12 bis 14 Sekunden lang alle acht Knöpfe ohne
Satz (B24); danach kein Hinweis «erstes Video oder Demo-Spiel» (B26), dafür sofort das
Zwei-Faktor-Banner. Der Verein ganz ohne handball.ch-Daten läuft durch den alten Vierschritt-
Assistenten mit «Team, Team» und «Einladen» (B27). Versteht man, was die App tut? Die öffentliche
Startseite verspricht Dinge, die nicht (mehr) Umfang sind (B40).

### Aufgabe 2: Video hochladen und auf die Analyse warten (`shots/a02-upload.jpg`)

| | Desktop | Handy |
|---|---|---|
| Geschafft | ja | ja (Ablauf identisch, nur Desktop vollständig fotografiert) |
| Schritte | 3 (Video hochladen, Spiel wählen, Datei wählen) | 3 (+ statt «Video hochladen») |

Stolperstellen: Während der Analyse sieht man eine technische Schrittliste («Analyse-Version
erstellen», «Qualitätscheck», «Für Wiedergabe umwandeln») in falscher Reihenfolge und ohne Minuten
(B11). Danach öffnet der Tab Video den alten Einrichtungs-Assistenten mit vier Schritten und vier
Unter-Tabs (B10). Dass die Analyse fertig ist, sagt die Glocke («Die Videoanalyse ist fertig.»)
ohne Spielnamen; ein Fehlschlag meldet die Glocke gar nicht (B29). Die Analyse eines echten
60-Minuten-Videos war nicht testbar (siehe «Nicht getestet»).

### Aufgabe 3: Die drei Dinge verstehen, Szenen zu Punkt 1, Taktik/Video (`shots/a03-drei-dinge.jpg`)

| | Desktop | Handy |
|---|---|---|
| Drei Dinge finden und verstehen | ja, sofort | ja |
| Szenen zu Punkt 1 ansehen | **nein** | **nein** |
| Taktik / Video umschalten | ja (1 Klick) | ja |

Stolperstellen: «9 Szenen» führt in ein Zeitfenster statt zu den neun Szenen (B01). «Spiel öffnen»
öffnet den Tab Video statt Spiel, Tabwechsel ändern die Adresse nicht (B09). Wörter im Tab Video:
«Tor Wir», «RR», «4. bis 11.», «Spielerin hervorheben» bei einem Herrenteam (B37). Taktikkamera am
Handy zu klein (B38). Positionen trotz unbestätigtem Feld, doppelte Nummer 15 (B12, B39).

### Aufgabe 4: Prüfen (`shots/a04-pruefen.jpg`)

| | Desktop | Handy |
|---|---|---|
| Geschafft | ja | ja |
| Schritte | 2 (Link «1 Frage offen», «Ja, stimmt») | 2 |
| Klar wozu? | teilweise | teilweise |

Stolperstellen: «Ecken verschieben» verlässt Prüfen und landet ohne Ecken im Spiel (B14). Der
Satz «Bis das Feld bestätigt ist, zeigen wir keine Wege und keine Positionen» stimmt nicht, die
Positionen sind schon zu sehen; nach «Ja, stimmt» ändert sich deshalb sichtbar nichts (B12). Der
gelbe Rahmen umfasst das ganze Bild statt das erkannte Feld (B13). Im Demo gibt es nur die
Feldfrage; «Wer ist das?» und «Tor oder kein Tor?» kamen nicht vor.

### Aufgabe 5: Sammlung, Notiz, Link teilen, als Spieler öffnen (`shots/a05-team.jpg`)

| | Desktop | Handy (C) |
|---|---|---|
| Sammlung aus einem Ding | mit Mühe (Entwurf enthält Falsches) | – |
| Notiz dazu | **nein** (keine Funktion) | – |
| Link teilen | ja, 4 Schritte (Teilen, Gültigkeit, Link erstellen, Kopieren) | – |
| Link als Spieler öffnen | – | ja, aber Seite nicht nach Zielbild |

Stolperstellen: B05, B16, B17, B15, B04.

### Aufgabe 6: «Wie viele Gegentore über rechts aussen in den letzten drei Spielen?» (`shots/a06-frage.jpg`)

| | Desktop | Handy |
|---|---|---|
| Über «Suchen» | **nein** (Sackgasse, B02) | **nein** |
| Über den Reiter «Szenen» | ja, 1 Klick (die Seite öffnet zufällig genau mit dieser Antwort: «24 von 66») | ja, 1 Tipp |

Stolperstellen: Man muss wissen, dass «Szenen» die Suche ist und «Suchen» nicht. «letzte 3 Spiele»
heisst in Wahrheit «letzte 3 Spiele mit Video» (B20). Eigene Wörter im Suchfeld werden nicht
verstanden (B19). «Alle 24 abspielen» spielt nur ein Spiel, «Als Tabelle» öffnet die alte Matrix
ohne die Filter (B21).

### Aufgabe 7: Saison, Einwilligungen (`shots/a07-saison-team.jpg`)

| | Desktop | Handy (C) |
|---|---|---|
| Was wiederholt sich? | ja, sofort | ja |
| Wem fehlt die Einwilligung? | ja, sofort (gelbe Wörter) | ja |
| Link verschicken | ja, 1 Klick, «Link kopiert» | – |
| Einwilligung als Spieler geben | – | ja, 4 Schritte |

Stolperstellen: Spieler im Formular ist auf «#1 Andrin G.» vorbelegt (B33). Spielerseite und
«Kader bearbeiten» sind im alten Aufbau (B41, Liste am Ende).

### Aufgabe 8: Spieltag am Handy (`shots/a08-spieltag.jpg`)

| | Handy |
|---|---|
| Geschafft | **nein** (Daten scheinbar weg nach Neu laden) |
| Schritte bis zur ersten Erfassung | 4 (Spiel öffnen, Spieltag starten, Start, Spieler + Tor) |

Stolperstellen: B03, B22. Vom Start aus gibt es keinen Weg zum Spieltag des nächsten Spiels.

### Aufgabe 9: Vereinsfarbe, Gegnerfarbe, Team, Sprache, Abmelden (`shots/a09-einstellungen.jpg`)

| | Desktop | Handy |
|---|---|---|
| Vereinsfarbe ändern | ja, 4 Schritte, «Gespeichert» | ja |
| Gegnerfarbe eines Spiels | mit Mühe (Mehr › Spiel bearbeiten › Trikotfarben) | mit Mühe |
| Team wechseln | mit Mühe (Kopf und Inhalt passen nicht, B30) | wie Desktop |
| Sprache wechseln | **nein** (kein Schalter, B06) | **nein** |
| Abmelden | ja, 2 Schritte | ja |

### Aufgabe 10: Fehler und Ränder (`shots/a10-fehler.jpg`)

| Fall | Ergebnis |
|---|---|
| Falsches Passwort | gut: «E-Mail oder Passwort ist falsch.», E-Mail bleibt stehen |
| Falsche Datei (Text als Video) | schlecht: «Etwas ist schiefgelaufen. Bitte versuch es nochmals.» (B29) |
| Kaputtes Video | schlecht: «Fehlgeschlagen · 8 %» ohne Grund, Text überlappt (B29) |
| Spiel ohne Video | erfundene Läufe, kein Kein-Video-Zustand (B07) |
| Neuer Verein ohne Daten | alter Assistent, leere Szenen sagt «Nimm einen Filter weg» (B27, B28) |
| Neu laden im Onboarding | springt nach «Übernehmen» direkt in die App, Trikotfarbe und «Das ist nicht mein Team» übersprungen (B24) |
| Neu laden im Spiel | Tab geht verloren (B09); im Spieltag scheinbar alle Einträge (B03) |
| Zurück-Taste | verlässt das Spiel statt den Tab zu wechseln (B09); nach Abmelden landet Zurück korrekt auf der Anmeldung |
| Alte Routen | 14 alte Seiten ohne Umleitung, 2 Umleitungen auf 404 (B32) |

---

## Befunde

Jeder Befund: Route, Gerät, Nachstellen, Erwartet, Passiert, Screenshot, Vorschlag.
`{o}` = `/app/<orgId>`, `{t}` = `{o}/teams/<teamId>`, `{m}` = `{o}/matches/<matchId>`.

### P1: blockiert eine Aufgabe oder verliert Daten

**B01 · Szenen zu Punkt 1 nicht erreichbar**
- Route: `{t}/matches` → `{m}?tab=video`; auch Tab Spiel. Gerät: beide.
- Nachstellen: Start, unter «1 von 3 · Gegentore über rechts aussen» auf «9 Szenen».
- Erwartet: die neun Gegentore über rechts aussen nacheinander, mit «Nächste Szene» (SPEC 7.1, 7.2).
- Passiert: Tab Video mit der Liste «4. bis 11. · 5 Szenen» (Tor TSV 4:11 Gegenstoss, Tor Wir 5:08,
  Tor TSV 7:46, Tor Wir 10:19, Tor TSV 10:51). Die anderen acht Szenen von Punkt 1 sind nur über
  die Zeitleiste zu erraten. Im Tab Spiel ist «9 Szenen» ein Knopf mit derselben Wirkung; am Handy
  scrollt die Seite zur Liste, die Kamera ist dann ausser Sicht.
- Screenshot: `shots/b01-szenen-punkt1.jpg`
- Vorschlag: «n Szenen» öffnet eine Szenenfolge genau dieses Dings (gleiche Logik wie die Sammlung:
  Liste der n Szenen rechts, laufende gelb, «Nächste Szene»), Adresse z. B. `?thing=1`. Die Liste
  «4. bis 11.» nur zeigen, wenn man auf der Zeitleiste klickt, und dann mit Titel «Minute 4 bis 11».

**B02 · «Suchen» mit einer Frage endet beim nicht eingerichteten Assistenten**
- Route: Schnellsuche → `{t}/assistant?q=…`. Gerät: beide.
- Nachstellen: «Suchen» in der Kopfzeile, «Wie viele Gegentore über rechts aussen in den letzten drei
  Spielen?» tippen, Enter.
- Erwartet: die Szenen-Suche mit erkannten Chips und der Antwort «24 von 66» (SPEC 6, 7.6, Wort
  «Suchen» ersetzt «Frag deine Daten»).
- Passiert: Schnellsuche zeigt «Nichts gefunden.» und «Suchen: «…»»; Enter öffnet die alte Seite
  «Suchen» mit «Der Assistent ist in dieser Installation nicht eingerichtet.», die Frage ist nicht
  mehr im Feld.
- Screenshot: `shots/b02-suchen-assistent.jpg`, `shots/b18-schnellsuche.jpg`
- Vorschlag: «Suchen» öffnet die Szenen-Seite mit fokussiertem Suchfeld und übergibt den Text;
  Wörter wie «rechts aussen», «Gegentore», «letzte drei Spiele» werden zu Chips. Die Route
  `assistant` auf Szenen umleiten.

**B03 · Spieltag: Einträge nach Neu laden scheinbar weg, Resultat falsch**
- Route: `{m}/matchday`. Gerät: Handy (auch Desktop).
- Nachstellen: Spieltag des nächsten Spiels, Start, «9 Simon» + «Tor» (Resultat 1:0, «Alles
  gespeichert»), Seite neu laden.
- Erwartet: Resultat 1:0 und der Eintrag im Verlauf.
- Passiert: 0:0, «Noch nichts erfasst», «Rückgängig» deaktiviert; die Spielseite zeigt «-:-». Der
  Server hat die Einträge (POST 201, 11 Ereignisse in der Datenbank) und zählt sie in Saison › Wer
  trifft (Tim Baumann 17 → 19 Tore nach meinen Tests). Dreimal nachgestellt. Offline: der Eintrag
  bleibt nach Neu laden als einziger stehen, die vorherigen sind weg.
- Screenshot: `shots/b03-spieltag-verlust.jpg` (links vor, rechts nach dem Neu laden)
- Vorschlag: Spieltag lädt beim Öffnen die Ereignisse des Spiels und rechnet das Resultat daraus;
  «Alles gespeichert» erst zeigen, wenn der Zustand nach Neu laden derselbe ist. Test in Playwright:
  erfassen, neu laden, gleiches Resultat.

**B04 · «Am Bildschirm zeigen» tut nichts**
- Route: `{o}/collections/<id>/present` → zurück auf `{o}/collections/<id>`. Gerät: Desktop.
- Nachstellen: eine Sammlung öffnen, «Am Bildschirm zeigen».
- Erwartet: Vollbild ohne Navigation für die Videositzung (SPEC 6, 7.7).
- Passiert: die Seite lädt neu und ist dieselbe. Laut Code-Kommentar «comes with the new look».
- Screenshot: `shots/b04-bildschirm-zeigen.jpg`
- Vorschlag: bauen, oder den Knopf ausblenden, bis es die Ansicht gibt. Ein Knopf, der nichts tut,
  kostet mehr Vertrauen als einer, der fehlt.

**B05 · Sammlung: keine Notiz, nichts entfernen, nichts umbenennen**
- Route: `{o}/collections/<id>`. Gerät: beide.
- Nachstellen: Start › «Fürs Team zusammenstellen».
- Erwartet: Entwurf, den die Trainerin kürzt; Einträge Szene, Spielzug, Notiz (SPEC 7.7, Aufgabe 5).
- Passiert: nur «Szene dazu» und «Spielzug dazu»; kein Notiz-Eintrag, kein Entfernen, kein
  Verschieben, Titel nicht bearbeitbar; jeder Eintrag ist ein Link ins Spiel.
- Screenshot: `shots/b05-sammlung-entwurf.jpg`
- Vorschlag: «Notiz dazu» als dritte Taste; pro Eintrag ein Griff zum Verschieben und «Entfernen»;
  Titel antippen zum Ändern.

**B06 · Sprache lässt sich nicht wechseln**
- Route: `{o}/me` (Ich › Profil). Gerät: beide.
- Nachstellen: Konto › Ich; nach «Sprache» suchen.
- Erwartet: Sprache in Ich (SPEC 6 nennt Profil); die App kann de-CH, fr, en.
- Passiert: Ich › Profil enthält nur E-Mail-Hinweis, Passwort und Geräte, keine Sprache, keinen
  Namen, keine Mitteilungen. Die Sprache folgt nur dem Cookie `NEXT_LOCALE`, nicht einmal der
  Browsersprache. Mit gesetztem Cookie sind fr und en auf Start, Spiel, Szenen, Team und Prüfen
  vollständig übersetzt.
- Screenshot: `shots/b06-ich-ohne-sprache.jpg`
- Vorschlag: Feld «Sprache» in Ich › Profil (und im Fuss der öffentlichen Seiten); ohne Wahl die
  Browsersprache nehmen.

### P2: verwirrt, kostet Zeit oder zeigt, was die Daten nicht hergeben

**B07 · Spiel nur mit Spielbericht: erfundene Läufe und leerer Verlauf**
- Route: `{m}` eines Spiels ohne Video (SG Horgen-Oberrieden). Gerät: beide.
- Nachstellen: Start › Spiel vom 24.10. öffnen.
- Erwartet: Telegramm und Verlauf aus dem Bericht, Block «Kein Video» (SPEC 7.2, 7.13).
- Passiert: «Lauf von 29 Toren in Folge», «Der Gegner erzielte 19 Tore in Folge», «Bester Lauf:
  29:0», «Den Unterschied machten die Paraden (37 % zu 0 %)», ein leeres Diagramm «Spielverlauf»,
  Gegner mit «0» Paraden und Ballverlusten, das Wort «Papierbericht». Kein Upload-Block, kein
  Telegramm; der Wurf-Kopf ist zur Hälfte leer.
- Screenshot: `shots/b07-nur-spielbericht.jpg`
- Vorschlag: ohne Torfolge keine Läufe und keinen Verlauf; fehlende Werte leer statt 0; Zustand
  «Kein Video» nach Zielbild.

**B08 · Tab Spiel: unter den drei Dingen das alte Produkt**
- Route: `{m}?tab=spiel`. Gerät: beide.
- Nachstellen: Spiel gegen Thalwil, Tab Spiel, nach unten scrollen.
- Erwartet: drei Dinge, Aktionen (Fürs Team, Highlights teilen, Als Bild für den Chat), «Punkt 1,
  geöffnet» mit Taktikkamera, Telegramm, Seitenleiste Gegentore / Eigene Tore / drei Zahlen mit
  Quelle (SPEC 7.2).
- Passiert: danach folgen «Ereignisse: 105 von Hand erfasst…», «Den Unterschied machten die
  Paraden…», eine zweite Liste «Drei Dinge» (Stärke, Baustelle, «Belege anzeigen», «Alle 6 zeigen»,
  «Zusammenfassung schreiben»), «Spielverlauf» als zweites Diagramm, «Kennzahlen im Vergleich» mit
  «xG (geschätzt)», «Torschützen», «Gegentore nach Position» zum zweiten Mal, «Ballbesitz 41 % zu
  59 %, 2 Angriffe, geschätzt», «Feedback · Notizen 0 von 38 · weiter mit Andrin Gerber», Highlights
  mit drei Zeilen Erklärung, «Am Spieltag gemerkt (0)». Es fehlen «Punkt 1, geöffnet», das
  Telegramm, «Highlights teilen», «Als Bild für den Chat», «Dazu üben».
- Screenshot: `shots/b08-tab-spiel-alt.jpg`
- Vorschlag: alles unterhalb der drei Dinge durch den Aufbau des Zielbilds ersetzen; xG und
  Ballbesitz streichen (nicht gemessen); Feedback und «Szenen der Spieler» hinter Teamfunktionen.

**B09 · «Spiel öffnen» öffnet den Tab Video; Tabs nicht in der Adresse**
- Route: `{m}`. Gerät: beide.
- Nachstellen: Start › «Spiel öffnen»; dann Tab Spiel wählen, neu laden oder Zurück.
- Erwartet: Tab Spiel mit Wurf-Kopf; Tab bleibt nach Neu laden; Zurück wechselt zurück.
- Passiert: Standard ist «Video» (`match-view.tsx`: `useState("video")`). Der Tabwechsel schreibt
  `?tab=` nicht; Neu laden springt auf den Tab der alten Adresse, Zurück verlässt das Spiel.
- Screenshot: `shots/b09-spiel-oeffnen-video.jpg`
- Vorschlag: Standard «Spiel» (bei Spielen mit Video und ohne), Tab in die Adresse schreiben
  (`router.replace`).

**B10 · Nach dem Upload: alter Einrichtungs-Assistent im Tab Video**
- Route: `{m}` nach dem Upload. Gerät: Desktop (Handy gleich).
- Nachstellen: neuer Verein, «Video hochladen», Spiel wählen, Datei wählen, warten.
- Erwartet: Bühne mit Taktik | Video, offene Fragen in Prüfen (SPEC 7.3, 7.5).
- Passiert: «Analyse fertig. Statistik und Szenen stehen bereit.», darunter vier Schritte
  «Spielfeld · Anwurf · Tore prüfen · Spieler zuordnen» und vier Unter-Tabs «Ereignisse,
  Abwehrsysteme, Kommentare, Feedback» (zwei Tab-Ebenen), Erklärtext zum Anwurf, runder Abspielknopf.
- Screenshot: `shots/b10-nach-upload-assistent.jpg`
- Vorschlag: die Einrichtungsschritte als Fragen in Prüfen; Tab Video ohne Unter-Tabs.

**B11 · «Analyse läuft» spricht Technik und sagt nicht, wie lange**
- Route: `{m}` während der Verarbeitung. Gerät: Desktop.
- Nachstellen: Video hochladen, sofort ansehen.
- Erwartet: «Die Analyse läuft.» im Kopf, Schritte fertig / läuft / danach in Reihenfolge,
  Minuten bis fertig, etwas Nützliches daneben (SPEC 7.13).
- Passiert: Überschrift «Verarbeitung», «Läuft · 70 %», Schritte «Video prüfen, Analyse-Version
  erstellen, Speichern, Qualitätscheck, Video laden, Für Wiedergabe umwandeln, Vorschaubilder» mit
  gemischt «fertig», «läuft», «danach», «fertig»; keine Zeitangabe; rechte Hälfte leer.
- Screenshot: `shots/b11-analyse-laeuft.jpg`
- Vorschlag: drei Schritte in Trainerwörtern («Video gelesen», «Spieler werden verfolgt», «Drei Dinge
  werden gesucht»), Minuten, daneben der Spielbericht und das Telegramm.

**B12 · Taktikkamera zeigt Positionen, obwohl das Feld nicht bestätigt ist**
- Route: Start (Szene 7:46), `{m}?tab=video`, `{m}/check`. Gerät: beide.
- Nachstellen: Start › «Szene 7:46»; dann «1 Frage offen» öffnen.
- Erwartet: ohne bestätigtes Feld keine Wege und keine Positionen (SPEC 7.13, ANLAUF 10).
- Passiert: die Kamera zeigt Spieler und Wege; Prüfen fragt «Passt das Spielfeld?» und sagt «Bis das
  Feld bestätigt ist, zeigen wir keine Wege und keine Positionen.» Nach «Ja, stimmt» ändert sich
  sichtbar nichts.
- Screenshot: `shots/b12-positionen-ohne-feld.jpg`
- Vorschlag: entweder die Kamera bis zur Bestätigung im Zustand «Stimmt das Feld?» zeigen, oder den
  Satz in Prüfen ändern. Das Erste ist die Regel des Zielbilds.

**B13 · Prüfen «Passt das Spielfeld?» zeigt das erkannte Feld nicht**
- Route: `{m}/check`. Gerät: beide.
- Erwartet: das erkannte Feld gestrichelt gelb mit vier Eckgriffen (SPEC 7.13).
- Passiert: ein gelber Rahmen um das ganze Bild; man kann nicht sehen, was «das Spielfeld» ist.
- Screenshot: `shots/b13-pruefen-feld.jpg`
- Vorschlag: die erkannten Linien als Viereck über das Bild legen.

**B14 · «Ecken verschieben» verlässt Prüfen ohne Ecken**
- Route: `{m}/check` → `{m}`. Gerät: Desktop.
- Nachstellen: Prüfen › «Ecken verschieben».
- Erwartet: vier Griffe auf dem Bild, «Speichern».
- Passiert: Weiterleitung ins Spiel (Tab Video), keine Ecken, die Frage bleibt offen.
- Screenshot: `shots/b14-ecken-verschieben.jpg`
- Vorschlag: Ecken im Prüfen-Screen selbst verschieben.

**B15 · Geteilte Seite nicht nach Zielbild**
- Route: `/s/<token>`. Gerät: Handy (C), Desktop.
- Nachstellen: Sammlung › Teilen › Link erstellen › Kopieren; Link ohne Konto öffnen.
- Erwartet: Wappen und Vereinsname, «von Sandra», Video | Taktik, Notiz, «Nächste Szene», Liste mit
  Titeln und laufender Szene gelb; kein Menü, keine Anmeldung (SPEC 7.8).
- Passiert: Produktkopf mit «Systemstatus» und «Anmelden», kein Wappen, kein Absender, Liste «1.
  Szene» bis «12. Szene» ohne Titel und ohne Minifeld, laufende Szene schwarz. Die Link-Vorschau
  (Open Graph) ist dagegen gut.
- Screenshot: `shots/b15-geteilt-handy.jpg`
- Vorschlag: Seite nach `#geteilt` bauen; Szenentitel aus der Sammlung übernehmen.

**B16 · «Fürs Team zusammenstellen» enthält nicht die drei Dinge**
- Route: `{o}/collections/<neu>`. Gerät: Desktop.
- Erwartet: Szenen der drei Dinge (9 + 4 + 11), als Entwurf.
- Passiert: 12 Einträge: «Tor über links aussen», «Tor aus dem Rückraum rechts/links», nur drei der
  neun Gegentore über rechts aussen, drei Einträge doppelt (1:15, 2:35, 5:08), ein Eintrag «Szene»
  ohne Minifeld; keine Spielangabe pro Eintrag. Die Demo-Sammlung hat dieselben Fehler.
- Screenshot: `shots/b05-sammlung-entwurf.jpg`, `shots/b51-sammlung-seed.jpg`
- Vorschlag: Entwurf aus den Szenen der drei Dinge bauen, Duplikate entfernen, je Ding eine
  Zwischenzeile als Notiz.

**B17 · Teilen: Extra-Dialog, Link nur einmal sichtbar, falscher Zustand danach**
- Route: `{o}/collections/<id>`. Gerät: Desktop.
- Nachstellen: «Teilen», Gültigkeit, «Link erstellen», «Kopieren», Dialog schliessen.
- Erwartet: «Link teilen» als Hauptknopf, ein Tipp, «Link kopieren» in der Seitenleiste, «Geöffnet»
  mit Zähler und «Link sperren» (SPEC 7.7, 30 Tage fest).
- Passiert: Teilen ist nicht der Hauptknopf; Dialog mit Auswahl 1 bis 90 Tage; «Link (nur jetzt
  sichtbar)»; nach dem Schliessen steht in der Seitenleiste weiter «Noch nicht geteilt.», der Link
  ist nicht mehr zu bekommen. «Kopiert» als Rückmeldung ist gut.
- Screenshot: `shots/b17-nach-teilen.jpg`, `shots/b17b-link-dialog.jpg`
- Vorschlag: «Link teilen» erstellt und kopiert in einem Schritt (30 Tage), Seitenleiste zeigt den
  Link, «Link kopieren», «Geöffnet 0 Mal», «Link sperren».

**B18 · Knopf «Suchen» öffnet eine Schnellsuche, nicht die Szenen-Suche**
- Route: alle. Gerät: beide.
- Erwartet: «Suchen» = Szenen-Suche (SPEC 9).
- Passiert: «Suchen oder springen …» mit «Gehe zu: Spiele, Szenen, Saison, Team, Sammlungen,
  Spielzüge, Tabelle, Ich, Verein» und «Aktionen». Spielzüge und Tabelle sind nicht im Umfang.
- Screenshot: `shots/b18-schnellsuche.jpg`
- Vorschlag: siehe B02. Die Schnellsuche höchstens über Tastenkürzel.

**B19 · Szenen-Suchfeld versteht keine Sätze; Rohwerte in den Kacheln**
- Route: `{t}/scenes`. Gerät: Desktop.
- Nachstellen: alle Chips abwählen, «Gegentore rechts aussen letzte drei Spiele» tippen.
- Erwartet: erkannte Chips, Antwort mit Basis; leere Suche mit neuesten Szenen und vier
  Beispielsuchen (SPEC 7.6).
- Passiert: die Chip-Vorschläge verschwinden, die Liste bleibt bei «163 Szenen aus dem letzten
  Spiel». Kacheln zeigen «throw_off», «Wurf», «Video 0:58» statt Spielzeit; alle Kacheln «0:09»
  lang; keine Beispielsuchen.
- Screenshot: `shots/b19-szenen-ohne-filter.jpg`
- Vorschlag: einfache Worterkennung auf die Chips; Ereignisnamen übersetzen; ohne Spielzeit
  «Video 0:58» weglassen oder als «ohne Spielzeit» sagen.

**B20 · «letzte 3 Spiele» meint «letzte 3 Spiele mit Video»**
- Route: `{t}/scenes`. Gerät: beide.
- Erwartet: die letzten drei Spiele (Thalwil, Stäfa, Horgen) oder ein ehrliches Wort.
- Passiert: Chip «letzte 3 Spiele», gerechnet über Thalwil, Stäfa und Rüti; Horgen (nur
  Spielbericht) fällt still heraus. Die Antwort «24 von 66» ist für die Frage der Aufgabe deshalb
  nicht dieselbe Zahl.
- Screenshot: `shots/b20-szenen-letzte3.jpg`
- Vorschlag: Chip «letzte 3 Spiele mit Video», oder die Spiele ohne Video aus dem Spielbericht
  mitzählen und sagen, dass sie keine Szenen haben.

**B21 · «Alle 24 abspielen» und «Als Tabelle» halten nicht, was sie sagen**
- Route: `{t}/scenes` → `{m}?tab=video&t=…` bzw. `{t}/matrix`. Gerät: Desktop.
- Erwartet: eine Folge aller 24 Szenen über drei Spiele; eine Tabelle derselben Antwort.
- Passiert: «Alle 24 abspielen» öffnet das Video eines Spiels an einer Stelle. «Als Tabelle» öffnet
  die alte Matrix mit zweiter Tab-Ebene «Szenen · Sammlungen · Spielzüge · Tabelle», Erklärsatz,
  «xG (Schätzung)», «Als Vorlage speichern»; die Filter sind weg.
- Screenshot: `shots/b21-als-tabelle.jpg`
- Vorschlag: Abspielen als Szenenfolge (wie B01); Tabelle als einfache Aufstellung der 24 Szenen
  (Spiel, Minute, Nummer), im selben Screen.

**B22 · Spieltag ist die alte Detail-Erfassung**
- Route: `{m}/matchday`. Gerät: Handy.
- Erwartet: Live-Streifen, sechs grosse Tasten (Tor wir, Tor Gegner, Gute Aktion, Fehler, Abwehr
  anschauen, Später anschauen), drei kleine, «zurücknehmen», «Pro Spielerin erfassen», «Link teilen»
  (SPEC 7.11).
- Passiert: Spielerraster (15 Felder) und sechs Aktionstasten pro Team, «Spieler wählen, dann
  Aktion», Kästchen «7-m-Wurf» (16 px), «Rückgängig», zwei Zurück-Wege («< Herren 1», «Zum Spiel»),
  Pille «Alles gespeichert». Kein «Link teilen». Erreichbar nur über ein Spiel, nicht vom Start.
  «Spieltag starten» steht auch bei längst gespielten Spielen mit Bericht im Mehr-Menü.
- Screenshot: `shots/b22-spieltag-handy.jpg`
- Vorschlag: Spieltag nach `#spieltag`; Detailebene hinter «Pro Spielerin erfassen»; auf dem Start
  am Spieltag einen Knopf «Spieltag starten» beim nächsten Gegner.

**B23 · Tab Zahlen ist die alte Statistikseite**
- Route: `{m}?tab=zahlen`. Gerät: beide.
- Erwartet: Tabellen Feld und Tor, leere Zellen leer, Ziel im Tor nur von Hand, Phasen mit Quelle,
  Laufleistung erst mit zugeordneten Spuren (SPEC 7.4).
- Passiert: Tabelle «Spielbericht» mit Spalten Fehlwürfe, Pfosten, Geblockt, Ballverluste und
  Dutzenden «0»; Wurfbild mit Grün, Rot, Gelb, Grau (Fremdfarben); «Torbild» in rot-weiss
  gestrichelten Rahmen aus dem Video; Wurfzonen; zwei Torhüter-Raster; «Laufleistung» mit
  «0.66 km», «24.5 km/h» aus 56 Sekunden Video; «Aufenthaltsorte»-Heatmap. 114 Ziele unter 44 px.
- Screenshot: `shots/b23-zahlen-alt.jpg`
- Vorschlag: nach `#zahlen` neu bauen; was nicht gemessen ist, weglassen.

**B24 · Onboarding: «Übernehmen» wartet 13 Sekunden ohne Wort; Neu laden überspringt Schritt 2**
- Route: `/onboarding`. Gerät: beide.
- Nachstellen: neues Konto, «Stäfa» suchen, «Übernehmen».
- Erwartet: der gewählte Knopf zeigt, dass etwas passiert, und ein Satz sagt was («Wir holen Spiele
  und Kader von handball.ch …»).
- Passiert: alle acht Knöpfe drehen und sind grau, 12,6 s (Desktop) bzw. 13,6 s (Handy). Wer in der
  Zeit neu lädt oder nach «Übernehmen» neu lädt, landet direkt in der App: Trikotfarbe und «Das ist
  nicht mein Team» entfallen.
- Screenshot: `shots/b24-uebernehmen-warten.jpg`
- Vorschlag: nur den geklickten Knopf drehen, Satz mit dem, was geholt wird; Schritt 2 auch nach
  Neu laden zeigen, bis bestätigt.

**B25 · Registrierung: Fehler auf Englisch, Bedingungen nicht verlinkt**
- Route: `/register`. Gerät: beide.
- Nachstellen: «Konto erstellen» ohne Eingaben.
- Erwartet: Deutsche Sätze an jedem Feld; Nutzungsbedingungen und Datenschutz lesbar.
- Passiert: «String should have at least 1 character», «value is not a valid email address: An
  email address must have an @-sign.»; das Kästchen wird nicht markiert. «Nutzungsbedingungen» und
  «Datenschutzerklärung» sind keine Links.
- Screenshot: `shots/b25-register-englisch.jpg`
- Vorschlag: Validierung im Formular auf Deutsch («Bitte Namen eingeben», «Das ist keine
  E-Mail-Adresse»), Links auf die Seiten.

**B26 · Erster Screen nach dem Onboarding: keine Aufgabe**
- Route: `{t}/matches` (neuer Verein). Gerät: beide.
- Erwartet: Spiele mit einer Aufgabe: erstes Video oder Demo-Spiel (SPEC 7.12).
- Passiert: Titel «Das letzte Spiel, noch ohne Video.», Hauptknopf «Spiel öffnen» (zu einem Spiel
  ohne Video), sofort das Banner «Als Vereinsadmin musst du die Zwei-Faktor-Anmeldung aktivieren»;
  kein Demo-Spiel. Am Handy steht bei einem Unentschieden «Zeichnen» statt «Unentschieden» (B50).
- Screenshot: `shots/b26-erster-screen-handy.jpg`
- Vorschlag: Hauptknopf «Video hochladen» zum letzten Spiel, zweiter Weg «Demo-Spiel ansehen»;
  Zwei-Faktor als Punkt am Konto (SPEC 5).

**B27 · Verein von Hand: alter Vierschritt-Assistent mit Einladungen**
- Route: `/onboarding` › «Verein von Hand anlegen». Gerät: Desktop.
- Erwartet: zwei Schritte, niemand wird eingeladen (SPEC 7.12).
- Passiert: «Schritt 1 von 4», Schrittleiste «Verein · Team · Team · Einladen» (Team doppelt);
  Schritt 4 «Lade Trainerkollegen und Spieler ein» mit Rollen Spieler/in, Elternteil usw.; im
  Kader-Schritt ein Knopf «Prüfen» (Wort ist belegt).
- Screenshot: `shots/b27-hand-anlegen-einladen.jpg`
- Vorschlag: Name und Farbe (Trikots wie beim handball.ch-Weg), Kader optional, fertig.

**B28 · Leerer Verein: Formular-Karte, geratene Gegnerfarbe, falscher Leer-Satz**
- Route: `{t}/matches`, `{t}/scenes` (FC Leer). Gerät: Desktop.
- Erwartet: ein Satz, eine oder zwei Aktionen, das gefüllte Layout blass dahinter (SPEC 7.13).
- Passiert: Start ist ein langes Formular in einer Karte mit Spiel | Training, Spielformat und vier
  vorbelegten Trikotfarben (Gegner rot, Gegner-Torhüter grün: geraten). Szenen sagt «0 Szenen aus 0
  Spielen.» und «Keine Szene mit Videozeit passt. Nimm einen Filter weg.», obwohl kein Filter aktiv
  ist.
- Screenshot: `shots/b28-leerer-verein.jpg`, `shots/b28b-leere-szenen.jpg`
- Vorschlag: «Noch kein Spiel. Lad das erste Video hoch.» mit Video wählen; Gegnerfarbe leer
  («Farbe offen»); Szenen «Szenen gibt es nach dem ersten Video.»

**B29 · Falsche oder kaputte Datei: keine Erklärung**
- Route: `{m}` nach Upload. Gerät: Desktop.
- Nachstellen: Textdatei bzw. zufällige Bytes als `.mp4` hochladen.
- Erwartet: was fehlgeschlagen ist, was bleibt, was zu tun ist (SPEC 7.13).
- Passiert: Textdatei: «Etwas ist schiefgelaufen. Bitte versuch es nochmals.» und «Fortsetzen».
  Kaputtes Video: rotes «Fehler», «Fehlgeschlagen · 8 %», «Fehlgeschlagen» überlappt «Video prüfen».
  Die Glocke meldet Fehlschläge nicht; «Die Videoanalyse ist fertig.» nennt das Spiel nicht.
- Screenshot: `shots/b29-kaputtes-video.jpg`, `shots/b29b-textdatei.jpg`
- Vorschlag: «Diese Datei ist kein Video, das wir lesen können (MP4, MOV, MKV). Der Spielbericht
  bleibt.» + «Andere Datei wählen»; Glocke mit Spielnamen und auch bei Fehlern.

**B30 · Team wechseln auf einer Spielseite: Kopf und Inhalt passen nicht**
- Route: `{m}` (Herren-Spiel). Gerät: Desktop.
- Nachstellen: Spiel öffnen, Team-Umschalter «Herren 1» › «U17 Juniorinnen».
- Erwartet: Spiele der U17.
- Passiert: Kopfzeile «U17 Juniorinnen», Seite bleibt das Herren-Spiel gegen Thalwil.
- Screenshot: `shots/b30-teamwechsel.jpg`
- Vorschlag: beim Wechsel auf Spiele des neuen Teams gehen.

**B31 · Gegnerfarbe eines Spiels nur über Umwege**
- Route: `{m}` › Mehr › Spiel bearbeiten. Gerät: beide.
- Erwartet: Farbchip neben dem Gegnernamen im Kopf antippen, fünf Trikots (ANLAUF 2).
- Passiert: im Dialog «Spiel bearbeiten» mit Resultat, Halbzeit, Spielformat und fünf
  Trikotfeldern («Eigene Feldspieler», «Eigener Torhüter», «Gegner Feldspieler», «Gegner
  Torhüter», «Schiedsrichter») und drei Erklärsätzen.
- Screenshot: `shots/b31-gegnerfarbe.jpg`
- Vorschlag: Chip im Kopf antippbar, fünf Trikots, sofort gespeichert.

**B32 · Alte Routen ohne Umleitung, zwei Umleitungen auf 404**
- Route: siehe Liste am Ende. Gerät: beide.
- Erwartet: alte Routen leiten um (SPEC 6).
- Passiert: 14 alte Seiten öffnen sich im alten Aufbau (u. a. `assistant`, `matrix`,
  `presentations` «Zum Zeigen», `assignments` «Aufgaben … die dir der Trainer gibt», `scouting`
  «Vorbereitungsbericht», `feed`, `schedule`). `/club/federation` (Verband, in SPEC unter Verein)
  ist 404, und `/settings/access-requests` leitet genau dorthin.
- Screenshot: `shots/b32-alte-route-assistent.jpg`, `shots/b32b-verband-404.jpg`
- Vorschlag: Umleitungen nach der Tabelle in SPEC 6; Verband-Seite bauen oder Umleitung auf Verein.

**B33 · Einwilligung: Spieler vorbelegt**
- Route: `/einwilligung/<token>`. Gerät: Handy (C).
- Erwartet: man wählt sich selbst; nichts vorbelegt.
- Passiert: «Für wen?» steht auf «#1 Andrin G.». Wer schnell tippt, willigt für den Torhüter ein.
  Jede Person mit dem Link kann für jede andere einwilligen (keine Prüfung); das ist bewusst so,
  sollte aber in der Bestätigung beim Trainer sichtbar sein. Kästchen 16 px, Kopf mit «Anmelden».
- Screenshot: `shots/b33-einwilligung.jpg`
- Vorschlag: «Bitte wählen» als erster Eintrag; nach dem Senden Name und Nummer gross bestätigen.

**B34 · Spielerseite und Kader bearbeiten im alten Aufbau, mit Ungemessenem**
- Route: `{t}/players/<id>`, `{t}?edit=1`. Gerät: Desktop.
- Passiert: «Saisonverlauf · 5 Spiele gespielt, an 4 beteiligt, 0× anwesend», Spalte «Torvorlagen»
  mit 0 (Pässe werden nicht gemessen), «Fehler»; Kader bearbeiten mit «Kein Konto», «Status»,
  «Einwilligungen pro Person und Zweck».
- Screenshot: `shots/b41-spielerseite.jpg`, `shots/b53-player-old-team-chips.jpg`
- Vorschlag: Torvorlagen und Anwesenheit weg; Seite im Seitenkopf-Aufbau.

**B35 · Mehr-Menü im Spiel voller alter Funktionen**
- Route: `{m}` › Mehr. Gerät: beide.
- Passiert: «Spielbericht als PDF, Matchkarte herunterladen, Spieltag starten, Spieltag: Szenen
  merken, Vorbereitung, Gegner-Profil, Daten austauschen, Spiel bearbeiten, Spiel löschen».
  «Matchkarte» und «Daten austauschen» sind unklar, Spieltag beim gespielten Spiel unnötig.
- Screenshot: `shots/b35-mehr-menue.jpg`
- Vorschlag: nur «Spielbericht hinzufügen», «Spiel bearbeiten», «Spiel löschen».

**B36 · Wörter im Tab Video**
- Route: `{m}?tab=video`. Gerät: beide.
- Passiert: «Tor Wir 5:08» (statt «Tor HC Zürichsee»), Unterzeilen «RR», «RL», «RA», Überschrift
  «4. bis 11.» (gemeint: Minute), «Spielerin hervorheben» bei einem Herrenteam, zwei Knöpfe
  «Teilen» auf einem Screen, «Mehr», «Tore im Spiel (44)».
- Screenshot: `shots/b37-video-tab.jpg`
- Vorschlag: Vereinsname statt «Wir», Positionen ausschreiben («Rückraum rechts»), «Minute 4 bis
  11», «Person hervorheben» oder nach Team-Geschlecht.

**B37 · Upload-Dialog bietet «Training» an**
- Route: «Video hochladen». Gerät: beide.
- Passiert: Segment «Spiel | Training» und Spielformat-Auswahl; Training ist nicht Umfang.
- Screenshot: `shots/b36-upload-dialog.jpg`
- Vorschlag: nur Spiel; neues Spiel mit Gegner und Datum, Rest später.

**B38 · Öffentliche Startseite verspricht, was nicht Umfang ist**
- Route: `/`. Gerät: beide.
- Passiert: «Spielbericht, Szenen, Statistiken, Spielzüge und drei Dinge … Ohne manuelles Tagging»,
  «Würfe, Tore, Torhüter, Laufwege», «Spieler und Eltern antworten direkt in der App».
- Screenshot: `shots/b40-startseite.jpg`
- Vorschlag: «Lad das Spielvideo hoch. Du bekommst drei Dinge und die Szenen dazu.»; Spieler- und
  Elternfunktionen weglassen.

**B39 · Doppelte Rückennummer auf der Taktikkamera**
- Route: Start (Szene 7:46), `{m}?tab=video`. Gerät: beide.
- Passiert: zwei eigene Spieler tragen die 15 (der Kader hat keine 15).
- Screenshot: `shots/b12-positionen-ohne-feld.jpg`
- Vorschlag: eine gelesene Nummer pro Moment nur einmal zeigen; unsichere Nummern weglassen oder
  als Prüfen-Frage stellen.

### P3: Schliff

**B40 · Startseite der App: Nächster Gegner und Tabelle**
- Route: `{t}/matches`. Gerät: beide. Nächster Gegner ist ein grosses leeres Minifeld mit einem
  Satz; die drei Fakten und die Tabelle (SPEC 7.1) fehlen; Kick-Zeile ohne «Analyse fertig seit».
  Am Handy keine eigene Sektion für die Szene von Punkt 1. `shots/b43-start-desk.jpg`.
  Vorschlag: Fakten aus Tabelle und Berichten, Tabelle darunter; ohne Daten den Block weglassen.

**B41 · Saison: Ballverluste mit Szenen, Rang fehlt**
- Route: `{t}/season`. «Ballverluste … 36 Szenen» (laut ANLAUF 10 nur aus dem Bericht, ohne
  Szenen); Titel und Seite ohne Rang und Tabelle. `shots/b42-saison.jpg`.

**B42 · Nächstes Spiel: Resultat-Platzhalter als Klötzchen, Upload als Kasten im Kasten**
- Route: `{m}` (HSG Rheinau). `shots/b44-naechstes-spiel.jpg`. Vorschlag: im Streifen Datum und
  Uhrzeit statt Platzhalter; Upload-Block ohne innere Karte, Kamera-Auswahl weg.

**B43 · Verein: «Verein» dreimal, roher Farbwähler, «Logo» statt Wappen**
- Route: `{o}/club`. `shots/b45-verein.jpg`. Vorschlag: Trikots wie im Onboarding, Vorschau mit
  dem Kopf, Wort «Wappen».

**B44 · Ziele unter 44 px**
- Team-Umschalter 28 px hoch, «Einrichten» 18 px, Banner-Schliessen 32 px, «Belege anzeigen» 16 px,
  «Video hochladen»-Links in der Spielliste 17 px, Namen im Team 29 px, Zahlen in Tabellen 20 bis
  24 px, Kästchen in Einwilligung und Spieltag 16 px. Gemessen bei 390 px.

**B45 · Prüfen am Handy**
- «Später weiter» bricht auf zwei Zeilen um; «Weiss nicht» zentriert, die anderen Antworten links.
  `shots/b47-pruefen-handy.jpg`.

**B46 · Anmelden und Registrieren als Karte, Keil losgelöst**
- `/login`, `/register`: Formular in einer Karte mit Rand und Fläche (ANLAUF 7: keine Karten), der
  Keil hängt auf dem Desktop unten links unter dem Text, «Anmelden» steht auf der Anmeldeseite oben
  noch einmal. `shots/b25-register-englisch.jpg`.

**B47 · Onboarding-Wörter**
- «Mannschaft suchen» und «Team oder Verein» auf demselben Screen; «Hauptrunde - M2-02»;
  «Übernehmen» (besser «Das ist mein Team»); «ihr» und «du» gemischt; «22 Spielerinnen und
  Spieler» bei einem Männerteam; Titel «Willkommen» über «Schritt 1 von 2». `shots/b49-onboarding-suche.jpg`.

**B48 · Zwei-Faktor-Banner auf jedem Screen**
- Alle App-Seiten. Laut SPEC 5 ein Punkt am Konto. Kostet am Handy eine Zeile über dem Kopf.

**B49 · Seitentitel im Browser fehlen**
- Team und Prüfen heissen nur «Handball Intelligence» (Tab-Titel).

**B50 · «Zeichnen» statt «Unentschieden»**
- Spielliste bei 29:29 (Pfadi Winterthur gegen Kadetten Schaffhausen). Ursache: derselbe
  Text-Schlüssel `anlauf.draw` für das Zeichenwerkzeug und das Unentschieden.
  `shots/b26-erster-screen-handy.jpg`.

**B51 · Taktikkamera am Handy zu klein**
- `{m}?tab=video` bei 390 px: das ganze Feld quer, Punkte etwa 8 px, Nummern unlesbar.
  `shots/b38-kamera-handy.jpg`. Vorschlag: am Handy die angegriffene Hälfte zeigen.

**B52 · Szenen: Highlights-Satz falsch**
- «Nach dem nächsten Spiel mit Video.» obwohl drei Spiele Video haben; Seitenleiste mit Links
  «Spielzüge» und «Tabelle»; «Mehr: Ereignisliste, gespeicherte Suchen, eigene Tags».
  `shots/b20-szenen-letzte3.jpg`.

**B53 · 404 innerhalb der App ohne Rahmen**
- `{o}/gibtsnicht`: 404 ohne Navigation, nur «Zur Startseite». `shots/b52-404.jpg`. Vorschlag:
  im App-Rahmen anzeigen, Seitenkopf mit Keil.

**B54 · Abmelden ohne Rückmeldung; Upload-Race im Seed**
- Nach «Abmelden» kommt die Anmeldeseite ohne «Du bist abgemeldet.» Ausserdem brach `make seed`
  beim ersten Lauf mit 404 auf `POST /videos/<id>/parts` direkt nach dem Anlegen des Videos ab
  (zweiter Lauf auf frischer Datenbank lief durch). Möglicher Wettlauf beim Upload, im Browser
  nicht nachgestellt.

---

## Seiten, die noch nicht «Anlauf» sind

Ganz im alten Aufbau (alte Struktur, alte Wörter, teils nur mit neuen Schriften und Farben):

| Route | Was man sieht |
|---|---|
| `{m}?tab=spiel` unterhalb der drei Dinge | zweite Drei-Dinge-Liste, Kennzahlen, xG, Torschützen, Feedback, Highlights |
| `{m}?tab=zahlen` | alte Statistikseite (Wurfbild, Torbild, Wurfzonen, Torhüter, Laufleistung) |
| `{m}` Tab Video nach dem Upload | Einrichtungs-Assistent und Unter-Tabs Ereignisse, Abwehrsysteme, Kommentare, Feedback |
| `{m}` Verarbeitung und Fehler | technische Schrittliste |
| `{m}` Zustand «Kein Video» und «vor dem Spiel» | Upload-Karte im Kasten, Kamera-Auswahl, Aufnahmetipps |
| `{m}/matchday` (auch `live`, `marks`) | alte Live-Erfassung, `?mode=marks` «Spieltag: Szenen merken» |
| `{m}/scouting` | «Vorbereitungsbericht» |
| `{o}/collections/<id>/present` | nicht gebaut |
| `/s/<token>` | geteilte Seite mit Produktkopf und nackter Liste |
| `/einwilligung/<token>` | Formular mit Produktkopf, ohne Seitenkopf und Wappen |
| `/register`, `/login`, `/auth/forgot` | Karten-Formular |
| `/onboarding` Weg «Verein von Hand» | Vierschritt-Assistent mit Einladen |
| `{t}` leer (neuer Verein) | Formular-Karte «Leg dein erstes Spiel an» |
| `{t}/assistant` | alter Chat-Assistent («nicht eingerichtet») |
| `{t}/matrix` | Pivot-Tabelle mit zweiter Tab-Ebene |
| `{t}/collections` | «Sammlungen» mit Tab-Ebene Szenen · Sammlungen · Spielzüge · Tabelle |
| `{t}/playlists`, `{t}/presentations` («Zum Zeigen»), `{t}/assignments` («Aufgaben») | alte Objekte statt Sammlung |
| `{t}/plays`, `{t}/plays/new`, `{o}/plays/<id>` | Spielzüge (erlaubt, aber im alten Aufbau) |
| `{t}/training`, `{o}/drills` | Planung und Übungen (sollten aus der Navigation, sind über Schnellsuche erreichbar) |
| `{t}/official` | «Abgleich mit handball.ch» |
| `{t}/join-requests` | «Beitrittsanfragen» |
| `{t}/players/<id>` | Spielerseite mit Anwesenheit und Torvorlagen |
| `{t}?edit=1` | «Kader bearbeiten» |
| `{o}/schedule`, `{o}/feed`, `{o}/consents` | Spieler-Seiten («Meine Termine», «Deine Szenen», «Einwilligungen»), ohne Teamfunktionen erreichbar |
| `{o}/me`, `{o}/me/security`, `{o}/me/data` | Formulare im alten Aufbau, ohne Sprache, Name, Mitteilungen |
| `{o}/club`, `{o}/club/teams`, `{o}/club/billing` | Formulare; Rollen mit Spieler/in und Elternteil; Abo als Karte |
| `{o}/club/federation` | 404 |
| Dialoge «Video hochladen», «Spiel bearbeiten», «Link zum Ansehen», Schnellsuche, Mitteilungen | alter Dialog-Aufbau, Spiel/Training-Segment |
| `/` | Marketing-Startseite mit alten Versprechen |
| 404 (`/gibtsnicht`, `{o}/gibtsnicht`) | einfache Seite ohne Keil und ohne App-Rahmen |
| E-Mails | nur Text, im Konsolen-Log geprüft (siehe unten) |

---

## Nicht getestet und warum

- **Echte Analyse eines Spielvideos**: Die lokale GPU-Pipeline lief nur mit dem synthetischen
  Demo-Video (60 s) und einem 20-Sekunden-Testbild; die Dauer «etwa 40 Minuten» und der Ablauf
  bei einem echten Spiel waren nicht prüfbar. Die Testbild-Analyse meldete «Analyse fertig.
  Statistik und Szenen stehen bereit.» nach 18 Sekunden, ohne sinnvolle Szenen.
- **E-Mails im Aussehen**: Der lokale Stack nutzt das Konsolen-Backend. Geprüft habe ich nur Betreff
  und Text der Bestätigungsmail («Bitte bestätige deine E-Mail-Adresse», reiner Text, de-CH).
  HTML-Mails, Passwort-Mail und Magic-Link-Mail im Postfach: nicht gesehen.
- **Prüfen-Fragen ausser «Passt das Spielfeld?»**: Das Demo erzeugt keine «Wer ist das?»- oder
  «Tor oder kein Tor?»-Fragen; Tastaturbedienung mit Rückennummern nicht prüfbar.
- **Echtes iPhone / Safari**: nur Chromium mit Handy-Viewport und Touch (OPEN_QUESTIONS Q-QA-1).
- **Mehrere Personen gleichzeitig** (zweiter Trainer, «Jemand fürs Filmen oder Prüfen einladen»):
  Einladungsmail nicht zustellbar, deshalb nicht durchgespielt. Ein zweites Konto, das einen schon
  übernommenen Verein wählt, bekommt «Anfrage gesendet. Die Admins von TV Thalwil melden sich in
  der App.»; was danach passiert, habe ich nicht verfolgt.
- **Teamfunktionen eingeschaltet** (Spieler- und Elternsicht): nicht Teil dieser Runde.
- **Kontrast gemessen**: nur Stichprobe nach Augenmass auf Blau und Rot; keine axe-Messung.
- **Handy-Upload**: Dialog und Weg identisch geprüft, Upload selbst nur am Desktop.

Alle Rohaufnahmen und Skripte liegen nicht im Repository (Scratchpad der Testsitzung); die
Screenshots unter `shots/` reichen zum Nachstellen.
