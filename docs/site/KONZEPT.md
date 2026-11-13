# Website «Handball Intelligence»: Konzept

Stand 12. November 2026. Grundlage: `docs/design/ux-reset/SPEC.md` (1, 2, 8, 9), `ANLAUF.md`,
`docs/design/brand2/taktik/README.md`, `docs/OPEN_QUESTIONS.md`, ADR 020, 026, 027, die Hilfe in
`apps/site/content/help`, der Bestand in `BESTAND.md`.

## 1. Botschaft

**Du filmst dein Spiel mit dem Handy, und Handball Intelligence zeigt dir drei Dinge zum
Mitnehmen, mit den Szenen dazu.**

Drei Belege:

1. **Drei Dinge statt hundert Zahlen.** Nach jedem Spiel drei Sätze mit einer Zahl, ihrer Basis
   und den Szenen dazu («7 von 24 Gegentoren aus dem Rückraum rechts, 7 Szenen»). Zu sehen als
   echtes Beispiel, ohne Konto.
2. **Ein Handy reicht.** Auf ein Stativ, hoch an der Mittellinie, das ganze Feld im Bild. Keine
   Kamera kaufen, nichts schneiden, nichts eintippen.
3. **Ehrlich.** Die Seite sagt, was die Analyse kann und was nicht. Geschätztes ist gestrichelt
   und heisst «geschätzt». Wo sie unsicher ist, fragt sie dich, statt zu raten.

Für wen, in dieser Reihenfolge: **Hans** (58, Trainer, Handy, Lesebrille): versteht in zehn
Sekunden, was es ist (Kopf), sieht in einer Minute, was er bekommt (drei Dinge, Demo), startet mit
einem Tipp. **Der Vorstand**: Preis, Daten, Sicherheit auf einen Blick, eine Seite zum
Weiterleiten. **Eltern und Spieler**: eine eigene Seite «Daten und Einwilligung», die ohne
Fachwörter sagt, was mit dem Video passiert.

## 2. Seitenplan

| Adresse | Titel in der Navigation | Aufgabe |
|---|---|---|
| `/{de,fr,en}/` | (Logo) | in zehn Sekunden verstehen, in einer Minute sehen, starten |
| `/so-funktioniert-es/` | So funktioniert es | drei Schritte, was man bekommt (echte App-Bilder), was es kann und was nicht |
| `/aufnahme/` | Filmen | Filmanleitung mit Bild der Halle, Datei, Aushang zum Drucken |
| `/demo/` | Demo-Spiel | ein erfundenes Spiel zum Anfassen, ohne Anmeldung, sichtbar als erfunden markiert |
| `/preise/` | Preise | drei Pläne, Testphase, Rechnung |
| `/hilfe/` | Fragen | häufige Fragen für Hans, darunter die Anleitungen mit Suche |
| `/daten/` | (Fuss) Daten und Einwilligung | für Eltern, Spieler, Vorstand |
| `/kontakt/` | (Fuss) Über uns und Kontakt | wofür wir stehen, Kontakt |
| `/agb/`, `/datenschutz/`, `/impressum/` | (Fuss) Rechtliches | bleibt, als Entwurf markiert |
| `/blog/` | (Fuss) Blog | bleibt: zwei echte Beiträge, beide zum Kern |
| `/funktionen/` | | leitet auf `/so-funktioniert-es/` weiter (alte Links) |

Rechts in der Kopfzeile: «Anmelden» (Textlink) und «Kostenlos starten» (Tinte, auf `/einstieg`
der App). Die Wortmarke steht zweizeilig (Zeichen rund 45 px hoch), damit sie lesbar ist. Sonst nichts:
keine Sprachkürzel als einzige Beschriftung (die Sprachwahl steht im Fuss mit ausgeschriebenen
Namen), kein Blog in der Kopfzeile. Auf dem Handy: Logo, «Menü» (Wort, kein Symbol allein).

Die Hilfeadressen, auf die die App verweist (`help-map.ts`), bleiben alle erreichbar. Artikel zu
Funktionen ausserhalb des Kerns (Training, Taktiktafel, Assistent, Präsentation, Spieler-Feed,
Vorbereitungsbericht) erscheinen nicht mehr in der Liste; ihre Seite sagt oben, dass die Funktion
gerade nicht im Vordergrund steht.

## 3. Gestaltung

Dieselbe Welt wie die App (Anlauf), grosszügiger gesetzt:

- **Grund Stoff** (`#eceae5` mit Punktraster), Tinte `#16171a`, Zweittext `#53565b` (6.1:1).
- **Kanit** kursiv 800/900 für Titel, Zahlen, Namen, Navigation; **Hanken Grotesk** aufrecht für
  Text und Knöpfe; **IBM Plex Mono** auf der Taktikkamera. Alle selbst gehostet (OFL, Dateien wie
  in `apps/web/src/fonts`).
- **Keine Rundungen, keine Schatten, keine Karten, keine Verläufe, keine Icon-Kacheln.** Struktur
  durch Abschnittsköpfe (schräger Titel, 2 px Linie) und Haarlinien. Knöpfe Tinte gefüllt oder
  Tinte umrandet, 56 px hoch.
- **Die Vereinsfarbe gehört dem Besucher.** Der Kopf der Startseite ist ein Spiel im Wurf-Kopf:
  mit einem Tipp auf ein Trikot («Welche Farbe trägt dein Team?», acht Farben mit Namen) färben
  sich Kopf, Zahlen und Bündel. Der Farbmodell-Code ist derselbe wie in der App (`kit()`), mit
  Kontrastregeln für Gelb und Weiss. Die Wahl geht über den Link «Demo-Spiel ansehen» mit
  (`?farbe=rot`), ohne Speicher im Browser.
- **Das Logo** zweifarbig quer in der Kopfzeile, nie auf der Vereinsfarbe (Logo-Regel). Im Fuss
  die einfarbige Fassung.
- **Bilder**: live gezeichnete Bausteine (Wurf-Kopf mit Verlauf, Bündel, Taktikkamera animiert,
  Zonen, Hallenplan mit Kamera) und echte Bilder der App aus `docs/screens/anlauf`, beschriftet
  «Bilder aus der App, mit Beispieldaten». Keine Fotos, keine Gesichter.
- **Bewegung**: Bündel zeichnen sich einmal, die Taktikkamera spielt mit «Pause». Mit
  `prefers-reduced-motion` alles still, die Kamera zeigt das letzte Bild und den Knopf «Abspielen».

Lesbarkeit: Fliesstext 19 px (Handy 18 px), Zweittext 17 px, nichts unter 16 px; Ziele 48 px oder
mehr; Zeilen höchstens 68 Zeichen; Layout hält 200 % Zoom und grosse Systemschrift (Grössen in
`rem`, keine festen Höhen um Text).

## 4. Aufbau und Texte (de-CH)

Regeln: du-Form, «ss», kurze Sätze, keine Anglizismen, wo es ein deutsches Wort gibt, keine
Gedankenstriche, Verben auf Knöpfen, keine Pfeile. Vokabular wie SPEC 9 (Spiele, Drei Dinge,
Szenen, Sammlung, Spielbericht, Prüfen, Spieltag, Teilen). fr und en stehen in
`apps/site/src/messages/{fr,en}.ts` mit denselben Schlüsseln.

### Start

1. **Kopf (Wurf-Kopf in der Farbe des Besuchers)**
   - Kicker: «Erfundenes Beispielspiel, so wie es die App zeigt»
   - Titel: «Dein Spiel. Und drei Dinge zum Mitnehmen.»
   - Text: «Du filmst das Spiel mit dem Handy und lädst das Video hoch. Die Analyse zeigt dir drei
     Dinge zum Mitnehmen, mit den Szenen dazu.»
   - Resultat 25:24, Namen «HC Beispiel» und «TV Muster», Verlauf des Spiels als Linie.
   - Farbwahl: «Welche Farbe trägt dein Team?» Blau, Rot, Gelb, Schwarz, Weiss, Grün, Orange,
     Violett.
2. **Team-Feld im Kopf** (Nachtrag 13. November, aus `docs/ux-test/runde1/EINSTIEG.md`): «Wie
   heisst dein Team?», ein Feld, Knopf «Zeigen», darunter «zum Beispiel: HC Zürichsee Herren 1».
   Schickt per GET auf `<App-URL>/einstieg?q=…`, wo die App das Team aus den Verbandsdaten ohne
   Konto zeigt. Am Handy im ersten Bildschirm, über der Farbwahl. Daneben «Demo-Spiel ansehen»
   (Umriss), darunter «Dein Team ansehen geht ohne Konto.» «Kostenlos starten» in der Kopfzeile
   führt auf `/einstieg` ohne Team.
3. **Drei Dinge** (Abschnittskopf «Das bekommst du nach jedem Spiel»): drei Spalten mit Index,
   Zahl, Einheit, Satz, Unterzeile, Bündel; Legende «Durchgezogen: Anlauf bis zur Wurfposition, von
   dir bestätigt. Gestrichelt: geschätzt.»
