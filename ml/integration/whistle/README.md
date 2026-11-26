# Pfiff aus dem Ton

Mess-Clips (keine Endtest-Spiele):
- Mülheim-Südpfalz H1, 480 s, Staging-Asset 90c0bf9a…. Das 8-kHz-Audio des Produkts ist
  `audio_8k.wav`, 16 kHz kommt aus `original.mp4`.
- Leimental-Arbon, 600 s ab Spielbeginn (840 s im Stream), Staging-Asset c3a27b6d…, 8 und 16 kHz
  aus `original.mp4`. **Halle aus Ball-Testset 1: nur Messung, nichts davon für
  Ballnetz-Training oder Ball-Tuning.**

Die Skripte erwarten ihre Dateien im eigenen Ordner: Audio, `passA/<clip>.json`,
`passB/<clip>.json`, `passC/third.json`, `ipA/`, `ipB/`. In `labels/` liegen dieselben Dateien
flach (`whistle_passA_mue.json` = `passA/mue.json`, `inplay_passA_mue.json` = `ipA/mue.json`).
Alle Labels sind **LLM-Labels**, nicht von Lukas. Die Pfiff-Truth ist eingefroren
(`wh_truth.json`, `wh_truth.sha256`).

- `spec.py`: Spektrogramm-Streifen, mit denen die Pfiffe gelabelt wurden.
- `whistle.py`: Runde 1, Regel vorab festgelegt; `wh_eval.py merge|score` bewertet sie.
- `whistle2.py`: Runde 2. Die Parameter sind nur auf Mülheim gewählt, dann einmal auf
  Leimental getestet.
- `ip_eval.py`: Pfiff als Signal «Ball nicht im Spiel» gegen die Labels «Ball im Spiel».
- Ergebnisse: `../results/whistle_round1.json`, `whistle_round2.json`, `whistle_dead_ball.json`.

## Pfiff als Bedingung für Tor-Kandidaten (`goals/`)

- `goal_truth.py`: Tor-Truth aus zwei LLM-Durchgängen plus drittem Blick, eingefroren als
  `goals_truth.json` mit `goals_truth.sha256`.
- `goal_whistle.py`: Gate «mindestens K Pfiffe in [goal_ms + A, goal_ms + B]». Gewählt auf
  Mülheim, einmal auf Leimental getestet.
- Die Skripte erwarten `../aud/` (Audio, `wh2_eval.json`) und `<clip>/goal_candidates.json`
  neben sich. Hier liegen die Kandidaten als `goal_candidates_<clip>.json`, die Labels als
  `goal_pass*_<clip>.json`.
- Mülheim-Kandidaten kommen aus der Staging-Analyse (mit `play.json`). Für Leimental wurde
  `observe` lokal gerechnet (YOLOX s, detect_every 3, ohne Ballnetz), ohne Uhr.
- Ergebnis: `../../results/whistle_goal_gate.json`.
