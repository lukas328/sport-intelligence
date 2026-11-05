# Backlog und Prioritäten (Backend und Analyse)

Stand 2026-11-05. Ziel des Produkts: Video hochladen, automatisch die Schlüsselsituationen
(Tore, Würfe, wer den Ball hat, wohin der Wurf geht, Spielzüge) und pro Spieler auswerten. Die UI
macht eine eigene Sitzung (`docs/plans/ui-match-workspace.md`).

## Läuft gerade
| Thema | Stand |
|---|---|
| Würfe als Vorschläge (wie Torkandidaten) | Messung und Einbau laufen |
| Mannschaft aus handball.ch übernehmen (Phase 1 bis 3) | Backend fertig (64bade8, fab3011), UI-Sitzung baut die Screens |
| 1. Kalibrierung für Stream-Kameras | läuft (messen, dann verbessern, Klick-Kalibrierung pro Halle) |
| 6. Spielberichte per Link aus nuLiga (DE, AT) und HLA-PDF | läuft |
| Backend-Prüfung auf Fehler bei echtem Material (Teil-Videos, ganze Spiele, Rechte) | läuft, erste Fixes gepusht |
| Torkandidaten im Produktpfad messen | läuft |
| Uploads von Lukas verarbeiten, schneller machen | läuft |
| Ball Runde 5 / 5b (OWLv2-Labels) | Kaggle, Auswertung danach |

## Als Nächstes (Reihenfolge)
1. **Kalibrierung für Stream-Kameras.** Auf allen vier geprüften Wädenswil/Horgen-Clips scheiterte
   die automatische Spielfeld-Erkennung (flache Sicht). Ohne Spielfeld keine Positionen, kein
   Ballbesitz pro Team, kein Bank-Filter, schlechtere Nummern. Erst messen, wie oft das auf allen
   hochgeladenen Spielen passiert, dann verbessern oder die Klick-Kalibrierung pro Halle einmal
   machen und für alle Spiele dieser Halle wiederverwenden.
2. **Ein ganzes Spiel end-to-end.** Ein 60-Minuten-Spiel echt durch Upload, Analyse, Torkandidaten,
   Würfe, Nummern und offiziellen Bericht laufen lassen: Dauer, Speicher, Fehler. Dazu die Frage,
   wo die Analyse im Betrieb rechnet (GPU-Worker: Kosten pro Spiel).
3. **Wohin der Wurf geht.** Beim Bestätigen eines Tors oder Wurfs die Torzone mit einem Klick
   erfassen (Raster 3x3), Wurfposition auf dem Feld aus den Spuren; Auswertung pro Spieler und
   Torhüter. Automatische Torzone erst, wenn der Ball gut genug ist.
4. **Ball Runde 6** mit OWLv2-Labels aus den neuen Spielen (Modal über die lokale Sitzung), danach
   "Wer hat den Ball" pro Spieler neu trainieren.
5. **Rückennummern breit messen** auf den neuen Spielen mit Matchblatt (ab 2023/24), Schwellen
   einstellen; Spieler-Statistik aus bestätigten Ereignissen prüfen.
6. **Spielberichte per Link aus nuLiga (DE, AT) und HLA-PDF (AT)** importieren, ohne Vertrag
   (`docs/plans/data-sources-de.md`).
7. **Spielzüge.** Angriffe gibt es schon als Phasen; erkennen, welche Auslösung gespielt wurde
   (Muster in den Spuren), Verknüpfung mit dem Taktikboard. Braucht 1 und 4.

## Reihenfolge der Starts
2 (ganzes Spiel) sobald die Upload-Verarbeitung fertig ist; 3 (Torzone) nach den Würfen;
4 (Ball Runde 6) nach der Auswertung von Runde 5 als Auftrag in `ml/gpu/JOBS.md`; 5 (Nummern) wenn
genug hochgeladene Spiele mit Matchblatt verarbeitet sind; 7 (Spielzüge) nach 1 und 4.
Kleine Lücke aus dem Onboarding: Namen offizieller Kader-Einträge ohne Einwilligung auch in
Ereignis- und Statistik-Ansichten verbergen (mit 5).

## Entscheide von Lukas (offen)
- Zählen übernommene offizielle Spiele zur Spiel-Limite des Gratis-Plans?
- Vereins-Bestätigung durch eine zweite Person: Vereins-Domain verlangen oder Prüfung durch uns?
- Kader-Vorschlag nur Name, Nummer, Einsätze, oder auch Statistik?

## Später / wartet
- Datenanfragen DHB und BHV (Entwürfe in `docs/plans/outreach-data-de.md`), Partnerschaft SHV.
- Eigenes ReID-Modell statt MSMT (Lizenz) vor einem kommerziellen Start.
- Rollen-, Holder- und Ballmodelle nur mit kommerziell nutzbaren Daten neu trainieren (ADR 003).
