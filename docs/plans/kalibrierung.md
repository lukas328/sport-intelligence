# Kalibrierung: Testsatz, Messung, Verbesserungen (ab 2026-11-16)

Auftrag: die automatische Spielfeld-Kalibrierung (`handball_vision.observe.auto_calibrate`, ADR 025)
verlässlich machen. Ohne sie gibt es keine Positionen in Metern, keine Taktiktafel, keine Wurfzonen.
Ein falsch akzeptiertes Feld ist schlimmer als keines. Werkzeuge: `ml/calib/` (Forschung; das
Produkt importiert nichts daraus).

## 1. Testsatz (eingefroren 2026-11-16)

- `ml/calib/testset.json`, erzeugt von `ml/calib/testset.py pick` (fester Seed): **70 Stücke à 90 s
  aus 67 Hallen**. Die 42 Spiele des Ball-Testsatzes 2 (`ml/ball/test_games.json`, 42 Hallen,
  Europa und USA, Amateur bis Länderspiel), 4 Spiele SG Wädenswil/Horgen (Club-Streams), 24 weitere
  Heimteams aus `ml/data/catalog.json`.
- Pro Spiel ein Segment aus s0, s1, s3, s4 (s2 liegt bei 50 % und ist oft die Pause), das Stück von
  20 s bis 110 s, wie die 39-Spiele-Messung im Nachtrag von ADR 025.
- **Aufteilung nach Halle:** 33 Stücke Entwicklung (`dev`), 37 Endtest (`test`). Auf dem Endtest
  wird nichts abgestimmt; er wird pro Pull Request höchstens einmal gemessen.
- Produktpfad 1:1 (`ml/calib/run.py`): Worker-Proxy (1280 px, 25 fps, crf 26), `observe()` mit
  YOLOX-S auf jedem 3. Bild, Linien auf jedem 90., dann `auto_calibrate`. Einschränkung: das
  Produkt sieht das ganze Spiel, der Test 90 s; das Panorama ist darum kleiner als im Betrieb.

## 2. Wahrheit

- Pro Stück ein Bild (feste Kamera) oder zwei (linkes und rechtes Schwenkende). Das Ende eines
  Schwenks zeigt ein Tor und prüft zugleich die Kamerabewegung.
- Gespeichert werden **Bildpunkt und Feldposition** der sichtbaren Feldpunkte (Ecken, Mittellinie,
  6-m- und 9-m-Enden, Pfostenfüsse, 7-m-Punkt; Namen wie `handball_court`). Keine Homographie als
  Wahrheit: so bleibt die Messung auch bei Linsenverzeichnung (Weitwinkel-Amateurkameras) ehrlich.
- Ablauf: Klickseite `ml/calib/labelling/feld.html` (Artifact mit Speicher). Wo das Produkt ein Feld
  gefunden hat, ist es als Vorschlag eingezeichnet; Lukas bestätigt, zieht Punkte zurecht oder setzt
  4 bis 6 grob neu, mit Feldlinien als Live-Overlay. Unklares wird übersprungen. Danach
  `ml/calib/truth.py pull`: jedes Bild wird an seinen Linienpixeln verfeinert (Homographie plus
  radiale Verzeichnung k1, k2); die verfeinerten Punkte gelten nur, wenn sie im Median höchstens
  6 px von den Klicks abweichen.
- Bekannte Verzerrung: Vorschläge des Produkts können die Wahrheit zu ihm hin ziehen. Die
  Verfeinerung an den Linien und die Prüfung durch Lukas begrenzen das; korrigierte und bestätigte
  Bilder werden getrennt gezählt.
- Zwei Runden: zuerst die Entwicklungs-Stücke, später der Endtest.

## 3. Metrik (`ml/calib/evaluate.py`)

- Fehler pro Wahrheitspunkt: Bildpunkt → Kamerabewegung → Kalibrierung → Feld, Abstand zur wahren
  Feldposition in Metern (gekappt bei 50 m). Pro Stück der Median.
- Klassen pro Stück: **richtig** (Feld akzeptiert, Median ≤ 1 m), **falsch akzeptiert** (Median
  > 1 m), **abgelehnt** (`needs_calibration`, mit `calibration_info.reason`).
- Anteile mit 95-%-Intervallen per Bootstrap über Hallen (2000 Ziehungen). Dazu: Anteil falsch unter
  den akzeptierten, Median-Fehler der akzeptierten.
- Eigene Messgrösse Verzeichnung: k1 der verfeinerten Wahrheit pro Stück; Anteil der Stücke mit
  starker Verzeichnung und Fehler mit und ohne Korrektur.

## 4. Messungen

### 4.1 Basis: Produkt heute (`main` e089b570, 2026-11-17)

Was `auto_calibrate` auf den 70 Stücken meldet (noch ohne Wahrheit, also ohne richtig/falsch):

| | Entwicklung (33) | Endtest (37) | alle (70) |
|---|---|---|---|
| Feld akzeptiert | 6 | 9 | 15 (21 %) |
| `no_floor` | 10 | 12 | 22 |
| `flat_view` | 8 | 8 | 16 |
| `court` | 8 | 4 | 12 |
| `camera_motion` | 1 | 3 | 4 |
| `few_people` | 0 | 1 | 1 |

62 Stücke haben eine bewegte Kamera (14 akzeptiert), 8 eine feste (1 akzeptiert). Auf
Sicht: bei akzeptierten Feldern liegt das Feld in der Schwenkmitte ungefähr richtig, an den
Schwenkenden daneben (Kamerabewegung). Fehler in Metern und der Anteil falsch akzeptiert folgen mit
der Wahrheit (Runde 1: Entwicklung, 63 Bilder).

## 5. Was nicht geholfen hat

(folgt)
