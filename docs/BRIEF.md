# Auftrag an Claude Code: Handball AI Plattform (Production Ready)

> So verwendest du diese Datei: Leg sie als `docs/BRIEF.md` in ein leeres Repository und starte Claude Code mit:
> "Lies docs/BRIEF.md vollständig und arbeite es Meilenstein für Meilenstein ab. Beginne mit Meilenstein 0."

---

## 0. Deine Rolle und Arbeitsweise

Du bist das komplette Engineering-Team für eine produktionsreife SaaS-Plattform: Product Engineer, Backend, Frontend, ML/Computer Vision, DevOps und QA. Du baust die **Handball AI Plattform**. Ein Verein lädt ein Spielvideo hoch, die Plattform analysiert alles automatisch und liefert Spielbericht, Clips, Statistiken, Spielzüge, Taktiktafel und Erkenntnisse.

Arbeitsregeln:

1. **Meilensteine strikt der Reihe nach** (Abschnitt 14). Jeder Meilenstein endet lauffähig, getestet und committet. Am Ende jedes Meilensteins hältst du an und schreibst einen kurzen Bericht in `docs/progress/M<n>.md`: was gebaut ist, was getestet ist, was offen ist, welche Entscheidungen du getroffen hast. Danach wartest du auf "weiter".
2. **Erst planen, dann bauen.** Zu Beginn jedes Meilensteins legst du einen Plan mit Tasks an. Grössere Architekturentscheidungen dokumentierst du als ADR in `docs/adr/NNN-titel.md`.
3. **Keine Fake-Ergebnisse.** Wenn ein ML-Schritt ohne trainiertes Modell oder ohne Daten nicht wirklich funktioniert, gibst du das ehrlich aus. Nutze dann eine klar markierte Fallback-Implementierung (`source: "heuristic"` oder `source: "mock"` im Datenmodell) und schreib es in den Bericht. Demo-Daten sind in der UI immer als Demo gekennzeichnet.
4. **Tests sind Pflicht.** Backend: pytest mit mindestens 80 % Abdeckung in Domänenlogik und API. Frontend: Vitest für Logik, Playwright für die Kernabläufe. ML: Evaluations-Skripte mit festen Metriken (Abschnitt 10).
5. **Fragen sammeln, nicht blockieren.** Was du nicht entscheiden kannst, schreibst du in `docs/OPEN_QUESTIONS.md`. Du arbeitest mit einer sinnvollen Annahme weiter und markierst sie.
6. **Sicherheit und Datenschutz von Anfang an** (Abschnitt 12), nicht am Schluss.
7. **Sprache:** Code, Bezeichner, Commits und technische Doku auf Englisch. Die UI ist auf Deutsch (de-CH: "ss" statt "ß"), mit i18n vorbereitet für Englisch und Französisch.
8. **Keine langen Gedankenstriche** in UI-Texten und generierten Texten. Kommas oder Punkte verwenden.

---

## 1. Produktvision

**Ein Satz:** Video hochladen, alles andere passiert automatisch. Kein manuelles Tagging, kein Analyst nötig.

Zielgruppe:
- Amateur- und Nachwuchsvereine im Handball, zuerst in der Schweiz und in Deutschland, dann in Skandinavien.
- Heute arbeiten diese Vereine mit Papier-Matchreports und Taktiktafeln oder werten ihre Videos gar nicht aus.
- Profi-Tools wie handball.ai oder Sportscode sind für sie zu teuer und zu aufwendig.
- Kamera-Anbieter wie Veo, Spiideo oder asport filmen zwar, werten Handball aber nicht automatisch aus.

Versprechen an den Nutzer:
1. **Hochladen und fertig:** Nach etwa 30 bis 60 Minuten ist die Analyse fertig, ohne Klick zum Markieren.
2. **Jede Zahl führt zum Video:** "7 Fehlwürfe von Rechtsaussen" ist ein Link auf genau diese 7 Clips.
3. **Probleme statt Zahlenfriedhof:** Die Plattform findet wiederkehrende Muster und Schwächen und formuliert sie in klaren Sätzen, mit Video als Beleg.
4. **Vom Video zur Taktiktafel:** Gespielte Spielzüge werden automatisch erkannt und als animierte Taktiktafel dargestellt. Umgekehrt zeichnet der Trainer einen Spielzug, und die Plattform findet alle Szenen, in denen er gespielt wurde.
5. **Sich selbst durchanalysieren:** Das Team erkennt über die Saison, wo es steht, was funktioniert und was nicht. Das gilt für jeden Spieler, jede Position, jeden Spielzug und jede Phase.

Der Torhüter-Bereich ist ein Zusatzmodul und nicht der Schwerpunkt.

---

## 2. Scope

### In Scope (Version 1.0 production ready)
- Mandantenfähige Web-App: Vereine, Teams, Saisons, Kader, Rollen
- Video-Upload (gross, fortsetzbar) und Import per Link
- Vollautomatische Analyse-Pipeline (Abschnitt 7)
- Spielbericht, Erkenntnisse, Spielverlauf, Wurfanalyse, Spielerprofile, Saisonstatistik
- Video-Player mit Ereignis-Zeitleiste, Filtern, Playlists und Zeichenwerkzeug
- Spielzugerkennung und Taktiktafel (Abschnitt 8)
- Gegneranalyse
- Trainingsbibliothek und Aufgaben an Spieler
- Torhüter-Modul (Analyse, ohne Antizipationstrainer)
- Teilen, Export (PDF, Clips), Benachrichtigungen
- Abos und Zahlung (Stripe)
- Admin-Backoffice für den Betreiber
- Datenschutz, Einwilligungen, Löschung, Audit-Log

### Out of Scope (später)
- Antizipationstrainer für Torhüter (eigenes Projekt, wird später angebunden)
- Native Mobile Apps (v1 ist eine PWA)
- Live-Analyse während des Spiels
- Beachhandball

---

## 3. Rollen und Rechte

Mandantenstruktur: `Organization (Verein) → Team → Season`. Personen sind über `Membership` mit einer Rolle einem Team zugeordnet. Eine Person kann in mehreren Teams verschiedene Rollen haben.

| Rolle | Rechte |
|---|---|
| `org_admin` | Teams anlegen und löschen, Abo und Zahlung, Personen einladen, alle Teams lesen |
| `coach` | Spiele anlegen, Videos hochladen, alles im Team lesen und schreiben, Kader pflegen, Playlists, Taktiktafel, Trainingsbibliothek, Aufgaben, Freigaben |
| `analyst` | wie `coach`, aber ohne Kader- und Rechteverwaltung |
| `player` | eigene Szenen, eigene Statistik, freigegebene Team-Inhalte, Aufgaben, Trainingsbibliothek |
| `goalkeeper` | wie `player`, zusätzlich das Torhüter-Modul |
| `guest` | nur einzelne geteilte Inhalte per Link, nur lesen, mit Ablaufdatum |
| `platform_admin` | Betreiber-Backoffice (Support, Jobs, Modelle), getrennt vom Kundenbereich |

Regeln:
- Ein Spieler sieht die Daten seiner Mitspieler nur, wenn das Team-Setting `players_see_team_stats` aktiv ist. Bei Nachwuchsteams (`team.is_youth = true`) ist es standardmässig aus.
- Die Rechte werden serverseitig auf Ressourcenebene durchgesetzt, nie nur im Frontend. Für jede Rolle und jeden Endpunkt gibt es einen Test (Policy-Test-Matrix).
- Geteilte Links sind signiert, laufen ab und können widerrufen werden.

---

## 4. Handball-Fachwissen (Domänenmodell der Analyse)

### 4.1 Spielfeld und Koordinaten
- Das Spielfeld misst 40 m × 20 m. Koordinatensystem in Metern: x = 0 an der linken Torlinie bis 40, y = 0 an der unteren Seitenlinie bis 20, Mittelpunkt (20, 10).
- Das Tor ist 3 m breit und 2 m hoch und steht mittig auf der Torlinie, y von 8.5 bis 11.5.
- Torraumlinie (6 m): zwei Viertelkreise mit Radius 6 m um die Torpfosten, verbunden durch eine Gerade. Freiwurflinie (9 m): gestrichelt, analog mit Radius 9 m. 7-m-Linie: 1 m lang, 7 m vor dem Tor. Torhütergrenzlinie bei 4 m.
- Alle Analysen werden in **Angriffsrichtung normalisiert**: Das angegriffene Tor liegt immer bei x = 40. So sind beide Halbzeiten und beide Teams vergleichbar.
- Die Court-Geometrie liegt als eine einzige Quelle in `packages/court/` und wird von Backend, ML und Frontend gemeinsam genutzt (Polylinien und Keypoints).

