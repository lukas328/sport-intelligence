# Wurfort aus dem Ballpfad (Audit Punkt 7)

Vergleich auf zwei Horgen-Testclips (je 10 min, geprüfte Kalibrierung, keine Endtest-Spiele):
heutiger Wurfort (nächster Angreifer in den 10 s vor der Torzeit, `shot_positions.fill_one`)
gegen den Abwurfpunkt aus dem Ballpfad (Start der letzten schnellen Ballbewegung Richtung Tor,
Werfer = Ballhalter-Box, Fusspunkt über die Homographie pro Frame).

Methode, Merge und Auswertung waren festgelegt, bevor ein Label vorlag (`methods.py`).

- `labels/`: **LLM-Labels**, nicht von Lukas. Zwei unabhängige Durchgänge (A, B) über die ganzen
  Clips, ein dritter Blick (C) bei Uneinigkeit, Prompts dabei. `truth.json` ist eingefroren
  (`truth.sha256`, von `evaluate.py` geprüft).
- `merge.py` → `finalize.py` → `evaluate.py`, mit `SHOT_LOC_DIR` = Ordner mit `wo/` (Clips,
  `out_h1`, `out_h2` mit `trk.pkl`, `motion.npz`, `observations.npz`) und `wl/` (Labels).
- Ergebnis: `../results/shot_location_ballpath.json`.