4. **Dazu** (Taktikkamera links, Liste rechts): «Alle Szenen. Jedes Tor als kurze Szene, nach
   Spiel und Thema sortiert.» «Die Taktikkamera. Die Szene von oben, als Punkte auf dem Feld.»
   «Die Zahlen. Aus dem Spielbericht und dem, was du markierst. Bei jeder Zahl steht, woher sie
   kommt.» «Ein Link fürs Team. In den Gruppenchat, ohne Konto für die Spieler.»
5. **So kommst du dahin** (drei Schritte mit grossen Ziffern): «Filmen. Handy aufs Stativ, hoch
   an der Mittellinie, das ganze Feld im Bild.» «Hochladen. Video in der App wählen. Wenn die
   Analyse fertig ist, bekommst du eine Nachricht.» «Prüfen und teilen. Wo die Analyse unsicher
   ist, fragt sie dich kurz. Dann schickst du dem Team den Link.» Link «So filmst du richtig».
6. **Das kann es, das noch nicht** (kurz, Link auf die ganze Liste).
7. **Für den Vorstand**: Preis «Ab CHF 39 im Monat für ein Team», Daten «Server in der Schweiz,
   Videos in der EU», Einwilligung «Per Link, ohne Konto. Für Kinder entscheiden die Eltern.»
8. **Schluss**: «Probier es mit deinem nächsten Spiel.» Zwei Knöpfe.

### So funktioniert es

Seitenkopf «In drei Schritten vom Spiel zu den drei Dingen.» Dann:

- **1 Filmen**: Hallenplan, vier Regeln, Link auf «Filmen».
- **2 Hochladen**: «Welche Datei? MP4 oder MOV, so wie das Handy sie speichert. Bricht die
  Verbindung ab, geht der Upload beim nächsten Mal dort weiter. Grosse Dateien lieber im WLAN.»
- **3 Die Analyse rechnet**: was sie tut (Spielfeld finden, Spielerinnen und Spieler verfolgen,
  Rückennummern lesen, Tore aus dem Spielbericht übernehmen), «Du bekommst eine Nachricht, wenn
  sie fertig ist.»
- **4 Prüfen**: «Wo die Analyse unsicher ist, fragt sie dich: Wer ist das? Passt das Spielfeld?
  Jede Antwort ist sofort gespeichert. Du kannst jederzeit aufhören.»
- **5 Anschauen und teilen**: drei echte App-Bilder (Start, Taktikkamera, geteilter Link).
- **Das kann es, das noch nicht** (ganze Liste, siehe 5).

### Filmen

Seitenkopf «So filmst du ein Spiel.» Hallenplan von oben mit Kamera an der Mittellinie und
Blickfeld. Abschnitte «Was du brauchst» (Handy, Stativ oder ein fester Platz auf der Tribüne,
Powerbank, mindestens 10 GB frei), «Aufstellen» (hoch, ab etwa 3 Metern; Mittellinie; ganzes
Feld; quer), «Einstellen» (1080p, wenn möglich 50 Bilder pro Sekunde; Flugmodus; Bildschirm an),
«Während dem Spiel» (nicht schwenken, nicht zoomen; einfach laufen lassen, auch in der Pause),
«Danach» (Datei hochladen, MP4 oder MOV), «Was weniger gut geht» (schwenkende Kamera: geht, aber
das Feld wird schwerer erkannt; Gegenlicht; nur hinter dem Tor). Aushang zum Drucken.

### Demo-Spiel

- Gelber Hinweis mit Wort, oben und nicht wegklickbar: «Erfundenes Spiel. Mannschaften, Tore und
  Laufwege sind erfunden, damit du siehst, wie eine Auswertung aussieht. Die Zahlen sind mit
  demselben Code gerechnet wie in der App.»
- Wurf-Kopf mit Farbwahl, Quellenzeile «Tore aus dem Spielbericht · Laufwege aus dem Video,
  geschätzt · Würfe und Paraden von Hand markiert».
- Drei Dinge zum Antippen; das gewählte zeigt seine Szenen als Liste.
- «Szene aus Punkt 1»: Taktikkamera mit Pause, Ball-Linie «Ball in dieser Szene nicht erkannt»,
  Legende.
- «Spielverlauf» (Tore auf der Zeitleiste), «Zahlen» (Tabelle mit Spalte Quelle), «Gegentore nach
  Position» (Zonen, geschätzt).
- «In der App öffnet jede Szene das Video an dieser Stelle. Im erfundenen Spiel gibt es kein
  Video.» Knöpfe «Kostenlos starten», «So funktioniert es».

