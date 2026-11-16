# Messplan Phase 0: Spieler, Kalibrierung und Ball auf dem Goldstandard

Stand 2026-11-12, Hauptsitzung. Gehört zu `docs/plans/tracking-strategie.md` (Abschnitt 6, Phase 0).
Ziel: die heutige Pipeline auf denselben 42 Goldstandard-Clips (`ml/gold/gold_clips.json`) messen,
bevor wir etwas neu bauen. Jede Zahl wird pro Kameraart (fest, schwenkend, TV mit Zoom) und pro
Auflösung getrennt ausgewiesen.

## 1. Ball (läuft)

- Labels: Seite "Goldstandard Ball", jedes Bild mit Zustand frei, in der Hand, verdeckt oder
  nicht im Bild, dazu der Abwurf-Moment bei Würfen.
- Kennzahlen pro Modell (heutiges Netz, OWLv2, später Ballmodell v2):
  - Trefferquote innerhalb von 8 px bzw. 12 px (1280 px breit), getrennt nach frei und in der Hand;
  - Fehlalarme in Bildern ohne sichtbaren Ball;
  - Pfad-Kennzahlen nach der Fusion: Anteil der Bilder mit richtigem Ballpfad, Lücken über 0.5 s,
    Wechsel auf falsche Objekte pro Minute;
  - Würfe: Abwurf-Moment innerhalb von ±3 Bildern erkannt.

## 2. Spieler und Kalibrierung (vorzubereiten)

**Labels (wenig Aufwand, pro Clip etwa 2 Minuten):**
- Pro Clip drei Bilder (Anfang, Mitte, Ende). In jedem klickt Lukas die Fusspunkte aller Personen
  auf dem Feld an und wählt für jede die Rolle: Team A, Team B, Torhüter A, Torhüter B,
  Schiedsrichter. Der Detektor schlägt die Punkte vor; Lukas korrigiert nur.
- Pro Clip ein Bild mit 4 bis 6 Feldpunkten: Ecken, Mittellinie, Torpfosten, 6-m- und 9-m-Linie.
  Das ergibt eine Referenz-Homographie (Bild zu Feld in Metern).

**Kennzahlen:**
- Personen: Recall und Präzision der Fusspunkte (Treffer innerhalb von 0.5 m im Feld bzw. 15 px im
  Bild), getrennt für Feld und Bank bzw. Publikum (Fehlalarme ausserhalb des Feldes).
- Rollen: Anteil richtig zugeordneter Teams und Rollen.
- Kalibrierung: mittlerer Fehler in Metern der Referenzpunkte durch die automatische Kalibrierung
  (ADR 025); Anteil der Clips mit Fehler unter 0.5 m bzw. ohne Kalibrierung.
- Tracking über den Clip: Wechsel der Identität (ID-Switches) zwischen den drei Bildern, sobald
  die Ball-Labels Clips mit durchgehenden Pfaden liefern; volles MOTA/HOTA erst mit dichteren
  Spieler-Labels.

**Einschränkung:** 8 Sekunden sind kurz. Die automatische Kalibrierung braucht teils längere
Videostücke (Kamerabewegung, Linien aus vielen Bildern). Gemessen wird darum mit dem ganzen
Segment (etwa 3 Minuten) als Eingabe, ausgewertet nur auf den Bildern des Clips.

## 3. Reihenfolge

1. Ball-Labels (Lukas, läuft). Danach sofort: Messung des heutigen Netzes, von OWLv2 und der
   Vorschläge auf dem Goldstandard (CPU, Hauptsitzung).
2. Seite für Spieler- und Feldpunkte bauen (Vorschläge vom Personendetektor auf Kaggle).
3. Heutige Pipeline auf den 42 Segmenten laufen lassen (Kaggle oder lokale Sitzung), Kennzahlen
   aus Abschnitt 2.
4. Ergebnis in `docs/plans/tracking-strategie.md` nachtragen: Zielwerte gegen Ist-Werte.
