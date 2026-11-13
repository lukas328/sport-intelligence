# UX-Test Runde 3: Abnahme

Stand: 13. November 2026. App `claude/trikot-ui` (Commit cb6aa90), in `claude/ux-test` zusammengeführt;
Website `claude/site-anlauf` (Commit 7907501), statisch gebaut, lokal auf Port 3100, App-Adresse auf
den lokalen Stack. Frische Datenbank (Cache von handball.ch leer), `make seed`, Produktions-Build,
Playwright mit Chromium: Desktop 1280, Handy 390, grosse Schrift als 300 CSS-Pixel bei Faktor 1,3.

Grundlage: `docs/ux-test-status.md` auf `claude/trikot-ui` (Spalte «Runde 2», Tabelle N01 bis N31).
Nichts davon ist übernommen; jede Zeile unten ist nachgestellt. Gewichte wie in Runde 1 und 2.

---

## (c) Schlussbewertung

### Was jetzt gut ist

- **Hans kommt durch.** Website › Teamname › sein Team mit Rang und Serie (vor dem Konto, kalt in
  1,8 s, der erste Satz nach 0,15 s) › E-Mail › Link (24 Stunden gültig) › Spiele mit Rang, Tabelle,
  Torschützen › Video › «Die Analyse läuft. Du kannst die Seite schliessen» › ehrliche Mail. Ohne
  Unterbruch, ohne Passwort, ohne Banner, nichts doppelt gefragt. Ränder halten: Tippfehler («Meintest
  du …?»), belegtes Team (Hinweis vorher), langsamer Verband («handball.ch antwortet heute langsam …
  Trotzdem speichern»), Drosselung mit eigenem Satz.
- **Die Kernwege des Zielbilds funktionieren**: drei Dinge mit Szenenfolge, Suche mit Gegner, Nummer
  und Zeitraum, Sammlung bearbeiten (Notiz an der Stelle, Rückgängig nach Entfernen), am Bildschirm
  zeigen, geteilte Seite mit «Feld von oben» und lesbaren Minifeldern, Prüfen mit verschiebbaren
  Ecken (44 px), Spieltag mit Spieluhr, «Zurücknehmen», allen Tasten und **funktionierend ohne Netz**.
- **Ehrlich**: keine erfundenen Läufe, kein xG, kein Ballbesitz, keine Positionen ohne bestätigtes
  Feld, Wurfquote passt zu den angezeigten Würfen, Mail verspricht nur, was da ist.
- **Lesbar**: auf Einstieg und Start nichts unter 14 px, auf der Website nichts unter 16 px, kein
  seitlicher Überlauf bei 390 und 300 px.

### Verbleibende Schwächen, nach Gewicht

1. **A02 (P2) Der Moment nach einem Video ohne erkannte Tore** ist noch geschwätzig und widersprüchlich:
   Mail «1 Fragen an dich», Start «2 Fragen offen …» und darunter drei weitere Sätze, die dasselbe
   sagen, dazu «Fürs Team zusammenstellen» bei 0 Szenen und «Kein Ding · 0 Szenen» in der Liste.
2. **A01 (P2) Grosse Schrift am Handy**: Der Teamname in der Kopfzeile wird zu «S / G.».
3. **N18 / B53 (P3)** unbekannte Spiel-IDs antworten mit HTTP 200; **N22 (P3)** ein ungültiger Link
   führt nicht zurück zur Teamwahl.
4. **Reste von altem Produkt hinter Umwegen (A07, P3)**: «Spielzüge» mit zweiter Tab-Ebene,
   «Gegner-Profil», «Zum Zeigen»; **Fachwort «Hauptrunde - M1-01»** in der Saison (A04).
5. Kleinigkeiten: Spieltag-Liste mit Handy-Uhrzeit neben der Spieluhr (A03), veralteter Hinweis unter
   «Mehr zum Spiel» (A05), Vereinsname statt Teamname in Prüfen (A06), Videozeit in der Szenenfolge
   (A08), Platzhalter-Block beim Laden (A09), negativer Balken ohne Zahl (A10).

Keiner dieser Punkte blockiert eine Aufgabe.

### Was in allen drei Runden nie geprüft werden konnte

