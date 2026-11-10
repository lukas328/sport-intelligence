# Einblendung

Runde 2, Richtung A. Feld: das Bild und die Bewegung. `index.html` im Browser öffnen (ohne Build,
Google Fonts aus dem Netz); `?club=blau|gelb|schwarz` oder die Knöpfe oben wechseln die Vereinsfarbe.
Bilder in `shots/`, alle sechs Ansichten auf einem Bild in `shots/bogen.jpg`.

## Leitidee

**Das Spiel ist die Oberfläche: Die Auswertung liegt als Übertragungsgrafik auf dem Bild des
Spiels, und alles andere ordnet sich darum.**

Die bisherigen Richtungen zeigen das Video als einen Kasten unter vielen. Hier ist das Bild der
Grund jedes Screens, und die Analyse spricht so, wie eine Fernsehübertragung spricht: Einblendung,
Bauchbinde, Spielstand in der Ecke, Wege auf dem Boden.

## Regeln

1. **Jeder Screen über ein Spiel beginnt mit einem Bild dieses Spiels.** Start: die Szene hinter
   Punkt 1, randlos über die ganze Breite. Spiel: der Endstand liegt auf dem Feld. Video: das Video.
   Text kommt als Einblendung darauf oder als Bauchbinde darunter, nie als Karte daneben.
2. **Ohne Einwilligung kein Standbild, sondern die Taktikkamera.** Das Feld von oben, gezeichnet aus
   den Positionsdaten: eigene Spielerinnen als volle Marken in Vereinsfarbe mit Nummer, Gegnerinnen
   als hohle Ringe, die letzten Sekunden als Spur, Pässe gestrichelt, der Wurf als weisser Pfeil.
   Auf dem Start ist das Feld leicht gekippt, wie die virtuelle Grafik einer Übertragung.
3. **Grafik wie im Fernsehen, nicht wie in einer App.** Harte Kanten, keine Rundung, kein Schatten,
   keine Pille. Bauchbinden mit Farbkeil links und schräger Kante rechts. Etiketten am Bild sind
   kleine dunkle Tafeln mit einem Strich in der Farbe ihrer Bedeutung.
4. **Wucht oben, Ruhe beim Arbeiten.** Start und Spiel zeigen das Bild gross. Video und Zahlen
   behalten nur den Spielstand-Bug und den Tab; Tabellen stehen auf hellen Tafeln, gross gesetzt,
   44 px pro Zeile.
5. **Bewegung erklärt.** Die Szene auf dem Start spielt beim Öffnen einmal ab (2,6 Sekunden: wer
   wohin läuft, wo die Lücke aufgeht) und bleibt dann stehen. Mit `prefers-reduced-motion` steht
   sie sofort.

## Erkennungszeichen

- **Die Taktikkamera mit Spuren.** Marken mit Kometenschweif aus echten Laufwegen; jedes der drei
  Dinge hat sein eigenes Bild, kein Symbol.
- **Der Bug.** Der Spielstand in der Ecke wie im Fernsehen (Kürzel in Vereinsfarbe, Ziffern breit,
  Gegner auf heller Tafel). Er steht auf jedem Spiel-Screen und ist das Bild eines Spiels.
- **Kamera und Taktik.** Im Video schaltet ein Knopf zwischen Videobild und Taktikkamera; die Wege
  sind in beiden auf dem Boden eingezeichnet.

## Stärken

- Sofort Sport, sofort Übertragung: Das kennt jede Trainerin vom Samstagabend.
- Das Produkt (Positionen, Laufwege) wird zum Bild statt zu Text. Punkt 1 zeigt die Lücke, die zum
  Gegentor führt.
- Die Ersatzdarstellung ist kein Notbehelf: Die Taktikkamera sieht ordentlicher aus als ein
  verwackeltes Hallenvideo und funktioniert ohne Einwilligung.
- Vereinsfarbe nur auf Marken, Keilen und Bug; trägt Rot, Blau, Gelb und Schwarz.

## Risiken

- Dunkel ist anstrengend in heller Halle am Handy. Ein helles Thema bräuchte eigene Entscheidungen
  (das Feld bleibt dunkel, die Tafeln hell).
- Steht und fällt mit der Qualität der Positionsdaten. Wenn Wege springen, sieht man es sofort.
- Übertragungsgrafik kann ins Kostüm kippen, wenn man sie überall streut. Regel 3 heisst auch:
  nur wo ein Spiel gezeigt wird.
- Schwarze Vereine: Eigene Marken werden auf dem dunklen Feld hell gefüllt (Ersatzton), der
  Unterschied zum Gegner liegt dann in voll gegen hohl, nicht in der Farbe.

## Schriften und Farben

- **Archivo** (SIL OFL, variable Breite 62 bis 125): schmal und fett für Titel und Bauchbinden,
  breit und schwer für Ziffern im Bug und im Endstand. Text normal.
- **IBM Plex Mono** (SIL OFL) nur für Zeiten, Quellenzeilen und Etiketten am Bild.
- Nacht `#0a0d11`, Feld `#0f2333`, Linien `rgb(226 236 244 / .55)`, Tafel `#f2f1ec`, Tinte
  `#0b0f14`. Vereinsfarbe als `--club`; auf dem dunklen Feld `--club-on-dark` (aufgehellt bis 3:1).
  Achtung (markierte Phase, Prüfen, Ballverlust) `#ffd23c`. Sieg und Niederlage immer als Wort.
- Schriftskala 12, 14, 16, 20, 28, 40, 48. Abstände in 4er-Schritten (4, 8, 12, 16, 24, 32).
