# Produkt-Audit: was nach dem Hochladen eines Videos passiert (Stand 2026-11-25)

Auftrag von Lukas: eine gründliche, ehrliche Analyse aller Funktionen nach dem Upload, mit dem Ziel,
das Produkt und vor allem die Modelle besser zu machen. Dieser Bericht ist eine Bestandsaufnahme mit
Bewertung und Vorschlägen; er ändert nichts am Produkt. Zwei kleine Fehler, die unterwegs auffielen,
sind als eigene PRs behoben (Abschnitt 6).

**Kennzeichnung.** *Gemessen* heisst: eine Zahl gegen eine Wahrheit (Gold-Labels, Spielbericht,
geklickte Punkte) mit Quelle. *Beobachtet* heisst: aus einem echten Lauf abgelesen, ohne Wahrheit.
*Geschätzt* heisst: Urteil aus Code und Daten, nicht gemessen. Der Wurf-Endtest
(`ml/gold/data/shot_endtest_marks.json`) wurde nicht angefasst; seine Ergebnisse sind nur aus den
bestehenden Berichten zitiert.

## 1. Grundlage

- **Code:** `apps/api`, `apps/worker`, `apps/gpu-worker`, `apps/web`, `packages/vision`,
  `packages/metrics`, `packages/jobkit` auf `main` (7c06232).
- **Messwerte:** `docs/plans/*` (vor allem `produkt-analyse-integration.md`, `kalibrierung.md`,
  `gpu-analyse.md`, `tracking-strategie.md`), `docs/adr/025` bis `030`, `docs/perf/*`,
  `ml/*/README.md`, `ml/ball/LINEAGE.md`, `ml/gold/data/shot_endtest_result.json`.
- **Echte Läufe auf Staging:** Diagnose-Artefakt des Deploy-Laufs 45210732565 (23.11., `mode=status`,
  `diag=true`) mit Job-Stufen, Ergebnis und Artefakten der neuesten Analyse, dazu die gespeicherten
  Artefakte von zwei 8-Minuten-Uploads vom 19.11. im Artefakt-Bucket, nur gelesen:
  - **Lauf U** (Asset 76201462, Uznach, 1920x1080, 30 fps, Overlay mit Spielstand): automatische
    Kalibrierung gescheitert, 0 Tor- und Wurfkandidaten.
  - **Lauf H** (Asset 90c0bf9a, 8 Minuten aus einem Vereins-Stream mit Schwenk und Zoom bis 3,7x,
    Hallentafel): kalibriert, getrackt, Ballpfad. Danach zwei Neuläufe von je 19 s auf den
    gespeicherten Beobachtungen.
- **Lokal nachgerechnet:** Auf den gespeicherten Beobachtungen beider Läufe wurden Kalibrierung,
  Pausenmaske und Torkandidaten mit dem Produktcode neu berechnet (Skripte nicht im Repo, nur in der
  Sitzung). Ein kompletter lokaler Lauf (Compose-Stack) war nicht sinnvoll: die Testvideos liegen
  hinter R2-Schlüsseln, die in der Sitzung fehlen. Stattdessen lief `run_analysis` mit einer
  Dateisystem-Attrappe für Bucket und API auf dem Testclip `sghorgen-h1-5min` (Abschnitt 3.3).

## 2. Die Kette in einem Bild

```
Upload (Browser, multipart) ─► Ingest (Queue pipeline, CPU)
   Download+SHA ─► ffprobe ─► Qualitätscheck ─► HLS 1080p/720p ─► Proxy 1280 px 25 fps
   ─► Poster/Thumbnails ─► Audio 8 kHz ─► Upload
                               │
                               ▼ API: start_analysis (Kits, Kader, Hallenreferenzen, Seitenhinweis)
Analyse (Queue gpu, heute CPU auf Staging) ── handball_gpu_worker.analysis._run_learned
   observe (ein Decode-Durchgang): Kamerabewegung jedes Bild, YOLOX-S jedes 3. Bild,
     Torso-Farbe, Rückennummern (PP-OCRv4), ReID (FastReID), Rollen (aus), Ballnetz (jedes Bild),
     Feldlinien, Overlay- oder Hallentafel-Uhr
   ─► Kalibrierung: Klickpunkte | Hallenreferenz | automatisch ─┬─ gescheitert ─► needs_calibration
   ─► Tracking + Teams + Torhüter + Nummern/ReID-Merge           │   (nur Uhr, Spielstand,
   ─► Ball (Pfad, Ballbesitz-Statistik)                          │    Torkandidaten)
   ─► Tor- und Wurfkandidaten (ohne Feld)                        │
   ─► Torwurf-Orte (nur mit Overlay-/Tafel-Toren)                │
   ─► Ereignisse, Ballbesitz-Phasen, Formationen (nur Positionen)│
                               │◄─────────────────────────────────┘
                               ▼ API: _apply_analysis_result
   Tracks, Kalibrierung, auto_events (Tore, Anwürfe, Phasen), Torkandidaten (+auto_accept mit
   Spielbericht), Signale (wenig gefunden), Wurforte, Spieltag-Marken, Highlights, Feed
                               ▼
   Web: Analyse-Panel, Prüfen, Torkandidaten, Übersicht/Statistik, Torhüter, Würfe, Bericht (PDF),
   Präsentation (MP4), Spieltag
```

