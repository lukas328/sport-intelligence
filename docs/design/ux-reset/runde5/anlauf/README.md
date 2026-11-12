> **Skizze, aus der das Zielbild wurde.** Entschieden ist «Anlauf» mit Schrift A und Grund «Stoff» (12. November 2026); verbindlich sind `../../ANLAUF.md` und `../../zielbild.html`.

# Anlauf

Runde 5, ausgearbeitete Synthese aus Lukas' Wahl im Mischpult (`K3-D1-S3-G2-Z3-M1-blau-schwarz`).
`index.html` im Browser öffnen (ohne Build, Google Fonts aus dem Netz). Oben umschaltbar: Schrift
A oder B, drei Gründe, sechs Vereinsfarben. Voreinstellung beim Öffnen: Schrift B, Grund Hallenlicht. `?still` zeigt alles ohne Bewegung (für Bilder),
`?f=fb&g=g2&club=rot` öffnet eine bestimmte Variante. Bilder in `shots/`: Einzelbilder, `bogen.jpg`,
`farben.jpg` (sechs Vereinsfarben, Start und Taktikkamera), `varianten.jpg` (A mit Kante, B mit
Hallenlicht, B mit Stoff).

## Idee in einem Satz

**Das Resultat steht schräg in der Vereinsfarbe, die Szene läuft auf der Taktikkamera, und jede
Linie ist ein gemessener Weg.**

Der Name: der Anlauf ist der Weg der Torschützin vor dem Wurf, der eine Teil eines Wurfs, den das
Tracking wirklich misst. Er ist das Motiv der ganzen App.

## Regeln

1. **Jeder Kopf hat seinen Ort.** Wurf ist das Resultat: gross auf Start und im Tab «Spiel», als
   schmaler schräger Streifen auf allen Unterseiten eines Spiels (Video, Zahlen, Prüfen). Die
   Taktikkamera ist die Bühne einer Szene: im Tab «Video» und wenn ein Ding geöffnet wird. Am Start
   läuft Punkt 1 klein als Vorschau.
2. **Eine Linie ist ein gemessener Weg.** Der Verlauf im Kopf (Tordifferenz aus dem Spielbericht),
   die Anläufe in den Bündeln, die Wege auf der Taktikkamera. Was nicht gemessen ist, wird nicht
   gezeichnet: kein Ball, keine Passlinie, keine Flugbahn. Bestätigt ist durchgezogen, geschätzt
   gestrichelt oder heller.
3. **Zwei Teams, zwei Farben, sonst Tinte.** Die Vereinsfarbe trägt den Kopf, die eigenen Linien
   und Ziffern; der Gegner erscheint als Strich unter seiner Zahl, als Farbfeld bei seinem Namen
   und als Linie. Gelb nur für «schau hier» (Prüfen, markierte Phase). Kein Grund ist aus der
   Vereinsfarbe getönt.
4. **Schräg ist das Tempo, nicht die Dekoration.** Der Kopf ist schräg geschnitten, das Resultat
   schräg gesetzt mit zwei versetzten Konturen (die 3D-Andeutung). Variante A setzt auch Titel und
   Köpfe schräg, Variante B nur Ziffern und Resultat. Gegen den Wett-Look: keine Leuchtfarben, kein
   Schwarz-Gelb als App-Farbe, keine Quoten-Kacheln, ruhiger Text.
5. **Bewegung zeigt, was passiert ist.** Die Taktikkamera spielt die Szene ab (sechs Sekunden,
   dann steht sie kurz und beginnt neu), mit Pause-Knopf. Die Bündel zeichnen ihre Anläufe beim
   Öffnen nacheinander. Mit `prefers-reduced-motion` steht alles sofort im letzten Bild.

## Datenquelle jeder Grafik

| Grafik | Zeigt | Quelle |
|---|---|---|
| Resultat, Halbzeit, Time-outs | Zahlen | Spielbericht (handball.ch) oder lesbare Anzeige |
| Verlauf im Wurf-Kopf | Tordifferenz Minute für Minute | Torfolge aus dem Spielbericht |
| Bündel (drei Dinge) | Anlauf der Torschützin in den Sekunden vor dem Tor, bis zur Wurfposition, dann ein dünner gerader Strich zum Tor | Spielerpositionen aus dem Video (8 bis 10 pro Sekunde); Wurfposition geschätzt als nächster Punkt zum Tor in den 10 Sekunden vor dem Tor; nur Tore |
| Taktikkamera | Spielerinnen als Punkte, Torhüter, Schiri, Wege der letzten zwei Sekunden, der ganze Weg der Torschützin | Spielerpositionen in Metern, nur bei erkanntem oder bestätigtem Feld; Nummer nur, wo sie gelesen wurde (rund ein Viertel der Zeit) |
| Minifeld in der Liste | Bündel von Punkt 1 dieses Spiels; ohne Video leeres Feld | wie Bündel |
| Gegentore / eigene Tore nach Position | Anzahl je Zone, Wurfpositionen als Punkte | geschätzte Wurfpositionen der Tore; leer: noch nicht bestätigt |
| Ziel im Tor (3x3) | Ecken | nur von Hand markiert oder vom Papierbogen; als Zustand «von dir markiert, 12 von 18» |
| Tabelle Feld | Tore, 7 m, 2 Minuten | Spielbericht; Würfe und Quote nur von der Trainerin markiert |
| Tabelle Tor | Gegentore, Paraden | Gegentore aus dem Spielbericht, Paraden von Hand markiert |
| Phasen | Über- und Unterzahl, Gegenstösse | Über- und Unterzahl aus den 2-Minuten-Strafen; Gegenstösse aus dem Video geschätzt |
| Zeitleiste im Video | Tore beider Teams, markierte Phase | Torfolge aus dem Spielbericht, Phase aus Punkt 2 |
| Ballverluste | Zeitpunkte | nur aus dem Spielbericht, ohne Position |

