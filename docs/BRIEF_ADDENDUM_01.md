# Nachtrag 01 zur Bauanleitung: Vollständige Plattform, Marktstandard und Abhebung

> So verwendest du diese Datei: Leg sie als `docs/BRIEF_ADDENDUM_01.md` neben `docs/BRIEF.md` ins Repository und sag Claude Code:
> "Lies docs/BRIEF_ADDENDUM_01.md vollständig. Schliess den laufenden Meilenstein sauber ab, arbeite den Nachtrag dann gemäss Abschnitt 1 in Plan und Meilensteine ein und mach weiter."

---

## 1. Wie du diesen Nachtrag einarbeitest

1. **Laufende Arbeit nicht abbrechen.** Beende den aktuellen Meilenstein inklusive Bericht, bevor du Änderungen aus diesem Nachtrag umsetzt.
2. **Plan aktualisieren.** Ergänze `docs/PLAN.md` mit allen Punkten aus diesem Nachtrag, gemäss der Zuordnung in Abschnitt 9. Schreib ein ADR `docs/adr/NNN-addendum-01.md` mit den Änderungen an Architektur und Datenmodell.
3. **Bereits Gebautes nachziehen.** Wenn ein Punkt einen schon abgeschlossenen Meilenstein betrifft (z.B. Rollen in M1), setzt du ihn als eigenen Task im nächsten Meilenstein um und erwähnst das im Bericht.
4. **Bei Widersprüchen gilt:** dieser Nachtrag vor `BRIEF.md`, die Produktprinzipien (Abschnitt 2) vor allem anderen. Echte Zielkonflikte trägst du in `docs/OPEN_QUESTIONS.md` ein.
5. **Vision-Check in jedem Bericht.** Jeder Meilenstein-Bericht bekommt einen Abschnitt "Vision-Check" mit je einem Satz pro Produktprinzip: eingehalten, verletzt oder nicht betroffen.

---

## 2. Produktprinzipien (Leitplanken für jede Entscheidung)

Diese Prinzipien sind die Vision in Regeln übersetzt. Wenn du unsicher bist, wie du etwas bauen sollst, entscheidest du danach.

| # | Prinzip | Was es konkret heisst |
|---|---|---|
| P1 | **Automatisch zuerst** | Nichts darf manuelle Arbeit voraussetzen. Manuelle Funktionen (Live-Tagging, eigene Tags, Korrekturen) sind immer optional und ergänzen die KI, ersetzen sie nie. |
| P2 | **Jede Zahl führt zum Video** | Jede Kennzahl, jede Erkenntnis, jede Antwort des Assistenten verlinkt auf die zugehörigen Clips. |
| P3 | **Ehrlich statt beeindruckend** | Unsicherheit wird gezeigt. Keine erfundenen Zahlen, keine Kausalbehauptungen, keine stillen Fallbacks. Fehlen Daten, sagt die App das. |
| P4 | **Amateur zuerst** | Handy statt Profikamera, schlechtes Hallen-WLAN, wenig Zeit, kleines Budget, Zahlung per Jahresrechnung, Ehrenamtliche ohne Technikwissen. Alles muss in diesem Umfeld funktionieren. |
| P5 | **Team-Plattform, Torhüter als Modul** | Die Plattform dient dem ganzen Team. Der Torhüter-Bereich ist ein Zusatzmodul. |
| P6 | **Nachwuchs schützen** | Für Minderjährige gelten strengere Standards: keine öffentlichen Rankings, keine öffentlichen Profile ohne Eltern-OK, entwicklungsorientierte Sprache. |
| P7 | **Datenschutz als Standard** | Gegner und Zuschauer haben nichts eingewilligt. Gegner nur mit Nummer, Daten in der Schweiz oder EU, so wenig Personendaten wie nötig. |
| P8 | **Handball-Sprache** | Begriffe so, wie Trainer sie benutzen, je Sprache korrekt (de-CH, fr, en). Keine generischen Sportbegriffe. |
| P9 | **Partner statt alles selbst** | Kamera-Hardware, Livestream, Teamchat und Sensoren werden angebunden, nicht nachgebaut. |
| P10 | **Schnell und günstig** | Analyse in höchstens 45 Minuten, unter CHF 2 Rechenkosten pro Spiel, App reagiert sofort. |

Nicht-Ziele (bewusst nicht bauen):
- ein eigener Livestream-Dienst
- ein eigener Teamchat
- eigene Kamera-Hardware
- Gesichtserkennung
- öffentliche Ranglisten von Spielern
- ein generisches Multi-Sport-Produkt in v1
- manuelles Tagging als Pflicht

---

## 3. Erweiterungen am Datenmodell