- **Ein echtes Spielvideo** (60 Minuten, Handy oder Vereinskamera, echte Halle): lokal nur das
  synthetische 60-Sekunden-Demo und ein 20-Sekunden-Testbild. Damit unbekannt: echte Dauer der
  Analyse, Qualität der drei Dinge, Zahl und Art der Prüfen-Fragen (die **Anwurf-Frage** kam nie vor),
  wie sich Feldecken an einem echten Hallenbild ziehen lassen.
- **Echte Geräte**: kein iPhone, kein Android, kein Safari; grosse Systemschrift nur nachgestellt
  (300 CSS-Pixel), nicht mit iOS-Dynamic-Type oder Android-Schriftgrösse.
- **Mails im Aussehen**: nur Betreff und Text im Konsolen-Log, nie ein echtes Postfach (HTML,
  Vorschauzeile, Spam-Filter, Link auf dem Handy öffnen).
- **Netz in der Halle**: offline nur als Schalter im Browser, kein schwaches oder wechselndes Netz.
- **Ein echter Ablauf des Links nach 24 Stunden** (nur ungültiger Link nachgestellt).
- **Mehrere Personen**: zweiter Trainer, Anfrage an einen belegten Verein bis zur Freigabe,
  eingeschaltete Teamfunktionen für Spieler und Eltern.
- **Echte Personen**: alle Zeiten für Hans sind Schätzungen (150 Wörter pro Minute, Daumentippen),
  kein Test mit einem echten Trainer über 55.
- **Hosting der Website**: Weiterleitungen nur im statischen Export geprüft (`/aufnahme/` →
  `/de/aufnahme/` je nach Sprache des Browsers).
- **Unentschieden** (B50): in keinem der geprüften Datensätze kam eines vor.

### Urteil

Ja, ich würde Hans die App so geben: Er sieht ohne Konto in einer Minute etwas Nützliches über sein
Team, kommt ohne Hilfe bis zum ersten Video und wird nirgends mehr angelogen oder in eine Sackgasse
geschickt. Vorher würde ich zwei Dinge erledigen: den Start nach einem Video ohne Tore auf einen
Satz und eine Aufgabe kürzen (A02) und den Teamnamen bei grosser Schrift lesbar machen (A01). Das
eigentliche Risiko liegt nicht mehr in der Oberfläche, sondern in dem, was ich nie prüfen konnte: wie
gut die Analyse mit einem echten Hallenvideo ist, denn davon hängt ab, ob die drei Dinge kommen.

---

## (a) Nachgeprüfte Zeilen

Status: **behoben** · **teilweise** (was fehlt) · **offen** · **nicht prüfbar** (Grund).

### Die dreizehn Punkte der Bau-Session