### 4.2 Positionen
Angriff: `LA` (Linksaussen), `RL` (Rückraum links), `RM` (Rückraum Mitte), `RR` (Rückraum rechts), `RA` (Rechtsaussen), `KM` (Kreismitte), `TW` (Torhüter). Abwehrpositionen werden aus der Formation abgeleitet.

### 4.3 Wurfzonen auf dem Feld
Die Wurfzonen sind fest definiert und in `packages/court/zones.ts` und `zones.py` hinterlegt:
- **Aussen links** und **Aussen rechts**: spitzer Winkel, nahe der Seitenlinie
- **Rückraum links, Mitte, rechts**: hinter oder auf der 9-m-Linie
- **Halbposition links, Mitte, rechts** zwischen 6 und 9 m
- **Kreis links, Mitte, rechts**: am oder im 6-m-Raum
- **7 m**
- **Gegenstoss**: Wurf innerhalb von x Sekunden nach Ballgewinn, unabhängig von der Position (Parameter, Standard 6 s)
- **Fernwurf**: Wurf aus über 15 m Entfernung
- **Leeres Tor**: Wurf auf das leere Tor (Wurfart `empty_net`), aus jeder Entfernung

### 4.4 Torzonen
Das Tor ist in ein 3×3-Raster geteilt: `TL TC TR / ML MC MR / BL BC BR`. Gespeichert wird **immer aus Sicht des Werfers**. Die UI kann auf die Sicht des Torhüters umschalten (gespiegelt). Diese Konvention wird überall einheitlich verwendet und dokumentiert.

### 4.5 Ereignis-Taxonomie
Angelehnt an die Taxonomie von Biermann et al. (EIGD, 2021). Jedes Ereignis hat `t_start`, `t_end` (Videozeit in ms), `match_clock`, `team_id`, `player_id?`, `court_xy?`, `confidence` (0 bis 1), `source` (`model`, `heuristic`, `official_feed`, `scoreboard_ocr`, `goal_cam`, `user_correction`) und `attributes` (JSON).

| Ereignis | Wichtige Attribute |
|---|---|
| `shot` | `outcome`: goal, save, miss, post, blocked · `shot_zone` · `goal_zone` · `shot_type`: jump_shot, standing, pivot, wing, fast_break, penalty, empty_net · `distance_m` · `hand` · `assist_player_id?` |
| `pass` | `from`, `to`, `success` |
| `turnover` | `type`: bad_pass, catch_error, steps, double_dribble, offensive_foul, line_violation, passive_play, other |
| `steal` | |
| `foul` / `free_throw` | |
| `seven_meter_awarded` | Fouler, Gefoulter |
| `suspension_2min` · `yellow_card` · `red_card` | |
| `timeout` | Team |
| `throw_off` | Anwurf, bestätigt Tore |
| `substitution` | inklusive Torhüterwechsel und 7-gegen-6 |
| `goalkeeper_save` | wird aus `shot` abgeleitet, separat indexiert |

### 4.6 Ballbesitz und Phasen
- `Possession`: zusammenhängender Ballbesitz eines Teams mit Start, Ende, Startart (nach Tor, nach Parade, nach Ballgewinn, nach Fehlwurf, nach Freiwurf) und Ergebnis (Tor, Fehlwurf, Parade, Ballverlust, 7 m herausgeholt, 2 Minuten herausgeholt, Halbzeit).
- `Phase` innerhalb eines Ballbesitzes: `fast_break_1` (erste Welle), `fast_break_2` (zweite Welle), `quick_center` (schnelle Mitte), `transition`, `set_attack` (Positionsangriff), `retreat`, `set_defense`.
- Spielsituation: Gleichzahl, Überzahl, Unterzahl, 7 gegen 6 (leeres Tor), 7-m-Situation.

### 4.7 Taktik-Begriffe (für die Spielzugerkennung)
- **Abwehrformationen:** `6-0`, `5-1`, `3-2-1`, `4-2`, `3-3`, `5+1` (Manndeckung gegen einen Spieler), `4+2`, offensive Vollmanndeckung
- **Angriffsaktionen:**
  - Kreuzung: zwei Spieler tauschen in der Breite ihre Reihenfolge, der Ball wechselt dabei
  - Sperre: der Kreisläufer stellt sich einem Abwehrspieler in den Weg
  - Einlaufen: ein Aussen oder Rückraumspieler läuft an den Kreis, das ergibt einen zweiten Kreisläufer
  - Parallelstoss: mehrere Spieler stossen nacheinander in dieselbe Richtung
  - Stossen, Durchbruch, Abwurf über Kreis, Rückpass, Kempa-Trick
- **Spielzug** = eine wiederkehrende Abfolge von Laufwegen, Pässen und Aktionen im Positionsangriff, mit typischem Ende (Wurf von Position X).

### 4.8 Kennzahlen (exakte Definitionen in `packages/metrics/DEFINITIONS.md`)
- **Wurfquote:** Tore / Würfe (ohne geblockte Würfe; geblockte Würfe separat ausweisen)
- **Angriffseffizienz:** Tore / Ballbesitze
- **Ballverlustquote:** Ballverluste / Ballbesitze
- **Paradenquote:** Paraden / Würfe aufs Tor. Würfe aufs Tor sind Tore plus Paraden, also ohne Fehlwürfe neben das Tor und ohne Pfostentreffer. Pfostentreffer werden separat ausgewiesen.
- **Gegenstosstore**, **Tore nach schneller Mitte**
- **Effizienz in Überzahl und Unterzahl**
- **Tor-Läufe:** grösste Serie ohne Gegentor
- **Längste Phase ohne eigenes Tor**
- **xG (erwartete Tore):** pro Wurf ein Modell aus Distanz, Winkel, Wurftyp, Abwehrdruck (nächster Abwehrspieler) und Torhüterposition. In v1 ist das ein Logistik-Modell auf eigenen Daten, später ein trainiertes Modell. Es wird klar als Schätzung gekennzeichnet.
- **Spieler-Plus-Minus:** Tordifferenz, während der Spieler auf dem Feld steht
- **Laufmetriken:** Distanz, Sprints über 5 m/s, Höchstgeschwindigkeit, Zeit in Zonen

---

## 5. Datenmodell (PostgreSQL)

Lege das Schema mit SQLAlchemy 2 und Alembic an. Für jede Entität gilt: `id` als UUID, `created_at`, `updated_at`, `organization_id` (Mandant). Postgres Row Level Security ist als zweite Verteidigungslinie aktiv.

Kernentitäten (Mindestumfang, sinnvoll ergänzen):

- `Organization` (Name, Logo, Farben, Land, Plan, Stripe-IDs, Datenregion)
- `User` (E-Mail, Name, Sprache, Auth-Daten, Einwilligungen)
- `Team` (Name, Liga, `is_youth`, Geschlecht, Settings)
- `Season` (Label, Start, Ende)
- `Player` (Vorname, Name, Geburtsjahr optional, Wurfhand, Hauptposition, Nebenpositionen, Foto optional, verknüpfter `User` optional)
- `RosterEntry` (Player × Team × Season, Rückennummer, aktiv)
- `Membership` (User × Team, Rolle)
- `Opponent` (Name, Vereinsfarben, Notizen) und `OpponentPlayer` (Nummer, Name, sofern bekannt)
- `Match` (Team, Season, Opponent, Datum, Heim/Auswärts, Wettbewerb, Trikotfarben beider Teams inklusive Torhüter, Endstand, Halbzeitstand, Status)
- `VideoAsset` (Match, Rolle: `main`, `goal_cam_left`, `goal_cam_right`, `other`; Speicher-URI, Dauer, FPS, Auflösung, Codec, Prüfsumme, HLS-URI, Zeitversatz zur Hauptkamera, Qualitätsbericht)
- `ProcessingJob` (Match, Pipeline-Version, Status pro Stufe, Fortschritt, Logs-URI, Fehler, GPU-Sekunden, Kosten)
- `Calibration` (VideoAsset, Homographie(n) pro Zeitsegment, Reprojektionsfehler, Konfidenz)
- `Track` (Match, Team-Zuordnung, Rolle: player, goalkeeper, referee; Zuordnung zum `Player` mit Konfidenz; Zeitbereich)
- `TrackFrame` (in Parquet auf dem Objektspeicher, nicht in Postgres: Frame, Bounding-Box, Feldposition, Geschwindigkeit, Pose-Keypoints)
- `Event` (siehe 4.5)
- `Possession`, `Phase`, `GameSituation`
- `DefenseFormationSegment` (Team, Formation, Zeitbereich, Konfidenz)
- `PlayInstance` (erkannter Spielzug im Spiel: Possession, Cluster, Template-Match, Aktionen, Ergebnis, Keyframes für die Taktiktafel)
- `PlayCluster` (pro Team und Saison automatisch gefundene Spielzug-Familie: Name, Beschreibung, Prototyp-Keyframes, Häufigkeit, Erfolgsquote)
- `PlayTemplate` (vom Trainer gezeichneter Spielzug: Name, Formation-Kontext, Keyframes, Tags)
- `TacticsBoard` (gespeichertes Taktiktafel-Dokument: Frames, Spieler-Token, Pfeile, Notizen)
- `Clip` (Match, Start, Ende, Quelle: Event, Possession, PlayInstance oder manuell)
- `Playlist` und `PlaylistItem` (mit Kommentaren)
- `Annotation` (Zeichnung im Video: Zeitpunkt, Formen als JSON)
- `Insight` (Ebene: Spiel, Saison, Spieler, Gegner; Typ, Schwere, strukturierte Fakten als JSON, generierter Text, Belege als Clip-IDs, Gültigkeit, Feedback "hilfreich" oder "falsch")
- `Drill` (Trainingsbibliothek: Titel, Beschreibung, Ziel-Tags, Video oder Taktiktafel, Dauer, Alter)
- `Assignment` (Aufgabe an Spieler: Clip, Playlist oder Drill, Fälligkeit, Status)
- `Correction` (Nutzer-Korrektur eines Ereignisses oder einer Zuordnung; dient als Trainingsdaten)
- `Comment`, `Notification`, `ShareLink`, `AuditLog`
- `Subscription`, `Invoice`, `UsageRecord` (Spiele, Speicher, GPU-Minuten)
- `ModelVersion` (Name, Version, Metriken, Artefakt-URI, aktiv)