Ergänze das Schema (Alembic-Migrationen, Tests, RLS):

- `Federation` (Verband oder Region): Name, Vertrag, Kontingent, Mitglieds-Organisationen, Admins
- `Presentation`, `PresentationSlide` (Typen: `clip`, `tactics_board`, `text`, `stat_card`, `image`). Clip-Folien mit In- und Out-Punkt, Haltepunkten, Zeitlupenabschnitten, Zeichnungen, Spotlight-Spieler
- `Tag`, `TagSet` (pro Team) und `ClipTag`, dazu `SavedFilter` (Smart Playlist)
- `HighlightReel` (Spiel oder Spieler, Format 16:9 oder 9:16, Status, Ausgabe-URI, Einwilligungsstatus)
- `ScoutingReport` (Spiel, Gegner, erzeugt am, Inhalt als strukturierte Fakten, PDF-URI, Datenbasis)
- `PlayerFeedItem` (Spieler, Spiel, Clip, Rang, Grund) und `SelfAssessment` (Spieler, Spiel, Bewertung 1 bis 5, Text, Zeitpunkt)
- `LiveTagSession`, `LiveTag` (Gerätezeit, Taste, Notiz, Zeitversatz zum Video, Konfidenz der Synchronisation)
- `TrainingSession` (Datum, Team, Drills mit Dauer, Notizen), `Attendance` (Spieler, Status, Grund)
- `ConversationThread` und `AssistantMessage` für "Frag deine Daten" (Frage, verwendete Werkzeuge, Antwort, Fakten, Clip-IDs, Kosten, Bewertung)
- `PublicProfile` (Spieler, aktiv, Slug, ausgewählte Inhalte, Einwilligungen)
- `PaperReportUpload` (Foto, Extraktion, Validierungsfehler, Status, bestätigt von)
- `MatchSegment` für mehrere Dateien pro Spiel und mehrere Spiele pro Video (Quelle, Startzeit, Ende, Lücke)
- `MatchFormat` (Spielzeit pro Halbzeit, Anzahl Abschnitte, Feldgrösse, Regeln wie Manndeckung im Nachwuchs)
- `Invoice` mit `payment_method` (`card`, `invoice_qr`), `due_date`, Mahnstufe, Zahlungseingang
- `Consent` erweitert um Zwecke: `analysis`, `highlights_internal`, `highlights_public`, `public_profile`, `training_data`
- Rollen erweitert: `goalkeeper_coach`, `athletic_coach`, `team_manager`, `parent` (nur Lesen der eigenen Kinder), `federation_admin`

---

## 4. P0: Vor dem Launch (Pflicht für "production ready")

Jeder Punkt hat Akzeptanzkriterien. Ein Punkt gilt erst als fertig, wenn alle Kriterien erfüllt und getestet sind.

### 4.1 Präsentationsmodus für die Videositzung
Die wöchentliche Videositzung mit dem Team ist der wichtigste Anwendungsfall für Trainer.
- Präsentation aus Folien bauen: Clips (aus Ereignissen, Spielzügen, Playlists, Suchergebnissen), Taktiktafeln, Textfolien, Statistik-Karten. Per Drag-and-drop sortieren.
- Pro Clip-Folie: In- und Out-Punkt, automatische Haltepunkte mit Zeichnung, Zeitlupenabschnitte, Spotlight auf Spieler, Notizen für den Trainer.
- Vollbild-Präsentation mit Referentenansicht (nächste Folie, Notizen) auf dem Laptop und Beamer.
- Fernbedienung per Handy: QR-Code koppeln, dann Weiter, Zurück, Pause, Zeichnen auf dem Handy, Echtzeit über WebSocket.
- Offline abspielbar: Präsentation als Paket herunterladen (PWA-Cache bzw. Download als ZIP mit MP4 und lokalem Player), weil das Netz in Kabinen oft fehlt.
- Export als MP4 mit eingebrannten Zeichnungen und als PDF (Standbilder plus Notizen).
- Teilen mit Spielern (nur Ansehen), auch als Aufgabe.
- Akzeptanz: Eine Präsentation mit 15 Clips ist in unter 5 Minuten erstellt. Sie läuft offline flüssig auf einem 3 Jahre alten Laptop, und die Handy-Fernbedienung reagiert in unter 300 ms.

