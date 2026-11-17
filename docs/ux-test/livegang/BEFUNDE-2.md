# Livegang: Befunde, zweite Runde

Ab 2026-11-17, nach dem Umbau der ersten Runde (`BEFUNDE.md`, Prüfbericht `QA-NACHT.md`).
Wie in der ersten Runde: **erst sammeln, dann in einem Rutsch umsetzen** (Wunsch von Lukas).
Quelle: K = Lukas beim Probieren, Q = Claude beim Prüfen.

Schwere: 🔴 blockiert einen Trainer · 🟡 stört · ⚪ Kleinigkeit.

## Von Lukas

| # | Befund | Wo | Stand |
|---|---|---|---|

## Noch offen aus der ersten Runde

| # | Punkt | Wo | Stand |
|---|---|---|---|
| Q1 | Szene als Videodatei teilen und «Das Spiel in 60 Sekunden» (K20): braucht die Analyse-Pipeline | Teilen | offen, gehört zur Analyse-Arbeit |
| Q2 | Szenentitel in Sammlungen lauten «Gegentor über aussen rechts» (Text aus `zoneFrom`), glätten | Sammlungen | offen ⚪ |
| Q3 | Chat-Vorschauen (WhatsApp, Signal, iMessage) auf einem echten Handy prüfen | Teilen | offen, Test durch Lukas |
| Q4 | Spieltag offline: Neuladen ohne Netz lokal unter `next dev` nicht bestätigt, in der echten App prüfen | Spieltag | offen, prüfen |
| Q5 | Login und Hauptflüsse in Produktion mit echtem Konto durchgehen (Claude hat kein Konto, nur öffentliche Seiten geprüft) | App | offen, Test durch Lukas |
| Q6 | «Gegner beobachten» (K3): wie gut es ist, hängt an der Analyse | Upload, Gegner | offen, nach dem Analyse-Fix prüfen |

## Entscheide und Aufgaben für Lukas

| # | Punkt | Stand |
|---|---|---|
| E1 | GPU-Kontingent bei Azure beantragen (Serverless T4, Switzerland North), siehe `docs/plans/gpu-analyse.md` | offen |
| E2 | Mail-Anbieter (Empfehlung Azure Communication Services), danach `HB_MAIL_ENABLED=true` | offen |
| E3 | Cloudflare: «Builds for non-production branches» ausschalten (sonst roter Check auf jedem neuen Zweig) | offen |
| E4 | CUDA-Image des gpu-workers in der CI bauen (Vorschlag der Hauptsitzung) | offen, Entscheid |
| E5 | Neue Staging-Variablen für Ballnetz und Wiedererkennung (`HB_BALL_MODEL`, `HB_REID_MODEL` mit SHA256) beim nächsten Deploy setzen | offen, Okay von Lukas |
| E6 | Aufräumen: alte Zweige, Testkonto `e2e-entry…`, DNS `test.` und `asuid.test` (Löschen war für Claude gesperrt) | offen |
| E7 | Optional: Partnerschaft J+S und SHV für die Übungsbibliothek anfragen (`docs/research/R1-uebungsbibliothek.md`) | offen |

## Betrieb

| # | Punkt | Stand |
|---|---|---|
| B1 | App-Feinschliff (#57) gemergt, Deploy wartet auf den laufenden Analyse-Lauf (zweite Halbzeit, vom Watchdog um 05:00 UTC neu gestartet) | wartet |
| B2 | Erste Halbzeit von Lukas' Spiel nach dem Lauf mit «Analyse neu starten» anstossen | offen |