Wichtige Regel: Abgeleitete Statistiken werden **nie** als Wahrheit gespeichert. Sie werden aus Events, Possessions und Tracks berechnet (Materialized Views oder Cache-Tabellen mit Pipeline-Version). Nach einer Korrektur rechnet die Plattform nur die betroffenen Spiele neu.

---

## 6. Architektur und Tech-Stack

### 6.1 Monorepo
```
/apps
  /web            Next.js 15 (App Router), TypeScript, Tailwind, shadcn/ui, TanStack Query
  /api            FastAPI (Python 3.12), SQLAlchemy 2, Alembic, Pydantic v2
  /worker         Python: Pipeline-Orchestrierung (CPU-Jobs)
  /gpu-worker     Python: CV-/ML-Inferenz (CUDA-Image)
/packages
  /court          Spielfeldgeometrie, Zonen (TS + Python, aus einer JSON-Quelle generiert)
  /metrics        Kennzahl-Definitionen und Berechnung (Python), Typen (TS)
  /tactics        Taktiktafel-Datenformat, Renderer, Animation (TS)
  /api-client     aus OpenAPI generierter TS-Client
  /ui             gemeinsame UI-Komponenten
/ml
  /datasets       Lade- und Konvertierungsskripte (TeamTrack, EIGD-H, UNIRI-HBD, Roboflow, eigene)
  /training       Trainingsskripte pro Modell
  /eval           Evaluations-Harness und Golden Set
  /models         Modellkarten (keine Gewichte im Repo)
/infra
  docker-compose.yml   lokal: postgres, redis, minio, api, web, worker, gpu-worker (CPU-Fallback), mailpit
  /terraform           Produktion
/docs
```

### 6.2 Komponenten
- **Auth:** E-Mail mit Passwort (Argon2) und Magic Link, optional Google und Apple. Sessions als httpOnly-Cookies, CSRF-Schutz, 2FA (TOTP) für `org_admin`. Einladungen per signiertem Token.
- **API:** REST mit OpenAPI-Schema. Daraus wird der TS-Client generiert. Paginierung, Filter, einheitliches Fehlerformat (RFC 9457). Rate-Limits.
- **Jobs:** Redis plus RQ oder Celery (ADR schreiben). Jede Pipeline-Stufe ist ein idempotenter Job mit Checkpoint auf dem Objektspeicher, damit ein Neustart ab der letzten Stufe möglich ist.
- **GPU:** Der GPU-Worker läuft als Container und skaliert auf null. Gegen eine Abstraktion `GpuBackend` bauen, mit den Implementierungen `local` (CPU oder lokale GPU), `runpod`, `modal` und `k8s`. Die Kosten pro Spiel werden erfasst.
- **Speicher:** S3-kompatibel, lokal MinIO. Uploads direkt vom Browser per Multipart mit signierten URLs, fortsetzbar über tus oder S3 Multipart. Videos werden mit ffmpeg zu HLS transkodiert (720p und 1080p). Clips werden nicht geschnitten, sondern als Zeitfenster über HLS ausgespielt. Physisch geschnitten wird nur beim Download-Export.
- **Echtzeit:** Server-Sent Events für Job-Fortschritt und Benachrichtigungen.
- **LLM:** Die Claude API generiert die Texte der Erkenntnisse und Berichte, ausschliesslich aus strukturierten Fakten (Abschnitt 9.3). Der Zugriff liegt hinter einer Schnittstelle `TextGenerator`, die Prompts sind versioniert.
- **E-Mail:** über einen Transaktionsdienst (Postmark oder Resend, ADR), lokal Mailpit.
- **Zahlung:** Stripe Billing mit Checkout, Kundenportal und Webhooks.
- **Hosting:** Daten bleiben in der Schweiz oder EU (Kandidaten: Exoscale, Infomaniak, AWS eu-central-2 Zürich), per ADR entscheiden. Die Datenregion ist pro Organisation hinterlegt.
- **Observability:** Sentry (Frontend und Backend), OpenTelemetry-Traces, strukturierte JSON-Logs, Metriken für Jobdauer, Fehlerrate und GPU-Kosten. Health- und Readiness-Endpunkte.
- **CI/CD:** GitHub Actions mit Lint, Typecheck, Tests, Build, Container-Scan, Migrations-Check und Preview-Deploy pro Pull Request.

### 6.3 Performance und Effizienz der Pipeline (verbindlich)
Ein Spiel hat bei 60 Minuten und 50 fps rund 180'000 Bilder. Jedes Bild mit jedem Modell einzeln zu verarbeiten, ist zu langsam und zu teuer. Deshalb gilt:

1. **Streaming statt Einzelbilder:** Das Video wird als Stream dekodiert, wenn möglich hardwarebeschleunigt (NVDEC über PyNvVideoCodec, decord oder PyAV mit CUDA). Bilder werden nicht als Dateien auf die Festplatte geschrieben. Die Frames wandern als Batches direkt in GPU-Speicher und Modell.
2. **Batching:** Alle Modelle laufen mit Batches (Grösse automatisch nach GPU-Speicher). Kein Modellaufruf pro Einzelbild in Python-Schleifen.
3. **Optimierte Inferenz:** Die Modelle werden nach ONNX exportiert und mit TensorRT bzw. ONNX Runtime (CUDA EP) in FP16 ausgeführt, INT8 wo die Genauigkeit es erlaubt. Die PyTorch-Version bleibt als Referenz für die Evaluation.
4. **Kaskade statt alles auf alles:** Günstige Schritte zuerst, teure nur dort, wo sie gebraucht werden:
   - Detektion und Tracking auf dem Analyse-Proxy (z.B. 1280 px, 25 fps), nicht auf 4K mit 50 fps
   - Detektion nicht zwingend auf jedem Frame: Detektion in festem Takt (z.B. jeder 2. Frame), Tracker und Bewegungsmodell dazwischen, Takt adaptiv je nach Spieldynamik (ADR mit Messwerten)
   - Rückennummern nur auf ausgewählten Crops: Ein Lesbarkeits-Klassifikator wählt pro Track wenige gute Bilder aus, nur diese gehen in die Texterkennung, und zwar aus dem Originalvideo in voller Auflösung
   - Pose nur dort, wo sie zählt: in Zeitfenstern um Wurf-Kandidaten und für Spieler in Ballnähe oder Wurfdistanz, nicht für alle 14 Spieler in jedem Frame
   - Ballerkennung mit hoher Bildrate nur in Zeitfenstern um Ereignis-Kandidaten
   - Torkamera-Modelle nur in Fenstern um erkannte Würfe
5. **Parallelisierung:** Das Video wird in Abschnitte mit Überlappung zerlegt (z.B. 5 Minuten plus 5 Sekunden), die parallel verarbeitet werden. Die Tracks werden an den Übergängen zusammengeführt. CPU-Arbeit (Dekodieren, Nachbearbeitung) und GPU-Arbeit laufen in einer Pipeline überlappend, damit die GPU nie wartet.
6. **Zwischenergebnisse und Caching:** Jede Stufe schreibt ihr Ergebnis als Parquet bzw. Arrow mit Hash aus Eingabe, Modellversion und Konfiguration. Bei einem erneuten Durchlauf werden nur Stufen neu gerechnet, deren Eingaben sich geändert haben. Eine Nutzerkorrektur löst nur die betroffenen nachgelagerten Stufen aus (z.B. Kennzahlen und Erkenntnisse), nie die ganze Pipeline.
7. **Leistungsbudget mit Messung:** Pro Stufe gibt es ein Zeit- und Kostenbudget. Ein Benchmark-Skript `ml/eval/bench.py` misst Laufzeit, GPU-Auslastung und Speicher pro Stufe und läuft vor jedem Meilenstein-Bericht. Ziel: 60 Minuten Video in höchstens 45 Minuten auf einer GPU der L4-Klasse, Kosten pro Spiel unter CHF 2. Abweichungen im Bericht begründen.
8. **Profiling statt Raten:** Engpässe werden mit Profilern (py-spy, Nsight Systems, PyTorch Profiler) gemessen, bevor optimiert wird. Ergebnisse kurz in `docs/perf/` festhalten.

