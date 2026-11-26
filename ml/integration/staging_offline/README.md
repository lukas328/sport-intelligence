# Staging-Läufe offline nachrechnen (2026-11-26)

Für die Torhüter-Regel (#147) auf den Artefakten im Testbucket `handball-testdata`, nur gelesen.
Pro Lauf liegen `analysis/observations.npz`, `motion.npz`, `panorama.jpg`, `tracks.parquet`,
`play.json` in einem Ordner; die Kalibrierung steht nur in der Datenbank.

1. `keepers.py calib DIR`: Homographie Feld nach Panorama aus `tracks.parquet` und den
   Fusspunkten der Beobachtungen (Paare grob nach x sortiert, dann nächster Nachbar, RANSAC),
   schreibt `DIR/recovered_calib.json`.
2. `keepers.py track DIR`: `observe.track` mit dieser Kalibrierung (ohne Trikotfarben),
   Teams, Quellen der Labels, `missing`, und für «referee»-Tracks Dauer und Anteil am Tor.
3. `keepers.py crops DIR`: Bildausschnitte der Torhüter- und torgebundenen «referee»-Tracks aus
   `DIR/proxy.mp4` nach `DIR/gk_crops.jpg`.

Laufen mit `uv run --project packages/vision --with pyarrow python ...`, für den Vergleich einmal
aus einem Worktree von `main`. Ergebnis in `docs/plans/produkt-analyse-integration.md`
«Torhüter in eigener Trikotfarbe».