### 4.2 Spieler im Video hervorheben (Spotlight)
- Klick auf einen Spieler im Video oder Auswahl aus der Liste: Ring unter den Füssen und Name bzw. Nummer folgen dem Spieler automatisch, berechnet aus den Tracks.
- Im Player wird das clientseitig auf Canvas gezeichnet, im Export (Clip, Präsentation, Highlights) serverseitig eingebrannt.
- Optional abgedunkelte Umgebung, Laufweg der letzten Sekunden als Spur.
- Bei Track-Verlust blendet der Ring weich aus, statt zu springen.
- Akzeptanz: Der Ring sitzt bei sauberem Tracking in mindestens 95 % der Frames auf dem richtigen Spieler (gemessen auf dem Golden Set).

### 4.3 Automatische Highlights
- Pro Spiel ein Team-Reel (Tore, Paraden, Steals, Blocks, schönste Assists) und pro Spieler ein persönliches Reel.
- Die Auswahl ist regelbasiert mit Rangfolge nach Wichtigkeit (Spielstand, Spielphase, xG-Abweichung) und Vielfalt. Es gibt eine Zielmindestlänge und eine Höchstlänge (Standard 60 bis 120 s).
- Formate 16:9 und 9:16 (Hochformat für Social Media). Beim Hochformat schwenkt der Ausschnitt automatisch mit dem Geschehen (Tracks und Ball) mit, geglättet.
- Vorspann mit Vereinslogo, Teams und Resultat, Spieler-Bauchbinde. Keine Musik in v1 wegen der Lizenzen. Eine Schnittstelle für eine lizenzfreie Bibliothek ist vorbereitet.
- Einwilligung beachten: Spieler ohne `highlights_internal` erscheinen nicht. Öffentliches Teilen nur mit `highlights_public` (bei Minderjährigen Eltern-OK).
- Akzeptanz: Reels werden nach der Analyse automatisch erzeugt. Ein Reel enthält kein Ereignis mit Konfidenz unter dem Schwellwert. Das Hochformat zeigt das Geschehen ohne abgeschnittene Hauptakteure in mindestens 90 % der Clips (Stichprobe).

### 4.4 Eigene Tags und Filter
- Teams definieren eigene Tag-Sets (z.B. "Rückzug zu langsam", "gute Abwehrarbeit").
- Tags sind auf Clips, Ereignissen und Spielzügen setzbar. Filter kombinieren automatische und eigene Tags. Filter lassen sich als Smart Playlist speichern.
- Tags erscheinen in Statistik, Suche und Präsentationen.
- Akzeptanz: Eigene Tags verändern keine automatischen Kennzahlen, sie kommen nur dazu.

### 4.5 Mehrwinkel-Player
- Synchroner Player für Hauptkamera und Torkameras: Kamerawahl per Taste, Bild-in-Bild, Nebeneinander.
- Ein Ereignis springt automatisch zur besten Kamera (z.B. Torzone aus der Torkamera).
- Akzeptanz: Der Versatz zwischen den Kameras liegt nach automatischer Synchronisation unter 2 Frames. Der Wechsel geschieht ohne Neuladen.

### 4.6 Automatischer Vorbereitungsbericht
- Wird automatisch 72 Stunden vor einem Spiel erzeugt, sofern Daten zum Gegner vorliegen: frühere Spiele gegen ihn oder vom Team hochgeladene Videos des Gegners. Push-Nachricht an den Trainer.
- Inhalt:
  - Gegner auf einen Blick
  - beste Werfer mit Wurfzonen und Torzonen
  - häufigste Spielzüge mit Erfolgsquote und Taktiktafel
  - Abwehrformation und ihre Schwachstellen
  - Gegenstoss-Stärke
  - Verhalten in Über- und Unterzahl
  - 3 Schlüssel-Clips pro Thema
  - Empfehlungen als Beobachtungen, nicht als Befehle
- Torhüter-Spickzettel: druckbare Werfer-Karte (Nummer, Position, bevorzugte Torzonen), im A6-Format für die Trinkflasche.
- Ohne ausreichende Daten zeigt der Bericht klar, worauf er basiert und was fehlt (P3).
- Export als PDF und als Präsentation (4.1).
- Akzeptanz: Jede Aussage im Bericht hat Stichprobengrösse und Clip-Belege. Der Bericht ist auf einem Handy gut lesbar.

### 4.7 Spieler-Feed "Deine Szenen"
- Nach jeder Analyse bekommt jeder Spieler eine Push-Nachricht und einen persönlichen Feed mit seinen 5 wichtigsten Szenen: positiv und negativ gemischt, Rangfolge nach Beteiligung, Wichtigkeit und Vielfalt.
- Mobile-first, vertikal, eine Szene pro Bildschirm, Spotlight automatisch aktiv.
- Selbsteinschätzung zuerst: Der Spieler bewertet sein Spiel (1 bis 5) und schreibt optional einen Satz. Erst danach sieht er den Kommentar des Trainers.
- Der Trainer kann pro Szene kommentieren und Szenen tauschen.
- Im Nachwuchs ist die Sprache entwicklungsorientiert, und es wird mindestens eine positive Szene garantiert.
- Akzeptanz: Der Feed ist 5 Minuten nach Ende der Analyse da. Die Selbsteinschätzungen sind für den Trainer als Übersicht sichtbar.