### 6.4 Performance in Backend und Frontend
- **Trackingdaten:** Sie liegen nicht zeilenweise in Postgres, sondern als Parquet auf dem Objektspeicher. Das Frontend lädt sie in Zeitabschnitten (z.B. 30 s) in einem kompakten Binärformat (Arrow IPC oder gepackte Float32-Arrays), nicht als riesiges JSON.
- **Statistiken** kommen aus vorberechneten Aggregaten (Cache-Tabellen pro Spiel und Saison, nach Pipeline-Version invalidiert). Keine Berechnung über Rohereignisse pro Seitenaufruf. Keine N+1-Abfragen: Abfragen werden in Tests mit einem Query-Zähler geprüft.
- **Video** wird nur über HLS mit CDN ausgeliefert. Clips sind Zeitfenster, keine Kopien.
- **Frontend:**
  - Mini-Feld und Taktiktafel-Animation über Canvas bzw. WebGL mit requestAnimationFrame, synchron zur Videozeit
  - Lange Listen virtualisiert
  - Code-Splitting pro Route
  - Diagramme erst rendern, wenn sie sichtbar sind
  - Budgets: LCP unter 2.5 s, Interaktionen unter 200 ms (INP), JS-Bundle der Startseite unter 250 kB gzip, in CI mit Lighthouse geprüft
- **API:** Antwortzeiten p95 unter 300 ms für Lesezugriffe, gemessen mit OpenTelemetry. Lasttest in M9.

### 6.5 Flexibilität und Erweiterbarkeit (verbindlich)
- **Austauschbare Modelle:** Jede ML-Stufe implementiert eine klar definierte Schnittstelle (z.B. `Detector`, `Tracker`, `JerseyReader`, `PoseEstimator`, `EventSpotter`, `GoalZoneEstimator`, `PlayClusterer`). Welche Implementierung läuft, entscheidet eine Konfiguration und die Modell-Registry, nicht der Code. Ein neues Modell einzubauen heisst eine Klasse plus ein Konfigurationseintrag. Heuristik und gelerntes Modell können parallel laufen und verglichen werden (Shadow-Modus).
- **Pipeline als Graph:** Die Stufen sind als gerichteter Graph mit deklarierten Ein- und Ausgaben definiert. Eine neue Stufe, zum Beispiel ein neues Insight oder eine neue Kennzahl, lässt sich einhängen, ohne bestehende Stufen zu ändern.
- **Ports und Adapter:** Externe Dienste (Speicher, GPU-Anbieter, E-Mail, Zahlung, LLM, Official Feed, Video-Import von Veo, Spiideo oder YouTube) laufen über Schnittstellen mit austauschbaren Adaptern. Die Fachlogik kennt keine Anbieter.
- **Konfiguration statt Code:** Schwellwerte, Zonen, Insight-Regeln, Mindeststichproben, Planlimits und Feature-Flags liegen in versionierten Konfigurationsdateien bzw. in der Datenbank, nicht im Code verstreut.
- **Daten versioniert:** Jedes Ergebnis trägt Pipeline- und Modellversion. Alte und neue Ergebnisse können verglichen werden. Reprocessing ist jederzeit möglich.
- **Sportart vorbereiten, nicht bauen:** Spielfeld, Positionen, Ereignis-Taxonomie und Kennzahlen sind als Sport-Definition gekapselt (`packages/court`, `packages/metrics`). V1 enthält nur Handball, aber Handball ist nicht hart im Kern verdrahtet. Ein späterer Ausbau auf Futsal, Basketball oder Unihockey soll ohne Umbau des Kerns möglich sein.
- **Öffentliche API:** Die REST-API ist versioniert (`/v1`) und dokumentiert, damit später Kamera-Partner und Verbände anbinden können. Webhooks für "Analyse fertig".
- **Codequalität:** Typisierung durchgehend (mypy strict für Python, TypeScript strict), keine zirkulären Abhängigkeiten zwischen Modulen (in CI geprüft), Module mit klaren Grenzen. Lieber einfache, gut getestete Lösungen als clevere.

---

## 7. Die automatische Analyse-Pipeline

### 7.1 Grundsätze
- **Vollautomatisch.** Der Nutzer muss nichts markieren. Korrekturen sind möglich, aber nie nötig.
- **Den Ball umgehen.** Die Ballerkennung ist in Handballvideos unzuverlässig: In der Literatur werden etwa 51 % der Bälle richtig erkannt. Ereignisse werden deshalb primär über Körperhaltung, Positionen und Folgesituationen erkannt. Der Ball ist nur ein zusätzliches Signal.
- **Mehrere Quellen zusammenführen.** Hauptvideo, optionale Torkameras, Anzeigetafel (OCR), offizieller Spielverlauf (falls verfügbar), Kader.
- **Jede Aussage hat eine Konfidenz.** Unsichere Ereignisse zählen in Statistiken gewichtet bzw. mit Kennzeichnung. Die UI zeigt "geschätzt", wo die Konfidenz unter dem Schwellwert liegt.
- **Pipeline-Version** an jedem Ergebnis. Ein Reprocessing mit neuer Version ist möglich, Nutzerkorrekturen bleiben dabei erhalten.

### 7.2 Stufen
Jede Stufe hat definierte Ein- und Ausgaben (Parquet oder JSON auf dem Objektspeicher), einen eigenen Test mit einem kurzen Testvideo und eine Metrik.