Die zentrale Abhängigkeit: **ohne Feld (Kalibrierung) gibt es keine Positionen**, also keine Tracks,
keine Ballbesitz-Phasen, keine Ereignisse, keine Wurforte, keine Laufwege, keine Formationen. Übrig
bleiben Spieluhr, Spielstand und Torkandidaten.

## 3. Echte Läufe

### 3.1 Lauf U (8 Minuten, fester Weitwinkel, Overlay)

| Stufe | Dauer | Bemerkung |
|---|---|---|
| Ingest gesamt | 28,8 min | 3,6x Videolänge |
| davon HLS-Transcode | 18,7 min | 2,3x Videolänge, der grösste Posten |
| davon Proxy | 6,2 min | |
| davon Thumbnails | 1,7 min | |
| Analyse `observe` | 60,3 min | 7,5x Videolänge |
| davon ReID (`appearance_net`) | 33,9 min | 56 % der Analyse |
| davon YOLOX (`detection`) | 13,2 min | |
| davon Nummern | 6,0 min | |
| davon Kamerabewegung | 4,1 min | |
| Ballnetz (eigener Thread, parallel) | 52,8 min belegt | konkurriert mit ReID um 2 vCPU |
| Kalibrierung | 14 s | gescheitert: `no_floor` |

Ergebnis für den Trainer:
- Hinweis «Feld markieren».
- 4 Tore aus dem Overlay (5:4 bis 8:5), ohne Wurfort.
- **0 Torkandidaten, 0 Wurfkandidaten, 0 Phasen**. Die Pausenmaske hatte das ganze Video als Pause
  markiert (`play_s 0`), darum zeigt «Prüfen» auch «wenig gefunden: kein Spiel».

Ursachen, lokal nachgerechnet:
1. **Pausenmaske:** Die Kamera hat 2,0° Drift und Zoom 1,03. `motion.py` nennt das «bewegt» (ab 1°).
   Die Regel «bediente Kamera steht 2,5 min still = geparkt» griff darum auf das ganze Video.
   Behoben in PR #119. Auf denselben Beobachtungen ergibt das 16 Kandidaten bei der Standardrate,
   **alle 4 Overlay-Tore** darunter.
2. **Kalibrierung:** scheitert auch dann, wenn man die Kamera als fest behandelt (mehrere
   Brennweiten probiert). Es bleibt `flat_view`: Kamera etwa 3,4 m hoch, Spieler im Median 5° unter
   dem Horizont, die Grenze liegt bei 10°. Eine tiefe Kamera ist der typische Vereinsfall. Ohne
   Klick bleibt dieses Video ohne Positionen.

### 3.2 Lauf H (8 Minuten, Vereins-Stream, Schwenk 59°, Zoom bis 3,7x)

- Analyse 56,5 min (7,1x), danach zwei Neuläufe von je 19 s auf den gespeicherten Beobachtungen.
- **Kalibrierung:** Die automatische Kalibrierung scheitert auch hier, lokal auf denselben
  Beobachtungen nachgerechnet: `flat_view`, Kamera etwa 3,4 m hoch, Spieler 7° unter dem Horizont.
  Das Feld dieses Laufs kam also aus Klicks.
  - Der Neulauf mit Klickpunkten funktioniert damit technisch auf Staging. Er war bisher als offen
    geführt (`kalibrierung.md` B1).
  - Ob die Klicks das Feld richtig gesetzt haben, lässt sich aus den Artefakten nicht sagen.
- **Zwischenstand:** Damit hatten **2 von 2** echten Uploads auf Staging kein automatisches Feld,
  beide aus tiefen Vereinskameras.
- **Tracking (beobachtet):**
  - 276 Track-IDs in 8 Minuten für etwa 16 Personen.
  - Median-Dauer eines Tracks 17 s, nur 28 Tracks dauern 60 s oder länger.
  - Im Median 6 sichtbare Personen pro Bild: die Kamera zeigt meist eine Hälfte, Verdeckte werden
    ausgeblendet.
- **Spieluhr (Hallentafel):** 55 Ablesungen, 205 s Spielzeit in 6 Stücken.
- **Ballpfad (beobachtet):** 4 810 Punkte, also auf 94 % der Spielzeit-Bilder ein Punkt. Das ist die
  Abdeckung, nicht die Richtigkeit. Gemessen sind 80 % auf Gold v1 (Abschnitt 4).
- Die Kennzahl `ball_path_coverage` im Ergebnis stand bei 1,2, weil sie durch die Detektionsbilder
  statt die Videobilder teilte. Behoben in PR #121.

### 3.3 Lokaler Lauf (Testclip Horgen H1, 5 Minuten, 4 CPU-Kerne)