### 4.8 Sonderfälle aus dem Vereinsalltag
- **Mehrere Dateien pro Spiel:** automatisch in Reihenfolge bringen (Metadaten-Zeit und Inhalt), Lücken erkennen und anzeigen, Analyse über die Lücke hinweg.
- **Mehrere Spiele in einem Video** (Turniere): Spielgrenzen erkennen (leeres Feld, Anwurf bei 0:0, lange Pause) und als Vorschlag zum Aufteilen anzeigen.
- **Seitenwechsel** automatisch erkennen (Team-Schwerpunkte, Torhüterwechsel der Seite), Normalisierung der Angriffsrichtung entsprechend.
- **Spielformate:** `MatchFormat` mit Vorlagen (Erwachsene 2 × 30, Nachwuchs 2 × 25 und 2 × 20, Minihandball, Turnier mit kurzen Spielen). Die Spieluhr wird aus Anwurf, Pfiffen und Unterbrechungen geschätzt und mit dem Format abgeglichen.
- **Ähnliche Trikotfarben und Leibchen:** Warnung beim Anlegen des Spiels mit Farbvergleich. Teamzuordnung mit zusätzlichen Signalen (Position, Bewegungsrichtung, Rückennummern) statt nur Farbe. Ehrliche Konfidenz.
- **Trainingsvideos:** Spieltyp `training` ohne Gegner, Analyse von Spielformen (z.B. 6 gegen 6), Ergebnisse getrennt von der Spielstatistik.
- **Schlechtes WLAN:** Upload später fortsetzen, Hintergrund-Upload in der App, optionale Komprimierung auf dem Gerät, Warnung bei mobilen Daten.
- Akzeptanz: Für jeden Sonderfall gibt es ein Testvideo bzw. einen Testfall in der Pipeline-Testsuite.

### 4.9 Gegner und Nachwuchs schützen
- Gegnerische Spieler werden standardmässig nur mit Nummer geführt. Namen nur, wenn der Trainer sie aus einer öffentlichen Quelle einträgt. Sie werden nie öffentlich gezeigt und nie in Highlights benannt.
- Nachwuchsteams: öffentliche Profile und öffentliches Teilen sind aus, es gibt keine Rankings zwischen Spielern, Erkenntnisse sind entwicklungsorientiert formuliert, Eltern-Einwilligung pro Zweck.
- Eltern-Rolle: sieht nur Inhalte des eigenen Kindes, verwaltet die Einwilligungen.
- Akzeptanz: Policy-Tests decken alle Regeln ab. Ein Datenschutz-Review steht im Bericht.

### 4.10 Abrechnung für Vereine
- Monatsabo per Karte und **Jahresabo per Rechnung** mit Schweizer QR-Rechnung (z.B. Python-Bibliothek `qrbill`), Zahlungsfrist 30 Tage, Erinnerung und Mahnung, Zahlungseingang im Backoffice markieren und optional per Bankdatei (camt.054) abgleichen.
- MWST Schweiz (aktueller Satz konfigurierbar), EU-Umsatzsteuer über Stripe Tax oder eine eigene Regel. Vereine sind oft nicht mehrwertsteuerpflichtig, steuerlich also wie Privatkunden. Die steuerliche Prüfung kommt in OPEN_QUESTIONS.
- Rechnungen mit Vereinsadresse, Rechnungsempfänger (Kassier), PDF-Archiv.
- Verbands- und Mengenrabatte über Gutscheine und Verträge im Backoffice.
- Akzeptanz: Ein Jahresabo per QR-Rechnung lässt sich von der Bestellung bis zum Zahlungseingang durchspielen. Rechnungen sind formal korrekt (Pflichtangaben CH).

### 4.11 Support, Hilfe und Onboarding
- **Hilfecenter** im Marketing-Bereich: Anleitungen (Aufnahme, Upload, Präsentation, Rechte), kurze Videos, durchsuchbar, de, fr, en, als MDX im Repo.
- **Hilfe in der App:** kontextbezogene Hilfe-Links pro Screen, Support-Chat über einen Adapter (z.B. Crisp oder Intercom, ADR), Feedback-Knopf mit automatischem Kontext (Seite, Spiel, Browser, optional Screenshot).
- **Onboarding:** geführte erste Schritte mit Checkliste, Demo-Spiel zum Ausprobieren und E-Mail-Serie an Tag 0, 1, 3, 7 und 14 mit Abmeldung.
- **Fehlgeschlagene Analysen:** verständliche Meldung, was passiert ist und was der Nutzer tun kann. Teilergebnis statt nichts. Automatische Gutschrift des Spiels im Kontingent.
- Akzeptanz: Ein Testnutzer ohne Vorwissen schafft Anmeldung bis erster Analyse ohne Support. Das wird mit 3 Personen getestet, die Ergebnisse stehen im Bericht.