| Punkt | Ergebnis | Bild |
|---|---|---|
| Spieltag ohne Netz, Spieluhr, «Zurücknehmen» | **behoben**: Service Worker registriert; offline erfasst («1 noch nicht hochgeladen»), offline neu geladen: Seite und Eintrag da; online: ein Eintrag, kein Doppel. «Uhr starten», Uhr läuft (00:03 …), «Zurücknehmen» entfernt den letzten Eintrag, «2 Minuten», «Time-out», «Halbzeit», «Link teilen» da. Rest: A03. | `shots/k01-spieltag.jpg`, `shots/k02-spieltag-offline.jpg` |
| Erstes eigenes Video ohne erkannte Tore, Mail, Start | **teilweise**: Tab Video zeigt Video und «Die Analyse ist fertig. Sie hat in diesem Video keine Tore gefunden.» (keine Werkbank, N04 behoben). Mail «Die Analyse gegen TSV Fortitudo Gossau 2 ist fertig … 1 Fragen an dich, dann zeigt sie mehr» (ehrlich, aber siehe A02). Start: vier Sätze (A02). | `shots/w02-hans-spiele-bis-start.jpg`, `shots/a02-start-nach-erstem-video.jpg` |
| Einstieg kalt, neuer Ort | **behoben**: SG Wädenswil/Horgen in leerer Datenbank: erster Text nach **0,15 s** («Männer 1. Liga · SG Wädenswil/Horgen … Wir holen die Spiele von handball.ch. Das dauert einen Moment.»), Rang und Torschützen nach **1,8 s**. Warm (zweites Konto, gleiches Team): Team in unter 4 s (nicht feiner gemessen). | `shots/k03-einstieg-kalt.jpg` |
| Langsamer Verband | **behoben**: künstlich 25 s Verzögerung; nach 8,1 s «handball.ch antwortet heute langsam. Du kannst warten oder dein Team trotzdem speichern: Die Zahlen kommen später dazu.» mit «Trotzdem speichern», «Anderes Team». | `shots/k04-langsam.jpg` |
| Belegtes Team | **behoben** (Vorschau): «Dieses Team nutzt Handball Intelligence schon. Speichern schickt eine Anfrage an die Leute, die es dort verwalten.» Seite nach dem Link nicht erneut geprüft. | `shots/k05-belegt.jpg` |
| Grosse Schrift bei 300 px | **teilweise**: Vereinsname im Kopf bricht nach «/» um, E-Mail im Postfach-Satz bricht um, nichts läuft seitlich über. In der Handy-Kopfzeile wird der Teamname zu «S / G.» (A01). | `shots/a01-kopf-grosse-schrift.jpg` |
| Wurfquote und «Bestätigt» | **behoben**: Tim Baumann 17 Tore, 20 Würfe, 85 %; «7 m» leer ohne Versuch. Zahlen: «alle Tore bestätigt» bei Baumann, Graf, Kunz, Keller …, leer bei Frei. | `shots/k11-spieler.jpg`, `shots/k10-zahlen.jpg` |
| «Mehr zum Spiel» | **behoben**: nur noch Spielverlauf und Highlights; kein Ballbesitz, keine Angriffe, kein «Daran arbeiten», kein Feedback. Die Beschreibung daneben verspricht noch «Vergleich, Torschützen, Highlights, Feedback, Marken» (A05). | `shots/k12-mehr-zum-spiel.jpg` |
| Feldecken am Handy | **behoben**: vier Griffe je 44 × 44 px. | `shots/k08-ecken.jpg` |
| Künftiges Spiel | **behoben**: öffnet Tab Spiel mit «Vor dem Spiel», «Spieltag starten», Gegner mit «Farbe offen · Welche Farbe trägt HSG Rheinau?». Rest: A05. | `shots/k09-zukunft.jpg` |
| Suche mit Gegner und Nummer; Tippfehler im Einstieg | **behoben**: «Paraden gegen Stäfa» › Chip «gegen BSV Stäfa-Uerikon», 11 Szenen; «Tore von Nummer 11» › Chip «Nummer 11», 11 Szenen; «Wädenswill» › «Kein Team genau wie «Wädenswill». Meintest du eines von diesen?» mit SG Wädenswil/Horgen. | `shots/k06-tippfehler.jpg` |
| Geteilte Seite | **behoben**: Minifelder als kleine Taktikbilder lesbar, Zeiten wie in der App (35:51), «1 Mal geöffnet», «Der Link gilt bis 13. Dezember». | `shots/k07-geteilt-minifelder.jpg` |
| Abgelaufener Link | **teilweise**: Ein ungültiger Link zeigt «Der Link ist ungültig oder abgelaufen.» und «Anmelden», ohne Weg zurück zur Teamwahl. Den Fall «echt abgelaufen, Token bekannt» (dann soll «Neuen Link an … schicken» kommen) konnte ich nicht nachstellen (24 Stunden). | `shots/k16-abgelaufen.jpg` |
| Website-Links mit Sprachpfad | **behoben**: Filmanleitung zeigt auf `https://handball-ai.ch/de/aufnahme/`; die Website leitet `/aufnahme/` je nach Browsersprache weiter (de-CH › `/de/aufnahme/`, sonst `/en/aufnahme/`). | – |

### N01 bis N31 (Runde 2)