| # | Stufe | Inhalt | Ausgabe |
|---|---|---|---|
| 0 | **Ingest** | Prüfsumme, ffprobe, Transkodierung zu HLS und einem Analyse-Proxy (z.B. 1280 px, 25 fps), Thumbnails | VideoAsset, Proxy |
| 1 | **Qualitätscheck** | Feld sichtbar (Anteil der Feld-Keypoints), Kamerabewegung (optischer Fluss), Auflösung, Belichtung, Flimmern. Ergebnis `ok`, `warn` oder `fail`, mit konkreten Tipps für den Nutzer. Läuft in den ersten 60 s nach dem Upload auf einer Stichprobe | QualityReport |
| 2 | **Spielfeld-Kalibrierung** | Keypoint-Modell für Handball-Feldlinien (Schnittpunkte, 6-m- und 9-m-Bögen, Mittellinie, Torpfosten). Homographie per RANSAC. Feste Kamera: eine Homographie, über viele Frames robust geschätzt. Bewegte Kamera (Auto-Follow): Homographie pro Frame mit zeitlicher Glättung. Linsenverzerrung bei Weitwinkel schätzen | Calibration |
| 3 | **Detektion** | YOLO (aktuelle Ultralytics-Version, ADR zu Lizenz AGPL vs. Enterprise; Alternative RT-DETR mit Apache-Lizenz) mit Klassen `player`, `goalkeeper`, `referee`, `ball`. Feinjustiert auf Handballdaten | Detections |
| 4 | **Tracking** | BoT-SORT oder ByteTrack mit ReID-Features. Fusspunkt per Homographie auf das Feld projizieren. Tracklets über Feldlogik verbinden: maximal 14 Feldspieler plus 2 Torhüter, Bewegungsgrenzen | Tracks, TrackFrames |
| 5 | **Team-Zuordnung** | Torso-Crops, Farbmerkmale (Lab-Histogramm) oder Embedding, Clustering in Team A, Team B, Torhüter A, Torhüter B und Schiedsrichter. Die Trikotfarben aus dem Match-Setup dienen als Prior. Mehrheitsentscheid pro Track | Track.team |
| 6 | **Spieleridentität** | Rückennummern-Erkennung pro Track: Lesbarkeits-Klassifikator, dann Texterkennung (z.B. PARSeq), dann Abstimmung über alle Frames des Tracks (Ansatz nach Koshkina et al., CVPR-W 2024). Zuordnung zum Kader per ungarischem Algorithmus mit Nebenbedingungen (jede Nummer nur einmal gleichzeitig auf dem Feld). Gegnernummern ohne Kader werden als `Opponent #7` gespeichert | Track.player_id + Konfidenz |
| 7 | **Pose** | RTMPose (rtmlib, Apache-2.0) auf Tracks mit ausreichender Grösse. 2D-Keypoints pro Frame | Pose in TrackFrames |
| 8 | **Ball (best effort)** | Spezialisiertes Kleinobjekt-Modell, z.B. nach dem TrackNet-Prinzip mit mehreren aufeinanderfolgenden Frames, plus Interpolation. Ballbesitz-Wahrscheinlichkeit pro Spieler | BallTrack |
| 9 | **Ereigniserkennung** | Temporales Spotting-Modell pro Spieler und Team, mit Pose-Sequenz, Geschwindigkeit, Feldposition, Abstand zum Tor, Ballwahrscheinlichkeit und Teamformation als Eingaben. Erkennt Wurf (Abwurfzeitpunkt), Pass, Ballverlust, 7 m, Timeout, Anwurf und Wechsel. **Wurf-Heuristik als Baseline:** Ausholbewegung des Wurfarms (Handgelenkgeschwindigkeit über Schwellwert, Arm über Schulterhöhe), Sprung (Hüftbahn), Position in Wurfdistanz, danach Formationswechsel. Das Modell wird später mit Daten trainiert | Events |
| 10 | **Wurfergebnis** | Tor über Anwurf-Erkennung (alle Spieler in der eigenen Hälfte, ein Spieler am Mittelpunkt, binnen 20 s), Anzeigetafel-OCR (falls im Bild), offiziellen Spielverlauf (Abgleich über Zeit und Torschütze) und Torkamera. Parade, Fehlwurf oder Block über Torhüter-Pose, Ballrichtung und Folgebesitz. Abgleich so, dass der Endstand mit allen verfügbaren Quellen übereinstimmt (Constraint-Lösung) | Event.outcome |
| 11 | **Torzone** | Mit Torkamera: Ball- und Netzposition im Torbild, eigenes kleines Modell, sonst Ballposition beim Torlinien-Durchgang. Ohne Torkamera: grobe Schätzung aus der Hauptkamera mit niedriger Konfidenz. In der UI dann als "geschätzt" gekennzeichnet | Event.goal_zone |
| 12 | **Ballbesitz und Phasen** | Ballbesitz-Segmentierung aus Ereignissen und Teamformation (Angreifer in der gegnerischen Hälfte, Abwehrlinie am 6-m-Raum). Phasenklassifikation aus Positionen aller Spieler (Trainingsdaten: Play-by-Play-Datensatz). Situation (Über- und Unterzahl, 7 gegen 6) aus der Spielerzahl pro Team und Torhüter-Präsenz | Possessions, Phases |
| 13 | **Abwehrformation** | Abwehrspieler-Positionen relativ zu 6 m und 9 m, Klassifikation in 6-0, 5-1, 3-2-1, 4-2 usw. pro Positionsangriff | DefenseFormationSegments |
| 14 | **Spielzüge** | siehe Abschnitt 8 | PlayInstances, PlayClusters |
| 15 | **Kennzahlen** | Berechnung aller Metriken (packages/metrics) | Stats-Caches |
| 16 | **Erkenntnisse** | siehe Abschnitt 9 | Insights |
| 17 | **Clips und Benachrichtigung** | Clip-Index pro Ereignis, Besitz und Spielzug. Benachrichtigung an Trainer und Spieler | Clips, Notifications |

### 7.3 Synchronisation mehrerer Kameras
Torkameras werden automatisch zur Hauptkamera synchronisiert: Kreuzkorrelation der Tonspuren (Pfiff, Jubel), zur Kontrolle Abgleich mit erkannten Wurfzeitpunkten. Der Zeitversatz wird in `VideoAsset` gespeichert.

### 7.4 Offizielle Daten
Baue einen Adapter `OfficialMatchFeed` mit einer Schnittstelle für Spielverlauf, Torschützen und Strafen. In v1 gibt es zwei Implementierungen: einen generischen CSV- oder JSON-Import und eine Stub-Implementierung für handball.ch. Ob und wie handball.ch Daten bereitstellt, ist offen (OPEN_QUESTIONS.md). Ohne gesicherte Erlaubnis wird nichts gescrapt.

### 7.5 Aufnahmeregeln (in der UI als Hilfe-Seite und im Qualitätscheck)
- Eine feste Kamera, erhöht (ab 3 m), auf Höhe der Mittellinie, das ganze Feld im Bild
- Mindestens 1080p, ideal 4K. In Hallen mit 50-Hz-Licht 50 oder 100 fps
- Optional eine Torkamera hinter jedem Tor
- Auto-Follow-Kameras (Veo, Spiideo, asport) werden ebenfalls unterstützt, mit Homographie pro Frame

---

## 8. Spielzugerkennung und Taktiktafel

Das ist ein Kernfeature und Alleinstellungsmerkmal. Es verbindet das reale Video mit der Taktiktafel in beide Richtungen.

### 8.1 Vom Video zur Taktiktafel (automatisch)
1. **Segmentierung:** Jeder Positionsangriff (`Phase = set_attack`) wird zu einer Sequenz. Sie beginnt, wenn die Angreifer ihre Grundaufstellung eingenommen haben, und endet mit dem Abschluss (Wurf, Ballverlust, Foul mit Freiwurf, Ende der Phase).
2. **Rollenzuordnung:** Die 6 Feldspieler im Angriff bekommen pro Sequenz Rollen (LA, RL, RM, RR, RA, KM), über ihre Startpositionen und den ungarischen Algorithmus gegen eine Referenzaufstellung. Bei 7 gegen 6 gibt es eine zweite Referenz. Dadurch werden Spielzüge unabhängig davon vergleichbar, welcher Spieler gerade auf welcher Position steht.
3. **Repräsentation:** Rollenbasierte Trajektorien im normierten Feld (Angriffsrichtung x = 40), auf feste Abtastung resampelt. Dazu Ballweg (geschätzt) und Ereignisse (Pässe, Wurf).
4. **Aktionserkennung pro Sequenz** (regelbasiert, mit Tests):
   - Kreuzung: Zwei Rollen tauschen innerhalb von 1.5 s ihre Reihenfolge in y, mit Ballwechsel in der Nähe
   - Einlaufen: Ein Aussen- oder Rückraumspieler bleibt länger als 2 s in der Nähe des 6-m-Raums, es entsteht ein zweiter Kreisläufer
   - Sperre: Der Kreisläufer steht unter 1 m vom Abwehrspieler entfernt, der dem Ballträger am nächsten ist, während der Ballträger in diese Richtung zieht
   - Parallelstoss: Mindestens drei aufeinanderfolgende Pässe in dieselbe Richtung, jeweils mit Stoss Richtung Tor
   - Stoss und Durchbruch, Rückpass, Positionswechsel
5. **Clustering wiederkehrender Spielzüge:** Distanzmass zwischen Sequenzen: Dynamic Time Warping auf den Rollen-Trajektorien, plus Abstand der Aktionsfolge, plus Abschlussposition. Clustering mit HDBSCAN pro Team und Saison, wenn genügend Sequenzen vorliegen (Minimum konfigurierbar). Jeder Cluster bekommt eine Prototyp-Sequenz (Medoid).
6. **Automatische Benennung:** aus der dominanten Aktionsfolge und dem typischen Abschluss, zum Beispiel "Kreuzung RL zu RM, Einlaufen LA, Abschluss Kreis". Der Trainer kann umbenennen ("Spielzug Zürich"). Das Mapping bleibt über Spiele hinweg stabil, neue Sequenzen werden dem bestehenden Cluster zugeordnet.
7. **Taktiktafel-Darstellung:** Für jeden PlayInstance und jeden PlayCluster-Prototyp wird ein `TacticsBoard` mit Keyframes erzeugt: Positionen der 6 Angreifer und 6 Verteidiger, Laufwege als Pfeile, Pässe als gestrichelte Pfeile, Sperren als Balken, Wurf als Pfeil zum Tor. Die Keyframes entstehen durch Vereinfachung der Trajektorien (Ramer-Douglas-Peucker plus Ereigniszeitpunkte).

### 8.2 Von der Taktiktafel zum Video
1. Der Trainer zeichnet in der Taktiktafel einen Spielzug: Startaufstellung, Laufwege, Pässe, Sperren, in mehreren Schritten.
2. Die Zeichnung wird als `PlayTemplate` in dieselbe Repräsentation überführt (Rollen-Trajektorien und Aktionsfolge).
3. Die Plattform sucht in allen Spielen der Saison nach ähnlichen Sequenzen (gleiches Distanzmass, Schwellwert einstellbar) und zeigt die Treffer sortiert nach Ähnlichkeit. Dazu kommen Statistik (wie oft gespielt, Erfolgsquote, gegen welche Abwehrformation) und Clips.
4. Funktioniert ebenso für Gegner: "Wie oft hat der Gegner diesen Spielzug gegen uns gespielt?"