### 4.12 Betrieb und Messung
- **Produktanalyse:** PostHog (selbst gehostet oder EU-Cloud), nur mit Einwilligung (Cookie-Banner), mit Kern-Events wie Registrierung, erster Upload, erste Analyse gesehen, Präsentation gehalten und Spieler aktiv. Dazu ein Dashboard für Aktivierung und Bindung.
- **Statusseite** über einen externen Dienst (Adapter), automatisch gespeist aus Health-Checks.
- **Alarme:** bei Fehlerrate, Warteschlangenlänge, Analysedauer und Kosten pro Spiel über dem Budget.
- **Qualitätsmonitoring der KI:** Konfidenzverteilungen und Korrekturquote pro Woche. Ein Alarm geht los, wenn die Qualität bei neuen Kundenvideos abfällt.
- **Penetrationstest:** Claude Code bereitet Scope, Testkonten und Checkliste in `docs/security/pentest-scope.md` vor. Durchgeführt wird er extern.
- **Speicherpolitik:** Rohvideo nach konfigurierbarer Frist (Standard 90 Tage) auf die komprimierte Version reduzieren, mit vorheriger Info an den Kunden.

### 4.13 Marketing-Website
- `apps/site` (Next.js, statisch generiert) mit diesen Seiten: Start, Funktionen, Preise (aus derselben Konfiguration wie die App), interaktive Beispielanalyse (Demo-Spiel, nur lesen), Aufnahmeanleitung, Hilfecenter, Blog, Kontakt, Rechtliches (AGB, Datenschutz, Impressum).
- SEO (Metadaten, Sitemap, strukturierte Daten), drei Sprachen, Performance-Budget wie in der App.
- Testphase direkt startbar.
- Akzeptanz: Lighthouse über 90 in allen Kategorien. Die Beispielanalyse funktioniert ohne Login.

---

## 5. P1: Erste Saison nach dem Launch

### 5.1 Frag deine Daten (Assistent)
- Chat-Fenster in der App: Fragen in normaler Sprache, zum Beispiel "Wie oft treffen wir nach einem Timeout?", "Zeig alle Gegentore über Rechtsaussen in den letzten 5 Spielen" oder "Welcher Spielzug funktioniert gegen 5-1?".
- **Architektur:** Claude API mit Tool Use. Die Werkzeuge sind typisierte, vordefinierte Abfragen über die Kennzahl- und Ereignis-Schicht, etwa `query_events`, `aggregate_metric`, `compare_periods`, `find_plays`, `get_clips` und `list_insights`. Es gibt **kein freies SQL**. Jedes Werkzeug prüft die Rechte des Nutzers.
- Die Antwort enthält Zahl, Stichprobengrösse, kurzen Text, Clips und bei Bedarf ein kleines Diagramm. Jede Zahl im Text muss aus einem Werkzeugergebnis stammen, das prüft ein Validator (wie in BRIEF 9.3).
- Ist eine Frage nicht beantwortbar, sagt der Assistent das und schlägt eine beantwortbare Frage vor.
- Kostenlimit pro Organisation und Monat. Alle Gespräche werden mit Werkzeugaufrufen protokolliert, für Qualität und Support.
- **Evaluation:** Testset mit mindestens 60 Fragen und erwarteten Antworten auf dem Demo- und dem Golden-Datensatz, in CI als Regressionstest.
- Akzeptanz: mindestens 90 % korrekte Antworten im Testset, keine erfundene Zahl, Antwortzeit unter 8 s.

### 5.2 Handy als Kamera
- In der nativen App (5.5): Aufnahmemodus mit Live-Hilfe.
- Overlay der Feldlinien, Neigungs- und Lagehilfe über die Gerätesensoren, Live-Prüfung, ob das ganze Feld im Bild ist (Modell auf dem Gerät oder Stichprobe an den Server).
- Aufnahme mit 1080p und 50 fps, Speicher- und Akkuprüfung vor dem Start, Sperrbildschirm-Schutz.
- Automatischer Upload in Abschnitten im Hintergrund, bevorzugt im WLAN, fortsetzbar.
- Mehrere Handys (z.B. Hauptkamera plus Torkamera) werden in der App einem Spiel zugeordnet.
- Akzeptanz: Eine Aufnahme von 70 Minuten auf einem Mittelklasse-Handy ist ohne Abbruch möglich. Der Upload setzt nach einem Verbindungsabbruch automatisch fort.