| # | Befund | Status | Beobachtung |
|---|---|---|---|
| N01 | Spieltag ohne Netz | **behoben** | siehe oben |
| N02 | Offline-Eintrag doppelt | **behoben** | ein Eintrag nach dem Hochladen |
| N03 | Einstieg 16 s «…» | **behoben** | 0,15 s Satz, 1,8 s Rang (kalt) |
| N04 | Tab Video nach erstem Video: Werkbank | **behoben** | Video, Satz, Link «Ereignisse und Kommentare von Hand» |
| N05 | Mail ohne drei Dinge | **teilweise** | Mail ehrlich; «1 Fragen» und Zahl passt nicht zum Start (A02) |
| N06 | Filmanleitung ohne Sprachpfad | **behoben** | `/de/aufnahme/` |
| N07 | Geteilte Minifelder | **behoben** | |
| N08 | Handy: «Suchen» fehlt | **behoben** | Lupe in der Kopfzeile |
| N09 | Team belegt: Sackgasse | **behoben** (Vorschau) | Hinweis vor dem Speichern |
| N10 | Tippfehler | **behoben** | «Meintest du …?» |
| N11 | Grosse Schrift: Namen, E-Mail | **teilweise** | Kopf und E-Mail brechen um; Kopfzeile «S / G.» (A01) |
| N12 | Wurfquote, «Bestätigt», 7 m | **behoben** | |
| N13 | «1 Frage» wird zu sechs | **behoben** | «1 Frage offen, danach Fragen zu den Personen im Bild» |
| N14 | Spieltag: Uhr, Rückgängig, Tasten | **behoben** | Rest A03 |
| N15 | Link 15 Minuten | **behoben** | «Er ist 24 Stunden gültig» |
| N16 | Künftiges Spiel verlangt Video | **behoben** | Rest A05 |
| N17 | Feldecken klein | **behoben** | 44 px |
| N18 | App-404 mit 200 | **teilweise** | unbekannte Adresse 404; unbekannte Spiel-ID 200 (wie von der Bau-Session angegeben) |
| N19 | Drosselung beschuldigt handball.ch | **behoben** | «Das waren viele Suchen in kurzer Zeit. Warte eine Minute, dann geht es weiter.» |
| N20 | Anrede mit E-Mail-Teil | **behoben** | «Hallo» |
| N21 | Gleiche Adresse: zweiter Verein | **behoben** | Weg mit Teamnamen: «FC Leer Herren» und «FC Leer Damen» im selben Verein |
| N22 | Abgelaufener Link | **teilweise** | siehe oben |
| N23 | Folge anders als Liste | **behoben** | Folge beginnt mit Thalwil wie die Liste; Untertitel mit Videozeit (A08) |
| N24 | Alte Sätze nach der Analyse | **behoben** | «Die Analyse ist fertig.»; Schliessen-Satz bleibt stehen |
| N25 | «Hauptrunde - M1-01», «Frei 3/1» | **teilweise** | Telegramm «Frei 3 (1 vom 7-m)»; Saison-Kopfzeile noch «Männer 1. Liga, Hauptrunde - M1-01» (A04) |
| N26 | Unbekannte Gegnerfarbe | **behoben** | «Farbe offen · Welche Farbe trägt HSG Rheinau?» mit fünf Trikots |
| N27 | Beispiel der Website | **behoben** | «Der Vereinsname oder der Ort reicht.»; in der App sucht der Ort |
| N28 | Website und App bei der Datei | **behoben** | App: «Am besten das ganze Spiel in einer Datei … Eine zweite Datei … wird gespeichert und abgespielt, ausgewertet wird aber nur die erste.» Website: «Am einfachsten ist das ganze Spiel in einer Datei.» |
| N29 | Notiz ganz unten | **behoben** | «Notiz danach» an jedem Eintrag |
| N30 | Entfernen ohne Rückgängig | **behoben** | «Entfernt. Rückgängig», funktioniert (`shots/k13-entfernt.jpg`) |
| N31 | «eigene Tags» | **behoben** | «eigene Stichwörter» |

### Zeilen aus Runde 1, die in Runde 2 offen waren

