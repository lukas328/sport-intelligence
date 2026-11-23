# Übergabe der Sitzung vom 20. bis 23.11. (A1 und Kaggle-Warteschlange)

Für die Hauptsitzung. Branch `claude/happy-mendel-04tk4q`; baut auf `claude/affectionate-edison-lkw4r3`
bis `4d9e5fbc` auf (Backlog-Abschnitt «Nächste Aufgaben»), sonst nur eigene Commits. Kein Konflikt
mit `main` und mit dem neueren Stand von `affectionate-edison` (R2-HLS), geprüft am 23.11.

## Was fertig ist
1. **A1, Ballpfad für Tor-Kandidaten: hilft nicht.** Auf 49 Dev-Segmenten (13 Spiele, 113 Tore) trennt
   der heutige Kandidaten-Wert Tor und Fehlalarm mit AUC 0.81; mit Ballgeschwindigkeit, Ball am
   Torende und Anwurf-Muster wird es nicht besser (0.80, Spiel für Spiel ausgelassen). Eine tiefere
   Quote (1.5 statt 2 pro Minute) spart ein Viertel der Fragen und verliert 14 von 100 Toren. Nichts
   ins Produkt eingebaut, Endtest nicht angeschaut. Details: `produkt-analyse-integration.md`,
   «Ballpfad als Bestätigung der Tor-Kandidaten». Skripte: `ml/integration/goal_ball_cues.py`,
   `goal_ball_cues_eval.py`.
2. **Gratis-CPU von Kaggle dauernd nutzen:** `ml/integration/kaggle/observe_queue.py` beobachtet alle
   Segmente der Bibliothek (ausser Endtest-Spielen) wie im Wurf-Endtest (hrp1 960 px und YOLOX je
   jedes 3. Bild) in Kernels `handball-obs-qNNN`, je 13 Segmente, höchstens 5 gleichzeitig.
   Ergebnis pro Segment: `motion.npz`, `observations.npz`, `observe.json`.
3. **Produkt-Fehler behoben:** `observe.save_observations` stürzte ab, wenn alle Personen-Segmente
   eines Videos leer waren (Kernel q069 starb daran). Jetzt keine Zeilen gespeichert, mit Test.

## Stand der Warteschlange (23.11.)
- Fertig: rund 160 von etwa 860 Segmenten (Kernels q004 bis q006, q059 bis q069). Läuft: q070 bis
  q072, q124, q125. Offen: 51 Kernels, 660 Segmente. Bei 5 Plätzen und etwa 6 bis 10 h pro Kernel
  gut 4 Tage, wenn immer nachgefüllt wird.
- Ausgaben liegen nur auf Kaggle (Kernel-Output, bleibt bei Kaggle stehen). Die Kopien dieser
  Sitzung im Scratchpad gehen mit ihr verloren; neu holen mit
  `kaggle kernels output lukasde1000/handball-obs-qNNN -p DIR`.
- Gelernt: Kaggle-Maschinen sind unterschiedlich schnell (20 bis 50 min pro Segment). 26 Segmente pro
  Kernel überschritten 12 h, die Ausgabe war weg (q000 bis q003, neu eingereiht). Darum 13 Segmente,
  Zeitwächter nach 11 h und neu ein Aufruf pro Segment (ein kaputtes Segment steht in `failed.json`,
  die übrigen laufen weiter).
- **Leerlauf ist das Hauptproblem:** Nachfüllen geht nur, wenn eine Sitzung läuft; eine
  Hintergrund-Schleife in der Cloud hält höchstens 2 h. Seit dem 20.11. standen die Plätze oft
  mehrere Stunden leer (am 21.11. allein etwa 25 bis 35 Kernel-Stunden).

## Ablauf, wenn ein Kernel fertig ist
```bash
python ml/integration/kaggle/observe_queue.py status
```
Fertige Kernels herunterladen, dann nur die fehlenden Segmente neu einreihen und nachfüllen:
```bash
kaggle kernels output lukasde1000/handball-obs-q070 -p /tmp/q070
```
```bash
python ml/integration/kaggle/observe_queue.py requeue 70 --have /tmp/q070
```
```bash
python ml/integration/kaggle/observe_queue.py step
```
`requeue` ändert `observe_queue.json`: committen, sonst weiss die nächste Sitzung nichts davon. Ein
Kernel mit Status `error` wird nicht wiederholt: Log ansehen (liegt im Output), dann `requeue --have`.

## Offen und Vorschlag
1. **Pausen messen (A1, der verbleibende Hebel).** Braucht die echte Spieluhr als Vergleich.
   Entscheid Lukas offen:
   - Option 1 (empfohlen): Die Kernels lesen zusätzlich die Hallentafel (Uhr), dann gibt es die
     Wahrheit für die ganze Bibliothek. Braucht ein neues Code-Dataset und ab dann neue Kernels.
   - Option 2: Nur die 13 Dev-Spiele mit der Uhr aus den offiziellen Spielberichten; sofort
     machbar, aber dünn.
2. **Nachfüllen ausserhalb der Cloud-Sitzung:** auf Lukas' PC (lokale Sitzung) alle 30 min
   `observe_queue.py step` als geplante Aufgabe, oder ein geplanter Auslöser für eine Cloud-Sitzung
   alle 3 bis 4 h. Entscheid Lukas offen.
3. Wofür die Daten sonst taugen: Personen, Kamera und Ballpfad für die ganze Bibliothek, ohne neue
   CPU-Zeit wiederverwendbar (Pausen, Teamzuordnung, Ballbesitz, Wurfzeit auf mehr Spielen).

## Regeln, die galten
Nie auf dem Endtest abstimmen; Endtest-Spiele nie in der Warteschlange. Löschen auf Kaggle macht
Lukas. Keine Geheimnisse ins Repo.