### 5.3 Live-Tagging am Spielfeldrand (optional)
- Tablet- und Handy-Ansicht mit 4 bis 8 grossen, frei belegbaren Tasten, offline-fähig, mit Gerätezeit.
- Nach dem Upload werden die Markierungen **automatisch** mit dem Video synchronisiert: Abgleich der Gerätezeit mit der Video-Metadatenzeit, verfeinert über erkannte Ereignisse wie Anwurf und Tore.
- Die Markierungen erscheinen als eigene Spur "Trainer" in der Zeitleiste und als Liste "Markiert während des Spiels".
- Halbzeit-Ansicht: alle Markierungen der ersten Halbzeit als Liste, mit Clip, sobald Videoabschnitte hochgeladen sind.
- Akzeptanz: Die Synchronisation ist nach dem Abgleich in 90 % der Fälle auf 2 s genau. Ohne Live-Tagging fehlt nichts (P1).

### 5.4 Statistik-Matrix, Import und Export
- **Pivot-Baukasten:** Zeilen (Spieler, Positionen, Spielzüge, Spiele, Phasen), Spalten (Kennzahlen), Filter. Als Vorlage speicherbar, jede Zelle führt zu Clips (P2).
- **Export:** Sportscode-kompatibles XML (Instanzen mit Code, Start, Ende, Labels), CSV der Ereignisse und Kennzahlen, Excel.
- **Import:** Sportscode-XML als eigene Tags, CSV von Spielverläufen, Video-Import per Link aus Veo, Spiideo, Hudl und asport (Adapter, API wo verfügbar, sonst Datei).
- Akzeptanz: Ein XML-Export lässt sich in Sportscode öffnen. Der Rundlauf Export und Re-Import ist verlustfrei getestet.

### 5.5 Native Apps
- Expo (React Native) für iOS und Android, gemeinsamer API-Client und gemeinsame Logik mit dem Web.
- Inhalt: Spieler-Feed, Clips, Aufgaben, Benachrichtigungen, Präsentations-Fernbedienung, Aufnahmemodus (5.2), Live-Tagging (5.3), Anwesenheit (5.7).
- Push über APNs und FCM, Deep Links in Clips, Offline-Cache für zugewiesene Clips.
- Store-Einträge vorbereitet: Texte, Screenshots, Datenschutz-Angaben.
- Akzeptanz: Die Apps bestehen die Review-Richtlinien (Checkliste). Kaltstart unter 2 s auf einem Mittelklassegerät.

### 5.6 Vom Problem zum Training
- Jede Erkenntnis hat Themen-Tags, die Trainingsbibliothek schlägt passende Drills vor.
- Mit einem Klick: Trainingseinheit planen (5.7), Beleg-Clips als Playlist, Aufgabe an betroffene Spieler.
- **Wirkung beobachten:** Die betroffene Kennzahl wird über die nächsten Spiele verfolgt und als "vorher und nachher" gezeigt, klar als Beobachtung gekennzeichnet, nicht als Beweis (P3).
- Akzeptanz: Der ganze Kreislauf ist mit Demodaten durchspielbar.

### 5.7 Schlanke Trainingsplanung
- Trainingseinheit aus Drills zusammenstellen (Dauer, Reihenfolge, Notizen), als PDF für die Halle.
- Anwesenheit pro Einheit und Spiel, auch per App durch die Spieler (Zu- und Absage).
- Kalender-Feed (ICS) zum Abonnieren.
- Adapter-Schnittstelle für Spond und ClubCorner, um Termine und Anwesenheit zu übernehmen statt doppelt zu pflegen (P9). Implementierung je nach verfügbarer API, sonst ICS und CSV.

### 5.8 Öffentliches Spielerprofil
- Opt-in für erwachsene Spieler, für Minderjährige nur mit Eltern-Einwilligung (P6).
- Inhalte: ausgewählte Highlights, Position, Wurfhand, Saisonkennzahlen nach Wahl, Kurzbeschreibung.
- Teilbarer Link, Sichtbarkeit jederzeit widerrufbar, keine Indexierung durch Suchmaschinen als Standard.