### 8.3 Taktiktafel-Editor (Frontend)
- Handballfeld als SVG im Massstab, ganzes oder halbes Feld, Hoch- und Querformat
- Spieler-Token für Angriff und Abwehr in Teamfarben, mit Nummer oder Position. Ball. Hütchen und Markierungen
- Werkzeuge: Laufweg (Pfeil, geschwungen möglich), Pass (gestrichelt), Sperre, Dribbling (Wellenlinie), Text, Zonenmarkierung
- Mehrere Schritte (Frames) mit Animation zwischen den Frames, Abspielgeschwindigkeit, Pause pro Schritt
- Ansicht "Video und Taktiktafel nebeneinander": Beim Abspielen eines Clips bewegt sich die Taktiktafel synchron zu den echten Trackingdaten. Schalter zwischen "echte Positionen" und "vereinfachter Spielzug"
- Bearbeitbar: Ein automatisch erzeugtes Board kann der Trainer korrigieren und als Template speichern
- Export als PNG, animiertes GIF oder MP4 und PDF. Teilen per Link. Einbinden in Playlists und Trainingsbibliothek
- Touch-tauglich für Tablets am Spielfeldrand
- Datenformat in `packages/tactics` versioniert und dokumentiert

### 8.4 Spielzug-Analysen (UI)
- **Spielzug-Bibliothek des eigenen Teams:** alle Cluster und Templates mit Häufigkeit, Tor- und Wurfquote, xG pro Angriff, Ballverlustquote, Erfolg gegen jede Abwehrformation, Entwicklung über die Saison, beteiligte Spieler, Clips
- **Gegner-Spielzüge:** dieselbe Ansicht für den Gegner aus allen vorhandenen Spielen gegen ihn
- **Matchup-Matrix:** eigene Spielzüge × gegnerische Abwehrformationen, mit Effizienz pro Zelle
- **Abwehr-Analyse:** welche Formation wir spielen, wie oft, Gegentore pro Formation, welche gegnerischen Aktionen (Kreuzung, Einlaufen) uns am meisten wehtun

---

## 9. Erkenntnisse (Insights Engine)

### 9.1 Prinzip
Erkenntnisse entstehen aus **strukturierten Fakten**, die mit festen Regeln und statistischen Prüfungen berechnet werden. Die Sprache erzeugt das LLM erst im letzten Schritt. Jede Erkenntnis hat:
- `type` (aus dem Katalog unten), `scope` (Spiel, Saison, Spieler, Gegner, Spielzug)
- `facts` (JSON mit allen Zahlen, Stichprobengrössen, Vergleichswerten)
- `severity` und `confidence`
- `evidence_clip_ids` (mindestens ein Clip, sonst wird die Erkenntnis nicht angezeigt)
- `text` (generiert) und `text_version`

### 9.2 Qualitätsregeln
- Mindeststichprobe pro Typ (z.B. mindestens 8 Würfe für eine Quote), sonst keine Erkenntnis
- Vergleich gegen die eigene Baseline (Saisonschnitt) bzw. gegen die übrigen Positionen. Die Abweichung muss statistisch plausibel sein (Wilson-Intervall oder Bayes mit Beta-Prior; ADR)
- Ereignisse mit niedriger Konfidenz zählen gewichtet. Bei zu vielen unsicheren Daten wird die Erkenntnis unterdrückt
- Pro Spiel höchstens 3 Top-Erkenntnisse auf der Startseite, priorisiert nach Schwere × Konfidenz × Neuheit
- Nutzer können "hilfreich" oder "stimmt nicht" klicken. Das fliesst in das Ranking ein

### 9.3 Textgenerierung
- Das Prompt bekommt nur `facts` und eine Stilvorgabe: Deutsch (de-CH), kurz, konkret, ein bis zwei Sätze, keine langen Gedankenstriche, keine Übertreibung
- Jede Zahl im Text muss in `facts` vorkommen. Ein Validator prüft das nach der Generierung. Bei einem Verstoss wird neu generiert, danach greift ein Template-Fallback
- Ohne API-Key oder bei Fehlern wird ein deterministisches Template verwendet. Die App funktioniert also auch ohne LLM

### 9.4 Katalog (mindestens umsetzen, erweiterbar)
Team-Angriff:
1. Wurfquote nach Wurfzone, Abweichung zur Baseline
2. Wurfquote nach Position und Spieler
3. Effizienz im Positionsangriff vs. Gegenstoss vs. schnelle Mitte
4. Ballverluste: Häufung nach Typ, Spieler, Phase, Spielminute
5. Gegentore nach eigenem Ballverlust (Gegenstoss-Anfälligkeit)
6. Effizienz in Über- und Unterzahl, 7 gegen 6
7. Torflaute: längste Phase ohne Tor, was davor passiert ist
8. Spielzug mit der besten und schlechtesten Bilanz
9. Spielzug, der gegen eine bestimmte Abwehrformation nicht funktioniert
10. Zu einseitiger Angriff: Würfe fast nur über eine Seite oder Position
11. Kreisanspiele: Anteil und Erfolg
12. xG vs. tatsächliche Tore (Chancenverwertung)

Team-Abwehr:
13. Gegentore nach Zone und gegnerischer Position
14. Gegentore nach gegnerischer Aktion (Kreuzung, Einlaufen, Sperre)
15. Effizienz unserer Abwehrformationen
16. Rückzugsverhalten: Gegentore aus erster und zweiter Welle, Rückzugszeit
17. 2-Minuten-Strafen: Häufung nach Spieler oder Spielphase

Spieler:
18. Persönliche Wurfbilanz und Trend über die Saison
19. Stärken und Schwächen pro Wurfzone und Torzone
20. Ballverluste pro 10 Ballkontakte
21. Laufleistung und Sprintwerte, Abfall in der zweiten Halbzeit
22. Plus-Minus
23. Bester und schlechtester Spielzug für den Spieler

Torhüter (Modul):
24. Paradenquote pro Torzone, Wurfzone, Wurftyp und Werfer
25. Schwache Torzone im Saisonverlauf
26. Paraden in Gegenstoss- und 7-m-Situationen

Spielverlauf:
27. Phasen mit Läufen (z.B. 0:5 in 6 Minuten) und ihre Auslöser
28. Leistungsabfall nach Timeouts, in Schlussphasen, nach Strafen
29. Halbzeitvergleich

Gegner (Vorbereitung):
30. Beste Werfer, ihre Lieblingszonen und Torzonen
31. Häufigste Spielzüge und ihre Erfolgsquote
32. Abwehrformation und ihre Schwachstellen
33. Gegenstoss-Stärke

Saison und Entwicklung:
34. Trends: was sich über die letzten 5 Spiele verbessert oder verschlechtert hat
35. Wiederkehrende Probleme (Problem-Radar): taucht über mehrere Spiele auf
36. Wirkung von Trainingsschwerpunkten: Vergleich vor und nach dem Zuweisen eines Drills zum Thema (nur als Beobachtung, keine Kausalbehauptung)

### 9.5 Von der Erkenntnis zum Training
Jeder Insight-Typ ist mit Tags verknüpft (z.B. `turnover_bad_pass`, `defense_vs_cross`). Die Trainingsbibliothek schlägt passende Drills vor. Der Trainer kann mit einem Klick eine Playlist mit den Beleg-Clips erstellen und als Aufgabe an die betroffenen Spieler schicken.

---

## 10. ML: Daten, Training, Evaluation

### 10.1 Startdaten (Skripte in `/ml/datasets`, Lizenzen dokumentieren)
| Datensatz | Nutzen | Lizenz |
|---|---|---|
| TeamTrack (Handball-Teil), Kaggle oder Google Drive | Detektion, Tracking, Feldkoordinaten | prüfen und in `ml/datasets/LICENSES.md` dokumentieren |
| EIGD-H (data.uni-hannover.de/dataset/eigd) | Ereignisse, Würfe, Pässe, Positionsdaten | CC BY-NC-SA, nur Forschung und Prototyp |
| UNIRI-HBD (IEEE DataPort) | Aktionen: Wurf, Sprungwurf, Pass, Dribbling | Open Access, Lizenz prüfen |
| Roboflow handball-detection (Farahat et al. 2026) | Detektion inkl. Torhüter und Ball | Annotationen CC BY 4.0, Bilder nach EIGD-Bedingungen |
| Play by Play (Zenodo) | Phasenklassifikation aus Positionen | CC BY-NC |
| UWB-Amateur-Frauen (Zenodo 12065335) | Positionsdaten, Ballbesitz, Phasen | CC BY 4.0 |
| Eigene Spiele und Partnervereine | Hauptdatenquelle für Produktion | eigene Einwilligung |

Wichtig: Modelle für die kommerzielle Produktion dürfen nur mit Daten trainiert werden, deren Lizenz das erlaubt. Die Pipeline erfasst pro `ModelVersion`, welche Datensätze verwendet wurden (Data Lineage).

