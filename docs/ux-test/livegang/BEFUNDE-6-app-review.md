# Befunde Runde 6: externes App-Review (19.11.2026)

Quelle: «Pre-Launch Review – Handball Intelligence Web-App» vom 19.11.2026 (Testkonto TV Thalwil auf
Staging, Desktop etwa 993 x 668, 45 Tickets, ohne Blick in den Code). Hier steht die Bewertung der
Hauptsitzung: was zu unserer Lage passt, was nicht, und die Entscheide zu den offenen Fragen.
Grundsatz wie in Runde 5: nichts blind übernehmen; die Ursachen im Review sind Vermutungen und
werden im Code geprüft.

## Bewertung
**Passt fast ganz.** Das Review ist konkret, reproduzierbar und trifft echte Fehler. Der grösste
Block (BUG-01 bis 07, 17, 18) ist ein einziges Problem: Bei beobachteten Spielen (das eigene Team
spielt nicht) wird das Konto-Team als «Wir» eingesetzt. Das ist vor einem Pilot ein Muss, weil
Gegner-Scouting ein Kernweg ist.

Nicht oder anders übernommen:
| Ticket | Entscheid | Begründung |
|---|---|---|
| TXT-01 «die drei Dinge» in «Muster» umbenennen | **ja (Lukas, 19.11.), ganz am Schluss** | Neu: «die drei Muster» (en «the three patterns», fr «les trois tendances») in App, Website, Demo und Hilfe; nur sichtbare Texte, URLs wie `?ding=1` bleiben. Als letzter Schritt, weil es fast jede Datei berührt. Ursprüngliche Einschätzung der Hauptsitzung:  «Die drei Dinge» ist das Kernversprechen auf Website, Demo und App (Lukas' Konzept). Ein Umbenennen müsste Lukas entscheiden. Stattdessen beim ersten Auftreten konkret sagen, was ein Ding ist («ein Muster, das sich wiederholt, z. B. drei Gegentore aus derselben Ecke»), den Satz «Ein Ding entsteht, sobald …» verständlich machen. |
| TXT-08 Saison-Headline | **Fakten zuerst** | «4 Siege, 5 Niederlagen.» als Titel, darunter der Link zu den Trainingstipps; kein belehrender Ton. Zeitstempel einheitlich («abgeglichen vor 9 Stunden»). |
| UX-07 Konzept beobachtete Spiele | **entschieden, siehe unten** | |
| BUG-12 Szenen leer | **mit UX-07** | Der heutige Leertext ist falsch, egal wie entschieden wird. |
| BUG-13 Zeichnen | **erst prüfen** | Gibt es einen Zeichenmodus im Video? Wenn ja reparieren, wenn nein den Knopf im Video-Modus ausblenden. Kein neues Zeichenwerkzeug bauen. |
| BUG-11 Laufleistung | **ehrlich statt schön** | Ursache suchen; wenn die Daten zu dünn sind, Abschnitt ausblenden statt Zahl zeigen. Keine erfundene Normalisierung. |
| UI-01 eine Spielfeld-Ausrichtung | **Tor oben überall, ausser Wurfort-Dialog** | Der Dialog folgt bewusst dem Video («das Tor links»); das bleibt, wird aber beschriftet. |
| UX-02 Player sticky, zweispaltig | **umsetzen** | Grösster Gewinn im Video-Tab. |
| UX-09 2FA-Hinweis 3x | **teilweise** | Der Punkt am Konto bleibt (B48, Runde 1 abgenommen), das Banner und der Abschnitt auf der Teamseite gehen. |
| UX-13 Filter, TXT-07 Namen | **später (P3)** | Nach dem Pilot. |
| LEGAL-01 Footer | **umsetzen, nur Links** | Links auf die Entwürfe der Website; keine Inhalte. |
| Rest | **umsetzen** wie im Review | |

## Entscheide (Hauptsitzung, 2026-11-19)
- **UX-07 beobachtete Spiele:**
  1. Szenen beobachteter Spiele erscheinen in «Szenen», gekennzeichnet «Beobachtet», mit Filter
     «Eigene / Beobachtet»; sie zählen nicht in Saison und drei Dinge des eigenen Teams.
  2. Der Onboarding-Schritt «Lade dein erstes Video hoch» gilt als erledigt, sobald irgendein Video
     analysiert ist.
  3. Die Spieleliste bekommt einen eigenen Abschnitt «Beobachtete Spiele», ohne Heim/auswärts, mit
     Jahr; der Zähler «x von y ohne Video» zählt nur eigene Spiele.
- **Neutrale Perspektive:** Bei beobachteten Spielen gibt es kein «eigenes Team». Beide Teams heissen
  mit Namen, «Wir», «Eigene», «Gegentore» entfallen; Reihenfolge überall Heimteam zuerst.

## Umsetzung (Helfer, Reihenfolge)
1. Beobachtete Spiele und Zahlen: BUG-01 bis 12, 15 bis 18, 20, 21, UX-07, TXT-03, TXT-06, UI-02.
2. Video-Tab: UX-01 bis 04, BUG-13, 14, 19, UI-05, UI-06, A11Y-01, UX-12 nach A22.
3. Rest P1/P2: UX-05, UX-06, UX-08, UX-09, UX-10, UX-11, UI-01, UI-03, UI-04, BUG-22, TXT-01,
   TXT-02, TXT-04, TXT-05, TXT-08, LEGAL-01. Dazu aus dem Website-Review: Herkunft `?src=` bei der
   Registrierung speichern (ohne Cookies), «Gemacht mit Handball Intelligence» dezent auf geteilten
   Szenen-Links, «Nutzungsbedingungen» in der App durch «AGB» ersetzen.
4. Zum Schluss: «drei Dinge» wird «drei Muster» (TXT-01), auch auf der Website.

## Ergänzungen aus Lukas' Notizen beim Testen (19.11.)
Doppelt mit dem Review (nicht neu): Szenen nur bei eigenen Spielen (UX-07, BUG-12), Unterteilung
eigene / alle / Gegner-Spiele (UX-07, UX-13), leicht zwischen Video und Feld von oben wechseln
(UX-01), Mannschaften wechseln hin und her (BUG-18), Steuerung doppelt (vermutlich BUG-19), Zahlen
«super leer» (UX-08, UI-02).

Neu:
| # | Befund | Entscheid | Block |
|---|---|---|---|
| L1 | «Ich will eigentlich nicht jedes Tor markieren müssen» | Richtung: weniger Fragen. Kurzfristig: Tore, die zum offiziellen Spielbericht passen, ohne Frage übernehmen (prüfen, was der Abgleich heute schon tut); Fragen nur, wo die Analyse unsicher ist. Mittelfristig bessere Tor-Kandidaten (Präzision heute 29 %). | Analyse, eigener Auftrag |
| L2 | Bei «Tor oder kein Tor?» soll das Bild so gezeigt werden, dass man es direkt beurteilen kann | Prüfen zeigt den Clip vollständig (BUG-14) und rund um den Torabschluss, Tor gut sichtbar; kein abgeschnittenes Video. | 2 |
| L3 | Erst einige Fragen beantwortet, dann standen da «24 weitere»; nach dem Wegnavigieren waren sie weg | Fehler: offene Fragen müssen bleiben, bis sie beantwortet sind, und der Zähler muss stimmen. Ursache suchen. | 2 |
| L4 | Spielerauswahl bei einem beobachteten Spiel zeigt nur den Kader des eigenen Teams; beide Teams wählbar | Gehört zur neutralen Perspektive. | 1 |
| L5 | UI/UX allgemein verwirrend: was ist wo, was muss man machen; wozu die Werkbank | Werkbank nur hinter «Einrichten von Hand» (wie B10), sonst nirgends; auf jeder Spielseite oben eine klare nächste Aufgabe («2 Fragen offen», «Wurforte nachtragen»). Danach ein UI-Check der ganzen Spielanalyse. | 3 |

Stand pro Ticket wird hier nachgetragen.

## Stand Block 2 (Video-Tab und Prüfen, 19.11.)
| Ticket | Stand |
|---|---|
| UX-01 | erledigt: Video ist Standard, Umschalter über dem Bild, Wahl pro Gerät gemerkt (localStorage, ohne Speicher wieder Video). «Feld von oben» ist ausgegraut, wenn die Szene keine Positionen hat; darunter der Grund («keine Positionen» oder «Feld noch nicht bestätigt» mit Link «Feld prüfen»). |
| UX-02 | erledigt: ab Laptop zwei Spalten, Player bleibt oben stehen (sticky), Liste rechts; am Handy Player sticky unter der Kopfzeile, Liste darunter. Klick auf eine Szene weiter unten holt den Player ins Bild. Wurfort bleibt rechts unter der Liste (sonst wird die sticky Spalte zu hoch). |
| UX-03 | erledigt: «Vorherige Szene» und «Nächste Szene» immer, nicht nur bei einem Ding; Tasten N und P im Player, Hinweiszeile darunter. Einzelbild-Knöpfe zeigen jetzt Pfeilspitzen statt Sprung-Symbol, mit Tooltip. |
| UX-04 | erledigt: aktive Szene mit Hintergrund und Balken, der Wurfort bleibt stehen; Teamfarben-Punkt pro Zeile; Zeit nur einmal. Am Clip-Ende «Szene zu Ende.» mit «Nächste Szene» und «Weiterlaufen lassen». |
| BUG-13 | Zeichnen gibt es, aber nur in der Werkbank. Der Knopf auf der Bühne öffnete bisher nur die Werkbank unten, ohne Werkzeug. Jetzt: Video pausiert, Werkbank öffnet mit den Zeichenwerkzeugen (aria-pressed) auf genau diesem Moment und scrollt hin. Im Modus «Feld von oben» ist der Knopf weg. Kein neues Werkzeug gebaut. |
| BUG-19 | erledigt: die Werkbank (mit eigenem Player) wird nur gemountet, wenn sie offen ist; Sprünge aus anderen Tabs warten auf ihren Player. Bei geschlossener Werkbank ein `<video>`. Mit offener Werkbank sind es bewusst zwei (Bühne und Werkbank sichtbar). |
| BUG-14, L2 | erledigt: im Prüfen liegt die Steuerung unter dem Bild statt darüber (sie deckte bei schmalem Video fast alles zu), `object-fit: contain`, Breite nach Bildschirmhöhe begrenzt, Antwortspalte auf Laptops schmaler. Der Clip um den Torabschluss läuft in Schleife. |
| L3 | Ursache: das Budget von Prüfen (A6). Nach der Hauptrunde ist `checks` leer, die übrigen Momente stehen nur in `more_checks`. Alles ausserhalb von Prüfen zählte nur `checks`: der Link «Prüfen» auf der Spielseite verschwand, die Glocke sprang auf «Alles geprüft» und führte zur Spielseite. Die Momente waren in der Datenbank nie weg, nur nicht mehr erreichbar. Jetzt: Spielseite zeigt «Prüfen · n weitere», die Glocke bleibt ruhig, sagt aber «n weitere Momente warten unter «Mehr prüfen»» und führt zu Prüfen; der Zähler folgt jeder Antwort. Regressionstest API (`test_the_moments_behind_more_stay_until_answered`) und Web (`graphics.test.ts`). Nebenbei gesehen, nicht geändert: ein beantworteter Anwurf gibt seinen Platz im Budget frei, dann rückt ein weiterer Moment in die Hauptrunde nach. |
| UI-05 | erledigt: Bild 16:9, Breite so begrenzt, dass Bild und Steuerung in die Fensterhöhe passen. |
| UI-06 | erledigt: Legende nur bei «Feld von oben». |
| A11Y-01 | erledigt für den Video-Tab: Umschalter mit aria-pressed und Grund bei deaktiviert; «Szene merken» ist ein Umschalter (aria-pressed, Häkchen, wieder lösbar statt grau). Teamfarben in der Szenenliste zusätzlich mit Namen; die Rail trennt die Teams schon über oben/unten. Überschneidet sich mit BUG-21 (Block 1, wo gemerkte Szenen erscheinen). |
| UX-12 | erledigt: der Wurfort-Dialog aus dem Video-Tab zeigt die Szene klein, stumm und in Schleife über dem Feld. Die Logik von A22 (Schätzung vorausgewählt, ein Tippen bestätigt) ist unverändert. |

Geprüft mit Unit-Tests, Typecheck, Lint und pytest. Kein Browser-Smoke-Test: die Spielseite braucht das Backend; die e2e-Specs sind an die geänderten Texte angepasst, aber nicht gelaufen.