Auf dem Testclip lief `run_analysis` mit allen Modellen auf CPU: YOLOX, PP-OCR, ReID und Ballnetz
hrp1. Die Laufzeit lag in derselben Grössenordnung wie auf Staging, über 20x Videolänge, solange
parallel andere Rechnungen liefen. Die Zahlen dieses Laufs sind wegen der geteilten Kerne nur als
Bestätigung der Grössenordnung brauchbar, nicht als Messung: 6323 s für 5 Minuten (21x),
automatische Kalibrierung akzeptiert (Kamera 5.9 m), aber keine Würfe. Details in Anhang A.

## 4. Alle Stufen

Legende Begrenzung: wie stark die Stufe heute das Endergebnis für den Trainer begrenzt
(hoch / mittel / tief).

| # | Stufe | Was / Modell oder Regel | Qualität | Laufzeit pro Spiel (60 min) | Fehlerbild | Was der Trainer sieht | Begrenzung |
|---|---|---|---|---|---|---|---|
| 1 | Upload, Ingest, HLS | ffmpeg: HLS 1080p/720p, Proxy 1280 px 25 fps, Poster, Thumbnails, Audio | funktioniert (Playwright-Check), HLS-Qualität nicht gemessen | **beobachtet** 3,6x auf Staging-Worker (8 min → 29 min), also etwa 3,5 h pro Spiel; gemessen 0,12x für den Proxy auf 4 Kernen | Transcode doppelt (HLS und Proxy getrennt), 1 vCPU; über 60 fps passt die GOP nicht (`transcode.py:35`) | Video erst nach Ingest abspielbar | mittel (Wartezeit) |
| 2 | Kamerabewegung, Panorama | ORB/KLT, Rotation und Zoom, Panorama als Hallenbild | 92 bis 100 % der Bilder platziert (beobachtet); «fest» nur unter 1° und 3 % Zoom | 4 min pro 8 min (beobachtet) | Drift einer Stativkamera gilt als «bewegt» (Lauf U); TV mit Schnitten scheitert (`camera_motion`) | Hallenbild zum Klicken | mittel |
| 3 | Automatische Kalibrierung | Liniennormalen, Kamerahöhe aus Personen, Feldvorlage, Torrahmen; `court_doubt` | **gemessen** Endtest 28 Stücke: 0 richtig, 2 falsch angenommen, 26 abgelehnt; Testset 70 Stücke: 21 % angenommen; Staging 0 von 2 (beobachtet) | Sekunden | tiefe Kamera (`flat_view`), viele Linien (`no_floor`), TV | «Feld markieren» | **hoch** |
| 4 | Klick-Kalibrierung | Pose mit bekannter Brennweite, sonst Homographie; Neulauf auf gespeicherten Beobachtungen | **gemessen** synthetisch 0,07 bis 0,11 m; Staging-Neulauf 19 s (beobachtet) | Sekunden, aber erst nach der vollen Analyse | Trainer muss zurückkommen; 37 von 101 Endtest-Bildern «nicht bestimmbar» | Prüfen: Ecken ziehen oder Linien klicken | hoch (wer nicht klickt, bekommt nichts) |
| 5 | Hallen-Wiederverwendung | Bildregistrierung gegen bis zu 3 bestätigte Hallenbilder | **gemessen** 18 Bilder: 5 Treffer, 0 falsche; auf echten Uploads nicht gemessen | Sekunden | ohne `match.venue` (Auswärtsspiel) keine Referenz; keine Plausibilitätsprüfung (`court_doubt` fehlt) | nichts, Feld ist einfach da | mittel (Hebel ab dem 2. Spiel) |
| 6 | Personen-Detektion | YOLOX-S COCO jedes 3. Bild, Bank-Filter | real nicht gemessen; Bank-Filter 89 bis 91 % Recall, 99 bis 100 % Präzision | 13 min pro 8 min CPU (beobachtet) | kleine, verdeckte Spieler; COCO-Modell ohne Handball-Training | indirekt | mittel |
| 7 | Tracking | Kalman, Ungarische Zuordnung, Stitching (4 s), Nummern- und ReID-Merge | **real nicht gemessen** (synthetisch MOTA 0,40); beobachtet 276 IDs für 16 Personen in 8 min | Sekunden bis Minuten | Fragmentierung, Ausblenden ausserhalb des Bildes; Farbtor ausgeschaltet (`colour_weight 0`) | Laufwege, Distanzen pro Spieler nur stückweise | **hoch** |
| 8 | Teams, Trikotfarben | Torso-Lab, k-Means 3 bis 5, Abgleich mit Kits | gemessen synthetisch 0,90; real Clip A Phasen 86/79 gegen 61/92 | Sekunden | ohne Gegner-Kit rät «hell = Heim»; Torhüter in Sonderfarbe wird «Schiedsrichter» | falsche Mannschaft an Track | mittel |
| 9 | Rückennummern | PP-OCRv4, Gate, Abstimmung; Kader als Prior | **gemessen** 12 Spiele: 94 % der gelesenen Nummern stimmen, aber nur 25 % der Spielerzeit nummeriert (35 % mit ReID); 99-min-Video: 34 Nummern, keiner einem Track zugeordnet | 6 min pro 8 min CPU | kleine Nummern, Rücken nicht sichtbar | Spieler-Statistik meist leer | **hoch** für Spieler-Auswertungen |
| 10 | ReID | FastReID MSMT17 (nicht kommerziell), alle 30 Bilder | **gemessen** 65 % zugeordnet, 70 bis 84 % davon richtig | **34 min pro 8 min CPU**, 56 % der Analyse | Lizenz: nicht auslieferbar | mehr nummerierte Zeit | tief (heute), Kosten hoch |
| 11 | Rollen (Torhüter, Schiri) | Klassifikator aus `ml/roles` | gemessen Torhüter Recall 67 %, Präzision 86 % | klein | **im Image nicht vorhanden** (aus) | - | mittel (siehe Torhüter) |
| 12 | Ball | Ballnetz hrp1 (3 Bilder, jedes Bild) + Tracker v2 | **gemessen** Gold v1 (42 Clips): 80 % (Ensemble), 73 % (GPU-Empfehlung), 63,5 % (CPU-Testsetting) | 53 min belegt pro 8 min CPU; GPU etwa 1 USD pro Spiel | DeepSport im Training (nicht kommerziell); Präzision auf ballfreien Bildern nicht messbar | Ball in der Taktik-Ansicht | mittel |
| 13 | Ballbesitz (Halter) | Ball in Spielerbox; Pass/Fehlpass | **gemessen** Forschung AUC 0,78, Top-1 43 % (Ziel 60 %); im Produkt nur Statistik | klein | wird von den Ereignissen **nicht** benutzt | kaum sichtbar | mittel |
| 14 | Ballbesitz-Phasen, Angriffe | 200-ms-Fenster, Hälften-Anteil ≥ 0,67, Gegenstoss ab 18 m Vorstoss | real **nicht gemessen** | Sekunden | ohne Torhüter keine Seiten, dann **keine Ereignisse** (`missing: goalkeepers`); Lücken werden überbrückt | Phasen-Liste, Ballbesitz-Anteil | hoch |
| 15 | Torhüter | Kit-Farbe, Position (60 % im 6,5-m-Raum), Rollenmodell | **nicht gemessen** | Sekunden | Sonderfarbe → Cluster «Schiedsrichter» → Positionsregel überspringt ihn | Torhüter-Ansicht (ab Team-Plan) | hoch (zieht Seiten und Ereignisse mit) |
| 16 | Tor- und Wurfkandidaten | Vorlage aus Kameraschwenk, Personenbewegung, Ruhe nach dem Tor; Quote pro Minute; Pausenmaske | **gemessen** Endtest 42 Spiele: Tor-Recall 75 %, Präzision 29 %; Wurf-Recall 85 %, Präzision 26 %; Median 2,8 s zu spät | Sekunden | viele Fragen (99 min: 122); feste Kamera nicht gemessen; Lauf U: 0 Kandidaten (PR #119) | Prüfen: «War das ein Tor?» | **hoch** (Aufwand des Trainers) |
| 17 | Spieluhr, Spielstand | Tesseract auf Overlay; PP-OCR auf Hallentafel | Overlay 5/5 Tore (1 Clip); Tafel: Spielzeit 21 statt etwa 54 min auf 99-min-Video; Ziffernfehler nicht gemessen | Sekunden bis Minuten | Tafel ausser Bild; Lücken | Tore, Spielstand, Pausen | mittel |
| 18 | Wurfort | Torschütze per Nummer, sonst nächster Angreifer in 10 s vor dem Tor | **nicht gemessen**; Overlay-Clip: 4 von 5 Orten vom nächsten Angreifer, nicht vom Schützen | Sekunden | trifft Kreisläufer oder Flügel statt Schütze; nur mit Overlay- oder Tafel-Toren | Wurfbild | mittel |
| 19 | Torzone (wo im Tor) | **existiert nicht** im Code | - | - | - | Text «keine Torzonen» (`analysis-views.tsx`) | - |
| 20 | Formationen | Regel: Verteidiger-Tiefe → 6-0, 5-1, 3-2-1 usw. | nicht gemessen | Sekunden | abhängig von Seiten, Teams; Abtastung setzt 25 fps voraus (`formation.py:130`) | Formations-Anteile | tief |
| 21 | Spielbericht-Abgleich | Tore im 20-s-Fenster, `auto_accept` von Kandidaten | **nicht auf echten Spielen gemessen**; mit Protokoll 94 % der Würfe am richtigen Kandidaten (dev) | Sekunden | 10 s Versatz im Protokoll → fast alles falsch | Tore aus Bericht im Video | mittel |
| 22 | Statistiken | `handball_metrics.stats`, «unbekannt» statt 0 bei Quoten | nicht gegen Wahrheit gemessen | - | PDF zeigt Würfe, Paraden, Fehlwürfe als **0**, wenn unbekannt (`report_pdf.py:285`) | Übersicht, PDF | mittel |
| 23 | Szenen, Highlights, Feed | Clips um Ereignisse, Reels (Worker) | - | Minuten | bei **jedem** erfolgreichen Lauf neues Reel (auch Klick-Neulauf; PR #123) | doppelte Highlights | tief |
| 24 | PDF, Präsentation | `report_pdf.py`, `export.py` (MP4) | - | Minuten | siehe Statistiken | Bericht | tief |
| 25 | Spieltag | Live-Marken am Spielfeldrand, Abgleich nach Analyse | synthetisch 200/200 innerhalb 2 s | - | - | Marken im Video | tief |

## 5. Top-10-Schwachstellen nach Wirkung auf den Nutzer

Reihenfolge nach dem, was der Trainer am stärksten merkt: ob er überhaupt etwas bekommt, wie lange
er wartet, wie viel er selbst korrigieren muss, und ob er den Zahlen trauen kann.

### 1. Ohne Klick kein Feld, ohne Feld fast nichts

- **Befund:** Die automatische Kalibrierung liegt auf dem Endtest bei 0 von 28 richtig. Auf Staging
  bekam **keiner der 2 Uploads** ein automatisches Feld (beide `flat_view`, Kamera etwa 3,4 m).
  Dann fehlen Positionen, Phasen, Ereignisse, Wurforte und Statistik.
- **Tiefe Kameras:** Die Grenze von 10° Blickwinkel schliesst den typischen Vereinsfall
  grundsätzlich aus. Das ist eine bewusste Sicherung gegen falsche Felder, kein Fehler.
- **Zeitpunkt:** Der Trainer erfährt das erst nach der vollen Analyse (Lauf U: 1 h für 8 min). Der
  Klick-Neulauf dauert dann nur 19 s, aber der Trainer muss zurückkommen.
- **Vorschlag (Regel und UI):** Klicken als Standardweg statt als Ausnahme.
  1. Die Kamerabewegung läuft heute im selben Durchgang wie alles andere. Sie kommt als eigener,
     schneller Schritt nach vorn (4 min pro 8 min, und nur jedes n-te Bild ist nötig fürs
     Panorama).
  2. Sobald das Hallenbild steht, fragt die App einmal pro Halle die Linien-Klicks ab, noch während
     `observe` läuft. Die Analyse ist dann in einem Zug fertig.
  3. Die automatische Kalibrierung bleibt als Vorschlag, den der Trainer mit einem Klick bestätigt.
  4. Die Hallen-Wiederverwendung soll auch ohne `match.venue` greifen, mit der Heimhalle des Teams
     als Fallback, und eine Plausibilitätsprüfung bekommen (`court_doubt` auf dem übertragenen Feld).
- **Aufwand:** M (Worker: Panorama-Vorstufe und Zwischen-Callback; Web: Klick-Schritt im
  Upload-Ablauf). Für die Plausibilitätsprüfung der Hallen-Wiederverwendung S.

### 2. Laufzeit und Kosten auf CPU

- **Befund:**
  - 8 min Video brauchen auf Staging etwa 29 min Ingest plus 60 min Analyse. Ein ganzes Spiel
    (60 min) bräuchte rund 3,5 h Ingest und 7 bis 8 h Analyse, über dem RQ-Timeout von 6 h.
  - ReID frisst 56 % der Analysezeit, darf aber wegen der MSMT-Lizenz gar nicht ausgeliefert werden.
  - Das Ballnetz läuft auf CPU nur bis 12 min Videolänge (`ball_max_minutes`), ist also bei echten
    Spielen auf Staging aus.
- **Vorschlag:**
  - **Sofort (Regel):** ReID auf CPU-Umgebungen aus (`HB_REID_MODEL` leer). Sein Nutzen ist klein
    (25 → 35 % nummerierte Zeit), die Lizenz fehlt, und die Analyse wird etwa doppelt so schnell.
  - **Ingest (Code):** HLS-Leiter und Proxy in einem ffmpeg-Aufruf mit geteiltem Decode, Preset
    `veryfast` für 720p. Das spart erwartungsgemäss 30 bis 40 % des Ingests (geschätzt).
  - **Analyse (Infra):** die GPU-Umstellung (T4, gemessen 0,87 bis 1,27 USD pro Spiel) ist
    entschieden und muss nur noch ausgerollt werden; das macht die Hauptsitzung.
- **Aufwand:** S (ReID aus), M (Ingest), Infra bei der Hauptsitzung.

### 3. Zu viele Fragen bei den Torkandidaten

- **Befund:** Tor-Präzision 29 %, Wurf-Präzision 26 %: der Trainer beantwortet drei falsche
  Vorschläge für jeden richtigen. Das 99-min-Video ergab 122 Fragen. Die Kandidaten kommen im
  Median 2,8 s nach der Marke, der Clip zeigt also oft schon das Zurücklaufen. Auf fest montierten
  Kameras ist die Vorlage nicht gemessen; sie wurde auf schwenkenden Streams gelernt.
- **Vorschlag (Modell und Daten):**
  1. Die Antworten der Trainer in «Prüfen» (Ja/Nein, Zeitpunkt) als Labels speichern und exportieren.
     Jede beantwortete Frage ist ein kostenloses Trainingsbeispiel.
  2. Auf diesen Clips einen kleinen Zweitstufen-Klassifikator trainieren: Ballpfad nahe Tor,
     Torraum-Belegung, Pfiff im Audio (`audio_8k.wav` liegt schon da). Er sortiert die Kandidaten
     um, statt neue zu finden.
  3. Den Spieluhr-Stopp als Merkmal nutzen. Nach einem Tor läuft die Uhr in den meisten Ligen
     weiter, bei Timeouts nicht; das trennt Timeouts von Toren.
  4. Den Zeitversatz von 2,8 s auf den Dev-Marken korrigieren, nicht auf dem Endtest.
- **Aufwand:** S (Labels speichern), M (Klassifikator), S (Versatz).

### 4. Torhüter weg, Seiten weg, Ereignisse weg

- **Befund:** Die Spielrichtung kommt nur von den Torhütern (`events.py:79-136`). Ohne Torhüter
  bleibt die ganze Ereignisliste leer (`missing: ["goalkeepers"]`), also keine Phasen, keine
  Anwürfe und keine Heuristik-Tore. Ein Torhüter in eigener Trikotfarbe landet im k-Means oft in
  einem kleinen dritten Cluster. Liegt der mehr als 25 Lab-Einheiten von beiden Teams weg, heisst
  er «referee» (`teams.py:222`).
  - Der Kommentar dort sagt «fixed later by position». Die Positionsregel `assign_goalkeepers`
    überspringt aber genau die Schiedsrichter (`events.py:510`).
  - Das Rollenmodell, das das retten könnte, ist nicht im Image.
- **Vorschlag (Regel, dann Modell):**
  1. Die Seiten bekommen eine zweite Quelle, die keine Torhüter braucht. Beim Anwurf stehen beide
     Teams in der eigenen Hälfte; `refine_teams` erkennt solche Momente schon. Daraus folgt direkt,
     welche Seite Heim verteidigt.
  2. Die Positionsregel bekommt eine strengere Variante für «referee»-Cluster-Tracks: mindestens
     80 % der Zeit im 6,5-m-Raum eines Tores und kein zweiter Torhüter-Kandidat am selben Tor. Der
     Torrichter steht neben dem Tor, aber selten so dauerhaft.
  3. Beides vorher auf den Dev-Clips mit Torhüter-Labels messen.
- **Aufwand:** M (Regel und Messung). Das Rollenmodell mit sauberer Lizenz neu trainieren ist L.

### 5. Spieler-Auswertungen fast leer (Nummern, Tracking)

- **Befund:**
  - Nur 25 % der Spielerzeit tragen eine Nummer. Auf dem 99-min-Video wurde keine der 34 gelesenen
    Nummern einem Track zugeordnet.
  - Die Tracks zerfallen: 276 IDs für 16 Personen in 8 Minuten.
  - Eine echte Tracking-Messung (MOTA, IDF1) gibt es nicht. Das Farbtor im Tracker ist im lernenden
    Pfad ausgeschaltet (`colour_weight 0`, `features=None`, `observe.py:833`).
- **Vorschlag (Daten, dann Modell):**
  1. Fünf Clips à 1 min mit Spieler-Boxen und IDs labeln. Das Werkzeug dafür gibt es schon
     (`ml/gold/players_prelabel.py`). Erst damit lässt sich jede Tracking-Änderung beurteilen.
  2. Das Farbtor einschalten und auf diesen Clips messen.
  3. Auf GPU Nummern auf jedem Detektionsbild lesen (`number_every 3`) und gegen den Kader
     abstimmen.
  4. Einen eigenen Nummern-Erkenner auf den gesammelten Torso-Crops trainieren; im Lauf U waren es
     7 939 Crops in 8 min.
- **Aufwand:** M (Labels), S (Farbtor messen), M bis L (Nummern-Erkenner).

### 6. Ballbesitz und Phasen ohne Ball und ohne Messung

- **Befund:** Phasen entstehen nur aus Positionen, also aus der Frage, welches Team in der
  gegnerischen Hälfte steht. Der Ballpfad (80 % auf Gold) fliesst nicht ein. Lücken ohne Halter
  werden überbrückt, auch über Timeouts (`events.py:212-228`). Gegen eine Wahrheit gemessen ist
  davon nichts.
- **Vorschlag (Daten, dann Regel):**
  1. Auf den 42 Gold-Clips Ballbesitzwechsel markieren; die Ballpunkte sind schon da, es sind etwa
     2 Stunden Arbeit.
  2. Den Ballhalter aus dem Ballpfad als zweite Quelle mit der Positionsregel verbinden.
  3. Lücken über 3 s beenden eine Phase.
- **Aufwand:** M.

### 7. Wurfort unzuverlässig, Torzone fehlt

- **Befund:** Ohne gelesene Nummer nimmt der Wurfort den nächsten Angreifer der letzten 10 s
  (`shots.py`). Im einzigen geprüften Fall war das 4 von 5 Mal nicht der Schütze. Eine Torzone (wo
  im Tor) berechnet der Code gar nicht, die Web-Ansicht zeigt dafür nur einen Leertext. Gemessen ist
  nichts (`backlog.md`).
- **Vorschlag (Modell):**
  1. Schütze ist der letzte Ballhalter vor einem schnellen Ballflug Richtung Tor. Der Ballpfad hat
     auf der Spielzeit fast überall einen Punkt.
  2. Wurfort ist dessen Position im Abwurfmoment.
  3. Die Torzone ergibt sich aus dem Ballpunkt beim Durchgang durch die Torebene; der Torrahmen ist
     aus der Kalibrierung bekannt.
  4. Messen auf den Endtest-Würfen ist erlaubt, tunen nur auf den Dev-Würfen.
- **Aufwand:** M.

### 8. Pausen und Spieluhr

- **Befund:** Die Hallentafel liefert auf dem 99-min-Video 21 statt etwa 54 min Spielzeit. Die Tafel
  ist oft nicht im Bild. Pausen mit stehender Kamera fängt die Pausenmaske. Eine fest montierte
  Kamera mit leichtem Drift wurde komplett als Pause erkannt (Lauf U, behoben). Ziffernfehler der
  Tafel sind nicht gemessen.
- **Vorschlag (Regel und Daten):**
  1. Uhr-Lücken mit der Uhr-Logik füllen: läuft die Uhr vor und nach einer Lücke mit passender
     Differenz, dann lief sie durch.
  2. Die Schwelle «bewegt» in `motion.py` auf etwa 5° anheben und auf dem Kalibrierungs-Dev-Set
     prüfen. Heute gelten Stativkameras mit Drift als bewegt; das schickt sie durch den
     Panorama-Pfad mit einer Brennweite aus der Bewegung, die bei fast stehender Kamera kaum
     bestimmbar ist.
  3. 20 Tafel-Ablesungen pro Spiel gegen die echte Uhr prüfen.
- **Aufwand:** S bis M.

### 9. Ergebnisse, die nicht stimmen oder doppelt sind

- **Befund:**
  - Das PDF zeigt Würfe, Paraden und Fehlwürfe als 0, wenn sie unbekannt sind; nur die Quoten
    zeigen «-» (`report_pdf.py:285-300`).
  - Ein Spiel mit nur heuristischen Anwürfen gilt als «hat Ereignisse» und zeigt dann Nullen
    (`match-view.tsx:873`).
  - Jeder erfolgreiche Lauf, auch ein Klick-Neulauf, legt neue Highlight-Reels an
    (`video_callbacks.py:251`). Behoben für unveränderte Szenen in PR #123.
  - Nach einem Lauf mit `needs_calibration` bleiben alte Heuristik-Ereignisse und die alte
    Kalibrierung stehen (`auto_events.py:339-342`, `video_analysis.py:488-493`).
  - Die Job-Stufen «Tracking» und «Upload» bleiben bei `needs_calibration` auf «pending» (Lauf U).
- **Vorschlag (Code):** unbekannte Zählwerte als «-» ausgeben; Reels nur beim ersten Lauf oder bei
  geänderten Ereignissen neu bauen; bei `needs_calibration` die Heuristik-Zeilen des Fensters
  löschen; offene Stufen beim Erfolg auf «skipped» setzen.
- **Aufwand:** S je Punkt (eigene kleine PRs).

### 10. Modelle ohne saubere Lizenz

- **Befund:** ReID (MSMT17), die Ballnetze (DeepSport), das Rollenmodell und das Halter-Modell sind
  nur für Forschung. Die beste gemessene Ballqualität (80 %) hängt an DeepSport.
- **Vorschlag (Daten):** Die Gold-Labels sind eigene Daten (Ball 1 553 Punkte, Würfe, Kalibrierung).
  Damit nach Plan `tracking-strategie.md` Abschnitt 9 ohne DeepSport neu trainieren, Ziel 70 % auf
  Gold v1. ReID streichen (Punkt 2) statt ersetzen, bis eigene Spieler-Labels da sind.
- **Aufwand:** L. Blockiert den Livegang, nicht die Testphase.

## 6. Unterwegs behoben

- **PR #119, Torkandidaten bei fester Kamera mit leichtem Drift:** Die Pausenregel «geparkte
  Kamera» gilt nur noch für bediente Kameras, also bewegt und mindestens 10° Schwenk über das
  Video. Lauf U: 0 → 16 Kandidaten, 4 von 4 Toren.
- **PR #123, Highlights:** Kein zweites automatisches Reel mit denselben Szenen, also nicht nach
  jedem Klick-Neulauf und jedem weiteren Spielteil.
- **PR #121, Ballpfad-Abdeckung:** Sie teilt jetzt durch die Videobilder statt die Detektionsbilder
  (Lauf H: 1,2 statt plausibel 0,4). `Observations.total` ist neu die Bildzahl statt des letzten
  Index.

## 7. Für die Analyse-Sitzung (Modelle)

Modellbezogen, nach erwartetem Nutzen:

1. **Torkandidaten:** Prüfen-Antworten als Labels, Zweitstufen-Klassifikator, Versatz 2,8 s
   (Punkt 3). Feste Kameras sind nicht gemessen; Lauf U ist ein erster Fall (4 Tore, Overlay als
   Wahrheit).
2. **Torhüter, Seiten:** Seiten aus Anwurf-Formationen; Torhüter aus dem «referee»-Cluster
   (Punkt 4).
3. **Ballhalter, Wurfort, Torzone aus dem Ballpfad** (Punkte 6 und 7).
4. **Spieler-Labels** für eine echte Tracking-Messung, Farbtor messen (Punkt 5).
5. **Schwelle «bewegt»** in `motion.py` gegen das Kalibrierungs-Dev-Set prüfen (Punkt 8).
6. **ReID auf CPU aus** (Punkt 2), Ersatz erst mit eigenen Labels.

## Anhang A: Lokaler Lauf Horgen H1 (5 min)

Beobachtet am 25.11. auf 4 geteilten CPU-Kernen (parallel liefen andere Rechnungen), Stand des
Branches vor #119, #121 und #123. Ohne Klickpunkte, ohne Trikotfarben, alle Modelle aktiv. Kein
Gold für diesen Clip: die Qualität ist nur geschätzt, nicht gemessen.

| Grösse | Wert | Einordnung |
|---|---|---|
| Laufzeit | 6323 s für 300 s Video (21x) | ein 60-Minuten-Spiel bräuchte so über 20 h, weit über dem 6-h-Timeout |
| Kritischer Pfad | Ballnetz-Thread 6240 s belegt (ball_net 4005 s), ReID 1168 s, Detektion 616 s, Nummern 225 s, Kamerabewegung 147 s | hier bremst das Ballnetz, nicht ReID wie in Lauf U: auf CPU sind beide zu teuer |
| Kalibrierung | automatisch (heuristic), akzeptiert: Kamerahöhe 5.9 m, Blickwinkel 16.6°, goal_score 0.74, floor_fit 0.63 | bei höherer Kamera klappt die Automatik; die zwei Staging-Uploads (3.4 m) scheiterten |
| Kamera | pan_deg 85.4, zoom_ratio 1.07, keine Schnitte | bediente Kamera, die Pausenregel greift korrekt (eine Pause 230 bis 254 s) |
| Tracks | 151 roh, 138 nach Zusammenführen, Median 12.9 s | für rund 16 Personen in 5 min: Spieler zerfallen weiter in viele Stücke |
| Teams | 71 home, 53 away, 10 Schiedsrichter, 3 + 1 Torhüter-Tracks | Torhüter erkannt, also Seiten und Ereignisse vorhanden |
| Nummern | 8 von 138 Tracks (4 gelesen, 4 über Erscheinung); 1499 von 2420 Kästchen gelesen | OCR liest oft, aber die Abstimmung pro Track gibt selten eine Nummer frei |
| Ereignisse | 5 Ballbesitzwechsel, 2 Gegenstösse, keine Würfe, keine Tore | ohne Wurf- und Torereignisse bleibt die Statistik leer |
| Ballbesitz | 7 Phasen; eine Heimphase dauert 72 s (96.4 bis 168.8 s) | unplausibel lang: das Überbrücken von Lücken (Schwäche 6) zeigt sich hier |
| Ballzeit | away 80.6 s, home 34.6 s bei 245.6 s Spielzeit laut Hallenuhr | knapp die Hälfte der Spielzeit einem Team zugeordnet |
| Ballabdeckung | gespeichert 2.418 (6048 Punkte / 2501 Detektionsbilder) | richtig wären 6048 / 7502 = 0.81: derselbe Fehler wie in Lauf H, behoben in #121 |
| Hallenuhr | 13 Ablesungen, 2 Spielintervalle, 0 Tore erkannt | Uhr ja, Tore aus der Anzeige nein |
| Torkandidaten | 18 (5 bei Rate 1, 9 bei Standardrate 2) | ohne Gold nicht bewertbar; bei der gemessenen Präzision von rund 27 % wären das etwa 2 bis 3 echte Tore |

Fazit: wenn die Kalibrierung gelingt, liefert die Kette Tracks, Teams, Torhüter, Seiten,
Formationen und Ballbesitz. Würfe fehlen trotzdem ganz, die Ballbesitzphasen sind zu lang, und
die Laufzeit auf CPU ist für ganze Spiele nicht tragbar. Das bestätigt die Rangfolge in Abschnitt 5.