| # | Befund | Runde 2 | Runde 3 | Beobachtung |
|---|---|---|---|---|
| B08 | Tab Spiel: Altes unter den drei Dingen | teilweise | **behoben** | siehe «Mehr zum Spiel»; Gesamtbild `shots/k17-spiel-desk.jpg` |
| B10 | Einrichtungs-Assistent im Tab Video | teilweise | **behoben** | auch nach neuem Video |
| B15 | Geteilte Seite | teilweise | **behoben** | |
| B17 | Teilen: Zustand danach | teilweise | **behoben** | «1 Mal geöffnet», Gültigkeit, «Link kopieren», «Link sperren» |
| B18 | Suchen am Handy | neu kaputt | **behoben** | |
| B19 | Suche versteht Sätze | teilweise | **behoben** | Gegner und Nummer |
| B22 | Spieltag | teilweise | **behoben** | |
| B23 | Tab Zahlen | teilweise | **behoben** | |
| B24 | Warten im Einstieg | teilweise | **behoben** | |
| B28 | Leerer Verein | nicht geprüft | **teilweise** | Start: «Noch keine Spiele. Leg dein erstes Spiel an» mit Gegner, Anpfiff, Heim/Auswärts, Rest hinter «Mehr» (gut). Szenen sagt «0 Szenen aus 0 Spielen.» mit Suchchips und «Szenen aus dem letzten Spiel», statt eines Satzes, dass es Szenen nach dem ersten Video gibt. `shots/k15-leerer-verein.jpg` |
| B29 | Falsche Datei | teilweise | **behoben** | Textdatei: «Das Video liess sich nicht lesen. Diese Datei ist kein Video …» `shots/k14-textdatei.jpg` |
| B34 | Spielerseite | teilweise | **behoben** | |
| B40 | Nächster Gegner doppelt | teilweise | **behoben** | einmal |
| B41 | Saison: Ballverluste, Rang | nicht geprüft | **behoben** | Ballverluste «aus dem Spielbericht», ohne Szenen; echter Verein: «Rang 4, 12 Punkte» in der Kopfzeile, Tabelle |
| B44 | Ziele unter 44 px | teilweise | **teilweise** | Feldecken und Tabellenzahlen 44 px; Namen in Teamlisten unverändert (wie angekündigt) |
| B46 | Anmelden: Keil, doppeltes «Anmelden» | teilweise | **teilweise** | ein «Anmelden»; Keil bleibt (Gestaltungsentscheid) |
| B47 | Onboarding-Wörter | teilweise | **teilweise** | siehe N25 / A04 |
| B49 | Seitentitel | teilweise | **behoben** | «Rückzug und rechter Flügel · Am Bildschirm · Handball Intelligence» |
| B50 | «Zeichnen» statt «Unentschieden» | nicht geprüft | **nicht prüfbar** | kein Unentschieden in den Daten; Schlüssel `anlauf.drawResult` = «Unentschieden» vorhanden |
| B53 | 404 | teilweise | **teilweise** | wie N18 |
| H04 | Team nach erstem Video | behoben | **behoben** | jetzt «Bei einer Person fehlt noch etwas», Einwilligung einmal in der Seitenspalte |
| H05 | Erstes Video | teilweise | **behoben** | Link `/de/aufnahme/`, Schliessen-Satz bleibt |
| H06 | Meldung «fertig» | behoben, neues Problem | **teilweise** | wie N05 |
| H10 | Wörter für Hans | teilweise | **teilweise** | nur noch «Hauptrunde - M1-01» in der Saison gefunden |
| H14 | Saison-Verlauf Beschriftungen | nicht geprüft | **teilweise** | Namen gekürzt («Unters.», «Andelf.») und lesbar; der negative Balken (Pfadi, −20) hat keine Zahl (A10) |
| Z4 | Versprechen Nachricht | teilweise | **teilweise** | wie N05 |
| Z5 | Ballbesitz, Angriffe | teilweise | **behoben** | |
| Z7 | Filmanleitung | teilweise | **behoben** | |
| – | Anwurf-Frage in Prüfen | nicht geprüft | **nicht prüfbar** | Beim Testvideo kamen «Passt das Spielfeld?» und eine zweite Frage; eine Anwurf-Frage nie |

### Zählung

| | Zeilen | behoben | teilweise | offen | nicht prüfbar |
|---|---|---|---|---|---|
| N01 bis N31 | 31 | 26 | 5 | 0 | 0 |
| Offene Zeilen aus Runde 1 (B, H, Z) | 28 | 18 | 9 | 0 | 1 |
| Anwurf-Frage | 1 | 0 | 0 | 0 | 1 |
| **Total** | **60** | **44** | **14** | **0** | **2** |