### 5.9 Papierbogen und Taktiktafel fotografieren
- Foto des Matchreports oder der Taktiktafel hochladen. Claude (Vision) extrahiert die Daten ins Papierbogen-Schema aus BRIEF Abschnitt 15.
- Validierung: Summen gegen Totale, Endstand gegen Spielverlauf. Unsicheres wird markiert.
- Prüfansicht mit Foto neben den Daten. Hier ist eine Bestätigung durch den Nutzer sinnvoll und erlaubt, weil die Funktion optional ist und Handschrift unsicher.
- Die Spiele erscheinen in der Saisonstatistik mit Quelle "Papier".
- Akzeptanz: Auf einem Testset von 10 echten Bögen sind mindestens 95 % der Zahlenfelder korrekt.

### 5.10 Verbands- und Mengenlizenzen
- `Federation` mit Kontingent, Einladung von Vereinen, gemeinsame Abrechnung.
- Verbands-Übersicht: Nutzung pro Verein und anonymisierte, aggregierte Kennzahlen. Keine Einsicht in Vereinsvideos ohne Freigabe des Vereins.

---

## 6. P2: Nach der ersten Saison (jetzt nur Architektur vorbereiten)

Für diese Punkte baust du jetzt nur die nötigen Schnittstellen und Datenstrukturen, damit später kein Umbau nötig ist. Umgesetzt werden sie nach M11.

- **Halbzeit-Bericht:** Upload in Abschnitten während des Spiels (Handy-App oder Kamera-Partner), Analyse der ersten Halbzeit in unter 10 Minuten, kompakter Bericht mit 5 Clips. Vorbereiten: Pipeline-Lauf auf Teil-Videos, priorisierte Warteschlange.
- **Vereins-Spielidee:** gemeinsames Playbook und Begriffe für alle Teams eines Vereins, Spielerentwicklung über mehrere Saisons und Teams. Vorbereiten: Playbook auf Organisationsebene, Player-Historie über Teams.
- **Anonymer Vergleich mit ähnlichen Teams:** Benchmarks pro Liga und Stufe, nur mit genügend Teams (k-Anonymität, Minimum 10 Teams). Vorbereiten: Liga- und Stufen-Zuordnung, Aggregations-Job.
- **Belastung, Tests, Abwesenheiten:** Fragebogen nach dem Training (Belastung 1 bis 10), Testresultate, Verletzungsabwesenheit ohne Diagnosen (Gesundheitsdaten minimieren).
- **Torhüter-Antizipationstrainer:** separates Projekt. Vorbereiten: Export-API für Wurf-Clips aus Torkameras mit Metadaten (Werfer, Position, Torzone, Abwurfzeitpunkt).
- **Videoaustausch in einer Liga:** Vereine tauschen Spielvideos gegenseitig, nur mit Zustimmung beider Vereine und klaren Nutzungsregeln. Vorbereiten: Freigabe-Modell zwischen Organisationen.

---

## 7. Partner-Anbindungen (Adapter statt Eigenbau)

Lege für jede Kategorie eine Schnittstelle in `apps/api/integrations/` an, mit Stub-Implementierung, Tests und Doku. Konkrete Anbindungen folgen, sobald Partnerschaften stehen.

| Kategorie | Schnittstelle | Erste Implementierung |
|---|---|---|
| Video-Quellen | `VideoSourceAdapter` (Liste, Metadaten, Download, Webhook) | Datei-Link und YouTube nur für eigene oder freigegebene Videos (ohne Umgehung von Nutzungsbedingungen), Stubs für Veo, Spiideo, asport, Hudl |
| Livestream | `StreamPartnerAdapter` (Spiel zuordnen, Aufzeichnung abholen) | Stub |
| Kalender und Team | `TeamOpsAdapter` (Termine, Anwesenheit) | ICS-Import und Export, Stubs für Spond und ClubCorner |
| Offizielle Daten | `OfficialMatchFeed` (aus BRIEF 7.4) | CSV und JSON, Stub für handball.ch |
| Sensoren | `WearableAdapter` (Positions-, Puls-, Belastungsdaten) | CSV-Import, Stubs für Kinexon und Polar |
| Support | `SupportChatAdapter` | Crisp oder Intercom (ADR) |
| Status | `StatusPageAdapter` | externer Anbieter (ADR) |

---

## 8. Ergänzungen zu Recht und Datenschutz

- Einwilligungen pro Zweck (Abschnitt 3), mit Verlauf und Widerruf, Eltern-Einwilligung für Minderjährige.
- AGB-Abschnitt zur Videonutzung: Der Verein bestätigt, dass er die Aufnahme machen darf (Hallenordnung, Information der Gegner). Hinweisvorlage für die Halle ("Dieses Spiel wird zu Analysezwecken gefilmt").
- Nutzung von Kundendaten für Training der Modelle nur mit Opt-in (`training_data`), standardmässig aus. Bei Nachwuchsteams ohne Eltern-OK nie.
- Datenmitnahme bei Vereinswechsel: Ein Spieler kann sein Profil und seine Statistik exportieren, Videos bleiben beim Verein.
- Alles Rechtliche als Vorlage mit klarer Markierung "rechtlich prüfen lassen", Liste in OPEN_QUESTIONS.