### 10.2 Daten-Schwungrad
- Jede Nutzerkorrektur wird als `Correction` gespeichert und in Trainingsformate exportiert
- Active Learning: Szenen mit niedriger Konfidenz werden für die interne Annotation priorisiert
- Ein internes Annotationstool im Admin-Backoffice dient zur Korrektur von Tracks, Nummern, Ereignissen und Torzonen. Es wird nur intern genutzt, nie vom Kunden verlangt

### 10.3 Golden Set und Metriken
Ein Golden Set aus mindestens 5 vollständig annotierten Spielen (Amateur, verschiedene Hallen und Kameras) liegt auf dem Objektspeicher. Das Repo enthält nur das Manifest. Der Evaluations-Harness `ml/eval/run.py` gibt eine Tabelle pro Stufe aus. Zielwerte für "production ready" (bei Verfehlen wird es im Bericht dokumentiert):

| Stufe | Metrik | Ziel |
|---|---|---|
| Kalibrierung | mittlerer Feldfehler | < 0.5 m |
| Detektion Spieler | mAP50 | ≥ 0.95 |
| Tracking | HOTA | ≥ 0.60 |
| Team-Zuordnung | Genauigkeit pro Track | ≥ 0.97 |
| Spieleridentität | Genauigkeit pro Track (eigenes Team) | ≥ 0.85 |
| Wurferkennung | Recall / Precision (±1 s) | ≥ 0.90 / ≥ 0.85 |
| Wurfergebnis Tor | Genauigkeit | ≥ 0.97 (mit Anwurf + Endstand-Constraint) |
| Torzone mit Torkamera | Genauigkeit 3×3 | ≥ 0.85 |
| Phasen | Makro-F1 | ≥ 0.80 |
| Abwehrformation | Genauigkeit | ≥ 0.80 |
| Spielzug-Cluster | Übereinstimmung mit Trainer-Labels (ARI) | ≥ 0.5 |
| Ende-zu-Ende | Endstand korrekt | 100 %, wenn Spielverlauf oder Anzeigetafel vorhanden |
| Laufzeit | 60 min Video, eine GPU der L4-Klasse | ≤ 45 min |

### 10.4 Modell-Lebenszyklus
- `ModelVersion`-Registry mit Metriken. Neue Modelle werden nur aktiv, wenn sie auf dem Golden Set nicht schlechter sind (Regressionstest in CI über ein kleines Subset, vollständig manuell auslösbar)
- Modellkarten in `ml/models/*.md`
- Reproduzierbares Training über Konfigurationsdateien, Seeds und Daten-Snapshots

---

## 11. Frontend: Screens und Akzeptanzkriterien

Design: ruhig, datenorientiert, viel Weissraum, Vereinsfarben als Akzent, Dark Mode, vollständig responsiv (Laptop, Tablet, Handy). Barrierefreiheit nach WCAG 2.2 AA. Leere Zustände, Ladezustände und Fehlerzustände sind für jeden Screen gestaltet. Diagramme einheitlich mit einer Bibliothek (z.B. visx oder Recharts, ADR).

1. **Onboarding:** Registrierung, Verein anlegen (Name, Logo, Farben), erstes Team, Kader per Formular oder CSV-Import, Spieler einladen. Ziel: in 5 Minuten fertig.
2. **Team-Übersicht (Home):** nächstes Spiel, letzte Resultate mit Formkurve, Top-3-Erkenntnisse der Saison, offene Aufgaben, grosser Upload-Knopf, Status laufender Analysen.
3. **Upload:** Spiel wählen oder anlegen (Gegner, Datum, Trikotfarben), Hauptvideo und optionale Torkameras per Drag-and-drop oder Link, Fortschritt, Live-Qualitätscheck mit konkreten Tipps, danach Fortschritt der Pipeline pro Stufe mit geschätzter Restzeit.
4. **Spiel-Analyse:** Kopf mit Resultat, Halbzeit und Top-3-Erkenntnissen mit Clip. Tabs:
   - Übersicht: Spielverlauf-Chart mit Läufen, Kennzahlen beider Teams im Vergleich
   - Matchreport: digital wie der Papierbogen, pro Spieler Tore, Würfe, Fehlwürfe, Pfosten, Ballverluste nach Typ, Strafen, Assists. Jede Zahl ist klickbar
   - Würfe: Wurfkarte auf dem Feld und Torbild, Filter (Team, Spieler, Phase, Ergebnis, Halbzeit)
   - Spielzüge: erkannte Spielzüge dieses Spiels mit Taktiktafel und Clip
   - Abwehr: Formationen über die Zeit, Gegentore nach Formation und gegnerischer Aktion
   - Spieler: Tabelle mit allen Spielern, Sortierung, Link zum Profil
   - Torhüter: Modul (nur für berechtigte Rollen)
   - Datenqualität: Konfidenz-Übersicht, unsichere Ereignisse, optionale Korrektur
5. **Video-Player:** HLS-Player mit Zeitleiste der Ereignisse (farbig nach Typ), Filter-Panel, Sprung zum nächsten oder vorigen Ereignis, Zeitlupe, Bild für Bild, Mini-Feld mit Live-Positionen aus dem Tracking, Zeichenwerkzeug (Pfeil, Kreis, Linie, Spotlight auf Spieler), Kommentare mit Zeitstempel, "Zu Playlist hinzufügen", Ansicht neben der Taktiktafel. Tastaturkürzel.
6. **Spielerprofil:** Saisonkennzahlen, Trend-Charts, Wurfbild (Feld und Tor), Heatmap, Laufmetriken, persönliche Erkenntnisse, "Meine Clips", Aufgaben. Spieler sehen ihr eigenes Profil, Trainer alle.
7. **Saison-Statistik:** alle Spiele, Trends, Vergleich Heim und Auswärts, Problem-Radar (wiederkehrende Schwächen mit Verlauf), Spieler-Vergleich, Export.
8. **Spielzüge und Taktik:** Spielzug-Bibliothek (Cluster und Templates), Detailseite pro Spielzug (animierte Taktiktafel, Statistik, alle Instanzen als Clips, Erfolg gegen Abwehrformationen), Taktiktafel-Editor, Matchup-Matrix.
9. **Gegner:** Gegnerliste, Gegnerprofil aus allen vorhandenen Spielen (beste Werfer, Wurfbilder, Spielzüge, Abwehr, Gegenstoss), Vorbereitungsbericht als PDF.
10. **Trainingsbibliothek:** Drills (Text, Taktiktafel, Video), Filter nach Thema, Alter und Dauer, vorgeschlagene Drills aus Erkenntnissen, Trainingseinheit zusammenstellen.
11. **Aufgaben:** Trainer weist Clips, Playlists und Drills zu. Spieler sehen ihre Aufgaben und haken sie ab. Trainer sieht den Status.
12. **Torhüter-Modul:** Paradenquote nach Torzone (3×3, umschaltbar Werfer- oder Torhütersicht), nach Wurfzone und Wurftyp, Werfer-Matrix, Gegentor-Clips, Saisonverlauf, Vergleich der Torhüter, Gegner-Werfer-Profile.
13. **Benachrichtigungen:** In-App, E-Mail und Web-Push: Analyse fertig, neue Aufgabe, Kommentar, Erwähnung.
14. **Verein und Einstellungen:** Teams, Personen und Rollen, Datenschutz-Einstellungen (Sichtbarkeit unter Spielern), Abo und Rechnungen, Datenexport, Löschung.
15. **Teilen:** Clip, Playlist, Taktiktafel oder Bericht per Link (Ablaufdatum, optional Passwort), PDF-Export für Spielbericht, Saisonbericht und Gegnervorbereitung.
16. **Betreiber-Backoffice:** Organisationen, Jobs (Status, Logs, Neustart, Reprocessing), Modellversionen, Annotationstool, Support-Ansicht (nur mit Zustimmung des Kunden und mit Audit-Log), Nutzungs- und Kosten-Dashboard.

**Prinzip für alle Screens:** Jede Zahl und jedes Diagrammelement führt mit einem Klick zu den zugehörigen Clips.

---

## 12. Sicherheit, Datenschutz, Recht