Die dreizehn Punkte der Bau-Session (oben in 14 Zeilen, weil Suche und Tippfehler getrennt stehen) sind in diesen Zeilen enthalten: 11 behoben, 3 teilweise.

---

## (b) Neue Befunde

| Gewicht | Anzahl |
|---|---|
| P1 | 0 |
| P2 | 2 |
| P3 | 8 |
| **Total** | **10** |

**A01 · P2 · Handy mit grosser Schrift: Teamname in der Kopfzeile unlesbar**
- Route: alle App-Seiten. Gerät: Handy 300 px (390 px bei 130 %).
- Nachstellen: als Hans angemeldet, grosse Schrift.
- Erwartet: «SG Wädenswil/Horgen» (zur Not gekürzt) lesbar.
- Passiert: Die Kopfzeile zeigt links nur «S» über «G.»: Der Name wird auf einen Buchstaben pro Zeile
  zusammengedrückt, weil Glocke, Lupe, «+ Video» und Konto den Platz nehmen. Die Zahl an der Glocke
  liegt über dem Symbol.
- Screenshot: `shots/a01-kopf-grosse-schrift.jpg`
- Vorschlag: unter etwa 340 px das Wort «Video» weglassen (nur «+») oder den Teamnamen in eine
  eigene Zeile unter die Symbole setzen; Mindestbreite für den Namen.

**A02 · P2 · Nach einem Video ohne erkannte Tore: widersprüchliche Zahlen, vier Sätze**
- Route: Mail, Start, Spielliste. Gerät: Handy.
- Nachstellen: Hans' Weg mit einem Video, in dem die Analyse keine Tore findet.
- Erwartet: ein Satz, eine Aufgabe («Die Analyse hat keine Tore gefunden. 2 Fragen helfen ihr.
  Fragen beantworten»).
- Passiert: Mail «… ist fertig. **1 Fragen** an dich, dann zeigt sie mehr». Start: «Gewonnen.»,
  «Spiel öffnen», «Fürs Team zusammenstellen» (es gibt 0 Szenen), «Prüfen · **2 Fragen** offen,
  danach Fragen zu den Personen im Bild», «Die Analyse ist fertig, noch ohne drei Dinge.», «2 Fragen
  in Prüfen, dann zeigt sie mehr.», «Fragen beantworten», «Spielbericht hinzufügen» (der Bericht von
  handball.ch ist schon da), «Für drei Dinge braucht es mehr Tore mit Video. Die Szenen findest du
  unter Video.» (es gibt keine). Spielliste: «Kein Ding · 0 Szenen».
- Screenshot: `shots/a02-start-nach-erstem-video.jpg`, `shots/w02-hans-spiele-bis-start.jpg`
- Vorschlag: eine Zahl für Mail und Start (zum Zeitpunkt der Mail), Plural richtig; ohne Szenen
  kein «Fürs Team» und kein Verweis auf Szenen; ein Block statt vier Sätzen; in der Liste «noch keine
  Tore erkannt».

**A03 · P3 · Spieltag: Liste mit Uhrzeit des Handys neben der Spieluhr**: Die Uhr zeigt «00:04 ·
1. Halbzeit», die Einträge in «Bisher» stehen mit «07:12» (Uhrzeit). Für den Trainer am Spielfeldrand
zwei verschiedene Zeiten. `shots/k01-spieltag.jpg`. Vorschlag: Spielzeit beim Eintrag, Uhrzeit
höchstens klein dahinter.

**A04 · P3 · «Hauptrunde - M1-01» in der Saison**: Kopfzeile der Saison beim echten Verein «Saison
2026/27 · Männer 1. Liga, Hauptrunde - M1-01 · nach 12 Spielen». Rest von N25. `shots/a03-saison-echter-verein.jpg`

**A05 · P3 · Veralteter Hinweis bei «Mehr zum Spiel»; «Highlights teilen» vor dem Spiel**: Neben
«Mehr zum Spiel» steht «Vergleich, Torschützen, Highlights, Feedback, Marken», drin sind nur
Spielverlauf und Highlights. Beim künftigen Spiel stehen «Highlights teilen» und dieselbe
Beschreibung, obwohl es noch nichts gibt. `shots/a06-zukunft-mehr.jpg`

