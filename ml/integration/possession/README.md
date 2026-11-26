# Ballbesitz: Positionsregel gegen Ballhalter (Audit Punkt 6)

Ballbesitz pro Sekunde auf zwei Horgen-Testclips (je 609 s, geprüfte Kalibrierung, keine
Endtest-Spiele). Verglichen werden:
- heute: die Phasen aus `events.detect`, also welches Team in der gegnerischen Hälfte steht;
- der Ballhalter aus `ballpossession`: Team des letzten Halters, gilt noch 3 s nach dem letzten
  Halten;
- die Kombination: Ballhalter, wo er etwas sagt, sonst die Positionsregel.

Methoden und Regel standen fest, bevor ein Label vorlag (`poss_methods.py`, `poss_eval.py`).

- `labels/`: **LLM-Labels**, nicht von Lukas. Zwei unabhängige Durchgänge als Segmente, ein
  dritter Blick auf strittige Stücke über 2 s. Eingefroren als `truth.json` mit `truth.sha256`.
- Aufruf: `POSS_DIR=<ordner mit passA/h1.json …, passC/third.json, truth.json> SHOT_LOC_DIR=<ordner mit wo/out_h1, wo/out_h2> python poss_eval.py merge|score`.
  In `labels/` liegen dieselben Dateien flach (`passA_h1.json` = `passA/h1.json`).
- Ergebnis: `../results/possession_ballholder.json`.