### Preise

Seitenkopf «Ein Preis pro Team.», Zahl «39», Einheit «CHF im Monat». Sichtbarer Hinweis: «Die
Preise sind noch nicht endgültig.» Drei Zeilen (keine Karten): Gratis (ohne automatische
Analyse), Team, Verein, mit dem, was in der Analyse drin ist, in den Worten der App. Testphase,
Jahresrechnung per QR-Rechnung, Fair Use, Fragen.

### Fragen

Seitenkopf «Fragen und Antworten.» Zuerst neun häufige Fragen zum Aufklappen (Handy, Kamera,
Datei, Dauer, von Hand, Kosten, Video, Einwilligung, Konto für Spieler), dann die Anleitungen mit
Suche, zuletzt «Noch Fragen? Schreib uns.»

### Daten und Einwilligung

Seitenkopf «Was mit dem Video passiert.» Abschnitte: Wer filmt und wer es sieht; die Einwilligung
(per Link im Teamchat, ohne Konto, einzeln wählbar, jederzeit widerrufbar); Kinder und
Jugendliche (unter 16 entscheiden die Eltern); wer nicht einwilligt; wo die Daten liegen; wie
lange; löschen; was wir nicht tun (nicht verkaufen, keine Werbung, nicht für die Erkennung ohne
Einwilligung). Kontakt.

### Über uns und Kontakt

Seitenkopf «Wir schreiben zurück.» E-Mail mit Antwortzeit; «Woran wir uns halten» (drei Sätze aus
den Prinzipien). «Wer wir sind» als Platzhalter «folgt vor dem Start» (offene Frage).

## 5. Das kann es, das noch nicht (Quelle: ADR 020, 026, 027, OPEN_QUESTIONS Q-UX-15 bis 17)

**Das kann es**
- Spielerinnen und Spieler im Video finden und ihre Laufwege schätzen, sobald das Spielfeld
  erkannt ist oder du es bestätigt hast.
- Tore aus dem Spielbericht übernehmen, oder aus einer Spielstand-Anzeige, die im Video gut lesbar
  ist.
- Rückennummern lesen, wo sie gut zu sehen sind. Die übrigen ordnest du beim Prüfen zu.
- Zu jedem Tor eine Szene schneiden und daraus die drei Dinge machen.

**Das noch nicht**
- Den Ball verfolgen. Darum zeigt es keine Pässe und keine Wurfbahnen.
- Paraden und Fehlwürfe erkennen. Die markierst du von Hand, wenn du sie willst.
- Tore allein aus dem Bild erkennen, wenn es weder Spielbericht noch Anzeige gibt.
- Laufdistanzen genau messen. Aus einer Kamera sind es Schätzungen.
- Ein Spiel aus zwei Dateien auswerten (Nachtrag 13. November: die zweite Datei wird gespeichert
  und abgespielt, ausgewertet wird nur die erste; so steht es in der App).

Geschätztes ist gestrichelt und heisst «geschätzt».

## 6. Offene Fragen (eingetragen in `docs/OPEN_QUESTIONS.md`, Q-SITE-*)

1. **Preise**: aus `packages/plans` (CHF 0 / 39 / 199), laut Q-PROD-4 Platzhalter. Die Seite zeigt
   sie mit «noch nicht endgültig». Torhüter-Modul (CHF 7) nicht gezeigt: ausserhalb des Kerns.
2. **Dauer der Analyse**: keine Zeit versprochen (CPU etwa zweimal Spiellänge, GPU offen).
3. **Wer wir sind**: kein Text vorhanden, Platzhalter.
4. **Domain und Firmenname**: Domain entschieden am 13. November: `handball-intelligence.com` (siehe `SEO.md`, «Vor dem Livegang»); Firmenname Handball AI GmbH per Build-Variable, offen.
5. **Rechtliches**: Entwürfe, nicht geprüft (Q-LEGAL-1, Q-ADD-5).
6. **Speicherort**: App und Datenbank Schweiz, Videos EU (ADR 025, ADR 002); Anbieter werden
   vor dem Start in der Datenschutzerklärung genannt.
7. **Öffentliches Demo-Spiel in der App**: die App hat keines. Ohne Konto gibt es nur das
   erfundene Spiel der Website.
8. **Testphase ohne Kreditkarte** und **Nachricht, wenn die Analyse fertig ist**: im Projekt nicht
   belegt; die Seite sagt beides nicht mehr (Q-SITE-7, Q-SITE-8).