**A06 · P3 · Prüfen nennt den Verein statt des Teams**: Streifen «Prüfen · HC Wädenswil gegen TSV
Fortitudo Gossau 2», überall sonst «SG Wädenswil/Horgen» (Rest von H11). `shots/a04-pruefen-vereinsname.jpg`

**A07 · P3 · Altes Produkt hinter Umwegen**: «Spielzüge» (aus der Seitenspalte der Szenen) mit
zweiter Tab-Ebene «Szenen · Sammlungen · Spielzüge · Tabelle»; «Gegner-Profil» (Mehr-Menü) mit dem
alten Formular «Spieler hinzufügen … Speichern»; `presentations` («Zum Zeigen») und `playlists` per
Adresse. Die Bau-Session hat sie bewusst stehen lassen; für Sandra sind es die einzigen Stellen, an
denen sie beim Herumgehen noch das alte Produkt trifft. `shots/a05-spielzuege.jpg`

**A08 · P3 · Szenenfolge mit Videozeit**: «Alle 24 abspielen» zeigt «TSV Thalwil-Gattikon · 0:09»
(Zeit im Video), die Liste daneben «7:46» (Spielzeit).

**A09 · P3 · Platzhalter-Block beim Laden des Teams**: In den ersten 1,8 Sekunden steht im Kopf statt
des Resultats ein schwarzer Block aus Balken (das «-:-» in der Ergebnisschrift). `shots/k03-einstieg-kalt.jpg`

**A10 · P3 · Saison-Verlauf: negativer Balken ohne Zahl**: Beim echten Verein hat das Spiel gegen
Pfadi (−20) nur einen gestrichelten Rahmen ohne «−20»; die positiven Balken tragen ihre Zahl.
`shots/a03-saison-echter-verein.jpg`

---

## Hans' ganzer Weg, einmal ohne Unterbruch

Handy 300 px (grosse Schrift), neues Konto, SG Wädenswil/Horgen, leerer Cache. Bilder:
`shots/w01-hans-website-bis-postfach.jpg`, `shots/w02-hans-spiele-bis-start.jpg`.

| # | Screen | Wörter | Felder | Warten | Text < 14 px | Stockt er? |
|---|---|---|---|---|---|---|
| 1 | Website, Farbe Rot, «Wie heisst dein Team?» | 522 (ganze Seite) | 1 | – | 0 | nein |
| 2 | `/einstieg?q=Wädenswil&farbe=rot`, Treffer | 160 | 1 | 4,8 s Seitenwechsel | 0 | nein |
| 3 | «Dein Team»: Satz nach 0,15 s, Rang nach 1,8 s | 78 | 0 | 1,8 s mit Satz | 0 | nein |
| 4 | «Wohin dürfen wir den Link schicken?» | 39 | 1 | – | 0 | nein |
| 5 | «Schau in dein Postfach.» (24 Stunden gültig) | 23 | 0 | – | 0 | nein |
| 6 | Spiele: Rang, Tabelle, Torschützen, «Video hochladen» | 250 | 0 | – | 0 | kurz: Teamname oben «S / G.» (A01) |
| 7 | Upload: drei Sätze, Satz zu zweiter Datei, Filmanleitung | 86 | 1 | – | 0 | nein |
| 8 | «Die Analyse läuft. Du kannst die Seite schliessen.» | 159 | – | 13 s bis fertig | 0 | nein |
| 9 | Tab Video: «Die Analyse ist fertig. Sie hat in diesem Video keine Tore gefunden.» | 45 | – | – | 0 | nein |
| 10 | Start nach der Analyse | 243 | 0 | – | 0 | **ja**: vier Sätze, 1 gegen 2 Fragen (A02) |

Bis zum ersten Nutzen (Screen 3): 3 Screens, 1 Feld, 2 Entscheidungen (Farbe freiwillig, Team), rund
240 Wörter in der App, 1,8 s Warten mit Satz. Runde 1: 6 Screens, 6 Felder, rund 500 Wörter, kein
Nutzen vor dem Konto.