Eine Abweichung vom bisherigen Inhalt: Punkt 3 heisst jetzt «7 von 26: Tore vom Kreis» statt
«Kreisanspiel: 7 von 8 verwertet». Ein Anspiel ist ein Pass, und Pässe kennt die Analyse nicht;
Fehlwürfe vom Kreis gäbe es nur von Hand.

## Zustände

- **Kein Video** (SG Horgen): Wurf-Kopf mit Resultat und Verlauf aus der Torfolge, Tab «Video»
  ausgegraut, ein leeres Feld «kein Video» mit «Video wählen» und «Link einfügen», das Telegramm.
- **Feld nicht bestätigt:** Das Video zeigt das erkannte Feld gelb gestrichelt mit vier Ecken.
  «Stimmt das Feld?» mit «Ja, stimmt» und «Ecken verschieben». Bis dahin keine Wege, keine Punkte.
- **Gegnerfarbe unbekannt:** Thalwil steht grau mit «Farbe offen», im Kopf fragt eine Reihe von
  Trikotfarben «Welche Farbe trägt Thalwil?». Auf der Taktikkamera sind die Gegnerinnen graue
  Ringe. Nie geraten.
- **Gleiche Farbe:** Sind die beiden Teams auf dem dunklen Feld zu ähnlich (schwarz gegen schwarz,
  weiss gegen schwarz im Zweittrikot), werden die Gegnerinnen zu grauen Ringen.

## Schrift, Grund, Farben

- **Kanit** (SIL OFL), kursiv 800 bis 900 für Resultat und Ziffern, in Variante A auch für Titel
  und Köpfe; in B stehen Titel aufrecht (Kanit 700). **Hanken Grotesk** (SIL OFL) für Text und
  Tabellen. **IBM Plex Mono** nur für Zeiten und Hinweise auf der Taktikkamera.
- Gründe, alle neutral: **Kante** `#f4f3ef`, jeder Abschnitt öffnet mit der Schräge des Kopfs als
  Linie; **Hallenlicht** `#e7eaed` mit weissen Flächen ohne Schatten; **Stoff** `#eceae5` mit einem
  feinen Maschenmuster wie Trikotstoff.
- Tinte `#15171a`, Text 2 etwa `#53575d`. Gelb `#ffd23c` für Prüfen und Phase. Sieg `#17703f`,
  Niederlage `#a8261e`, immer als Wort.
- Taktikkamera: Feld `#0f2333`. Eigene Punkte in der Vereinsfarbe (verschwindet sie auf dem
  dunklen Feld, in der Zweitfarbe), Gegnerinnen in ihrer Farbe mit Rand, Schiri grau als Raute.
- Schriftskala 13, 15, 17, 20, 26, 34, 44, 58, Ziffern 64 bis 196. Abstände 4, 8, 12, 16, 24, 32, 48.

## Offene Punkte

- Die Bewegungsdaten der Taktikkamera und die Anläufe sind hier gezeichnet (Demo), nicht aus
  einem echten Spiel. Ob echte Tracking-Wege so ruhig aussehen, muss man mit einem Spiel prüfen;
  wahrscheinlich braucht es eine leichte Glättung, die dann als solche benannt wird.
- Variante A gegen B: A ist näher an dem, was Lukas mag, B ist ruhiger und weiter weg vom
  Wett-Look. Meine Empfehlung ist B.
- Grund: Hallenlicht mit weissen Flächen ist am klarsten, Kante am eigenständigsten, Stoff am
  wärmsten. Keiner ist schon ein Wow.
- Am Start Desktop schaltet Punkt 1 im selben Rahmen zwischen «Alle 9» (Bündel) und «Szene 39:55»
  (Taktikkamera); am Handy hat die Szene einen eigenen Abschnitt. Nie beides übereinander.
- Beim Feld-Check zeigt das Bild etwas weiter, damit alle vier Ecken drin sind. Schwenkt die
  Kamera im echten Video so, dass eine Ecke fehlt, braucht es einen Hinweis.
- Kontrast: weisse Schrift auf Gelb und auf Weiss wird im Kopf auf Tinte umgestellt; die
  Vereinsfarbe als Text wird bei zu wenig Kontrast zu Tinte.