---

## 9. Neue Zuordnung zu den Meilensteinen

Die Meilensteine aus BRIEF bleiben. Die Punkte werden so ergänzt:

| Meilenstein | Ergänzungen aus diesem Nachtrag |
|---|---|
| M1 Konten, Mandanten, Kader | neue Rollen inkl. Eltern, Admin-Übergabe, Spielgemeinschaften und Spieler in mehreren Teams, Nachwuchs-Standards (4.9), Einwilligungen pro Zweck, `Federation` als Struktur |
| M2 Spiele, Upload, Player | mehrere Dateien pro Spiel und Lücken, Spielformate, Upload bei schlechtem WLAN, eigene Tags und Smart Playlists (4.4) |
| M3 Kalibrierung, Detektion, Tracking | Spotlight (4.2), Seitenwechsel, ähnliche Trikotfarben, mehrere Spiele pro Video erkennen, Trainingsvideos (4.8) |
| M4 Ereignisse und Spielbericht | automatische Highlights (4.3), Spieluhr aus Format und Ereignissen |
| M5 Identität, Torzonen, Torkameras | Mehrwinkel-Player (4.5), Gegner nur mit Nummer |
| M6 Spielzüge und Taktiktafel | keine Änderung, aber Taktiktafeln als Präsentationsfolien nutzbar |
| M7 Erkenntnisse, Saison, Gegner, Training | Präsentationsmodus (4.1), Vorbereitungsbericht (4.6), Spieler-Feed mit Selbsteinschätzung (4.7) |
| M8 Zahlung, Teilen, Export, Backoffice | Jahresabo mit QR-Rechnung und MWST (4.10), Hilfecenter, Support, Feedback, Onboarding (4.11), Produktanalyse und Statusseite (4.12), Marketing-Website (4.13) |
| M9 Härtung und Go-Live | Pentest-Vorbereitung, Speicherpolitik, KI-Qualitätsmonitoring, Usability-Test mit 3 Personen, Partner-Adapter als Stubs (7), P2-Vorbereitungen (6) |
| **Launch** | nach M9 |
| **M10 Daten und Training** (neu) | Frag deine Daten (5.1), Statistik-Matrix, Import und Export (5.4), vom Problem zum Training (5.6), Trainingsplanung (5.7) |
| **M11 Mobile und Wachstum** (neu) | Native Apps (5.5), Handy als Kamera (5.2), Live-Tagging (5.3), öffentliches Spielerprofil (5.8), Papierbogen-Digitalisierung (5.9), Verbandslizenzen (5.10) |
| **M12+** (neu) | P2-Punkte nach Priorisierung durch den Product Owner |

---

## 10. Ergänzte Go-Live-Kriterien

Zusätzlich zu `docs/GO_LIVE.md` aus BRIEF:

- [ ] Alle P0-Punkte (Abschnitt 4) erfüllen ihre Akzeptanzkriterien
- [ ] Vision-Check: kein Produktprinzip verletzt, sonst begründet und vom Product Owner freigegeben
- [ ] Ende-zu-Ende-Test mit 3 echten Amateurspielen aus unterschiedlichen Hallen, Ergebnisse im Bericht
- [ ] Usability-Test mit 3 Trainern ohne Vorwissen bestanden
- [ ] Kaufprozess für Monatsabo per Karte und Jahresabo per QR-Rechnung durchgespielt
- [ ] Hilfecenter mit mindestens 15 Artikeln in Deutsch, Übersetzungen fr und en vorhanden
- [ ] Statusseite, Alarme und Backups mit Restore-Test aktiv
- [ ] Pentest-Scope fertig, externer Test beauftragt oder durchgeführt
- [ ] Rechtliche Vorlagen zur Prüfung übergeben (in OPEN_QUESTIONS dokumentiert)
- [ ] Analysedauer und Kosten pro Spiel im Budget (P10), Messung im Bericht

---

## 11. Start

1. Schliess den laufenden Meilenstein ab.
2. Lies diesen Nachtrag vollständig, aktualisiere `docs/PLAN.md`, `docs/OPEN_QUESTIONS.md` und schreib das ADR zum Nachtrag.
3. Schreib einen kurzen Bericht `docs/progress/addendum-01-plan.md`: Welche Punkte landen in welchem Meilenstein, was ändert sich an bereits Gebautem, welche Risiken siehst du?
4. Halte an und warte auf "weiter".