- **Datenschutz:** Schweizer DSG und EU-DSGVO. Datenschutzerklärung und AVV-Vorlage (Auftragsverarbeitung) als Platzhalter-Dokumente mit TODO für die rechtliche Prüfung
- **Minderjährige:** Bei Nachwuchsteams ist für jeden Spieler die Einwilligung der Eltern erforderlich. Das System erfasst Einwilligungen pro Spieler (`Consent`) und blendet Spieler ohne Einwilligung in Clips aus, soweit technisch möglich. Andernfalls werden Spieler ohne Einwilligung nicht als Person identifiziert, also keine Namenszuordnung
- **Löschung:** Spieler, Spiel, Team und Organisation sind löschbar, inklusive Videos, Tracks und abgeleiteter Daten. Ein Löschjob mit Nachweis ist dokumentiert. Aufbewahrungsfristen sind konfigurierbar
- **Datenexport:** Export aller Daten einer Organisation (JSON, CSV, Videos)
- **Biometrie:** Es gibt keine Gesichtserkennung. Die Identifikation läuft nur über Rückennummer und Kader. Das ist eine bewusste Entscheidung und wird dokumentiert
- **Technik:** OWASP ASVS Level 2 als Leitlinie, Secrets nur über einen Secret-Manager, verschlüsselte Speicherung, signierte URLs mit kurzer Laufzeit, Mandantentrennung mit Tests, Dependency-Scanning, Content Security Policy, Audit-Log für sensible Aktionen
- **Datenlizenzen:** Trainingsdaten von Kunden nur mit expliziter Zustimmung (Opt-in in den AGB oder separat). Diese Entscheidung kommt in OPEN_QUESTIONS.md

---

## 13. Abos und Abrechnung

| Plan | Inhalt | Preis (Platzhalter, in Config) |
|---|---|---|
| Free | 2 Spiele pro Saison, Spielbericht und Clips | 0 |
| Team | 1 Team, unbegrenzt Spiele (Fair Use), alle Analysen | CHF 39 pro Monat |
| Verein | bis 10 Teams, Vereinsstatistik, Prioritäts-Verarbeitung | CHF 199 pro Monat |
| Torhüter-Add-on | Torhüter-Modul | CHF 7 pro Torhüter und Monat |

- Stripe Checkout und Kundenportal, Webhooks idempotent verarbeiten, Test-Modus lokal
- Feature-Flags pro Plan zentral in einer Datei
- Nutzungslimits (Speicher, Spiele, GPU-Minuten) werden erfasst und in der UI angezeigt
- Testphase 30 Tage für Team und Verein

---

## 14. Meilensteine

Jeder Meilenstein endet mit einem Bericht (Abschnitt 0). Die Akzeptanzkriterien müssen erfüllt sein.

**M0: Fundament (Repo und Plan)**
- Repository-Struktur, Docker Compose, CI, Lint, Typecheck, Pre-commit
- `docs/ARCHITECTURE.md`, erste ADRs (Job-Queue, Hosting-Region, Detektor-Lizenz, Chart-Bibliothek)
- `docs/OPEN_QUESTIONS.md` mit allen offenen Punkten
- Akzeptanz: `docker compose up` startet alle Dienste, `make test` ist grün, eine Health-Seite ist erreichbar

**M1: Konten, Mandanten, Kader**
- Auth, Organisation, Teams, Saisons, Spieler, Rollen, Einladungen, Policy-Test-Matrix
- Onboarding-Flow im Frontend, Kader-CSV-Import
- Akzeptanz: Ein neuer Nutzer legt in unter 5 Minuten Verein, Team und Kader an. Rollentests sind grün

**M2: Spiele, Upload, Video-Player**
- Match-CRUD, Multipart-Upload (fortsetzbar), Ingest, HLS, Qualitätscheck (zunächst heuristisch)
- Video-Player mit Zeitleiste (vorerst ohne Ereignisse), Playlists, Kommentare, Zeichenwerkzeug
- Akzeptanz: 2 GB Video hochladen, Abbruch und Fortsetzen funktionieren, Wiedergabe in Chrome, Safari und auf dem iPhone

**M3: Pipeline-Gerüst und Kalibrierung, Detektion, Tracking**
- Job-Orchestrierung, GPU-Backend-Abstraktion, Stufen 0 bis 5 mit vortrainierten Modellen, Projektion aufs Feld
- Mini-Feld im Player mit Live-Positionen
- Evaluations-Harness mit den ersten Metriken, Benchmark-Skript `bench.py`
- Streaming-Dekodierung, Batching und ONNX/TensorRT von Anfang an, nicht als spätere Optimierung
- Akzeptanz: Ein Testvideo läuft Ende zu Ende durch. Die Positionen sind im Player plausibel. Metriken und Laufzeit pro Stufe stehen im Bericht

**M4: Ereignisse und Spielbericht**
- Pose, Wurf-Heuristik plus Modell-Schnittstelle, Anwurf-Erkennung, Endstand-Constraint, Official-Feed-Adapter (CSV), Anzeigetafel-OCR, Ballbesitz und Phasen (Baseline)
- Kennzahlen-Paket, Spiel-Analyse-Screen (Übersicht, Matchreport, Würfe), alle Zahlen klickbar
- Akzeptanz: Für ein Testspiel stimmen Endstand und die meisten Torschützen. Abweichungen sind dokumentiert

**M5: Identität, Torzonen, Torkameras**
- Rückennummern-Erkennung, Kaderzuordnung, Sync der Torkameras, Torzonen-Modell, Torhüter-Modul
- Akzeptanz: Metriken gegen das Golden Set im Bericht. Die UI zeigt "geschätzt", wo nötig

**M6: Spielzüge und Taktiktafel**
- Rollenzuordnung, Aktionserkennung, Clustering, automatische Benennung, Abwehrformation
- Taktiktafel-Editor, Video und Taktiktafel nebeneinander, Template-Suche, Spielzug-Bibliothek, Matchup-Matrix
- Akzeptanz: Ein gezeichneter Spielzug findet seine Instanzen in den Testspielen. Ein automatisch erkannter Spielzug wird korrekt animiert

**M7: Erkenntnisse, Saison, Gegner, Training**
- Insights Engine mit Katalog, Qualitätsregeln, Textgenerierung samt Validator und Template-Fallback
- Saison-Statistik, Problem-Radar, Gegnerprofil, Trainingsbibliothek, Aufgaben, Benachrichtigungen
- Akzeptanz: Für jedes Testspiel 3 sinnvolle Top-Erkenntnisse mit Beleg-Clips. Keine Zahl im Text ohne Fakt

**M8: Zahlung, Teilen, Export, Backoffice**
- Stripe, Pläne, Limits, Teilen-Links, PDF-Berichte, Betreiber-Backoffice inklusive Annotationstool
- Akzeptanz: Kompletter Kaufprozess im Stripe-Testmodus. PDF-Berichte sehen professionell aus

**M9: Härtung und Go-Live**
- Lasttest (z.B. 50 gleichzeitige Uploads, 20 Analysen parallel), Sicherheitsreview nach Checkliste, Datenschutz-Funktionen (Export, Löschung, Einwilligungen), Monitoring und Alerting, Backups mit Restore-Test, Runbooks in `docs/runbooks/`
- Akzeptanz: Go-Live-Checkliste in `docs/GO_LIVE.md` vollständig abgehakt oder begründet offen

---

## 15. Seed- und Demodaten

- `make seed` erzeugt einen Demo-Verein mit 2 Teams, Kader, 5 Spielen und synthetischen Ereignissen, Tracks und Spielzügen. In der UI ist das als "Demo" gekennzeichnet. So kann das Frontend ohne GPU entwickelt werden.
- **Import realer Papier-Matchreports:** Es existiert bereits ein JSON-Schema für die Papier-Matchreports eines Teams. Pro Spiel gibt es Torschützen, Fehlwürfe, Pfosten, Blocks, technische Fehler nach Typ, Torhüterparaden, Gegentore nach 3×3-Torzone mit Werfernummer, Spielstand alle 5 Minuten und Taktiktafel-Notizen nach Wurfzonen. Baue einen Importer `import_paper_reports`, der diese Dateien (falls in `data/paper_reports/*.json` vorhanden) als Spiele **ohne Video** anlegt, mit `source: "paper_report"`. So nutzt die Saison-Statistik von Anfang an echte historische Daten, und Video-Spiele kommen später dazu. Frag nach den Dateien, wenn sie nicht vorhanden sind. Das Schema liegt dann bei.

---

## 16. Definition of Done (pro Feature)

- Funktion vollständig, inklusive Leer-, Lade- und Fehlerzuständen
- Rechte serverseitig geprüft und getestet
- Unit- und Integrationstests, bei Kernabläufen E2E-Test
- Barrierefreiheit geprüft (axe in Playwright)
- Telemetrie und Logging vorhanden
- Doku aktualisiert (API, ADR wenn nötig, Nutzerhilfe-Text)
- Keine bekannten Sicherheitswarnungen
- Im Bericht des Meilensteins erwähnt

---

## 17. Start

Beginne jetzt mit **M0**:
1. Lies diese Datei vollständig.
2. Schreib `docs/PLAN.md` mit deinem Verständnis, der Architektur, den Risiken und einer Task-Liste pro Meilenstein.
3. Schreib `docs/OPEN_QUESTIONS.md`.
4. Setz das Fundament von M0 um.
5. Halte an, berichte in `docs/progress/M0.md` und warte auf "weiter".
