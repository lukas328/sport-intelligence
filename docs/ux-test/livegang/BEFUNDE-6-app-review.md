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
   TXT-02, TXT-04, TXT-05, TXT-08, LEGAL-01.
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

## Stand Block 1 (Helfer, 19.11.)
Gemeinsame Ursache BUG-01 bis 07, 17, 18: Es gab keinen zentralen Begriff der Perspektive. Die
Spielseite setzte bei beobachteten Spielen den Namen der anderen Mannschaft nur in den Kopf; alle
anderen Teile bekamen den Teamnamen des Kontos (`teamName`), sagten fest «Wir», «Gegentore»,
«Eigene» und lasen den Kader des Kontos. Behoben an zwei Stellen: im Web `lib/match-sides.ts`
(`matchSides`: eigene oder neutrale Perspektive, Namen beider Seiten, Heimteam zuerst) mit dem
Kontext `components/domain/match-sides.tsx`, den die Spielseite einmal setzt; in der API
`Match.observed`, das Spieler des Kontos in beobachteten Spielen abweist (Ereignisse, Spuren).

| Ticket | Stand |
|---|---|
| BUG-01 | erledigt: Seitentitel aus `matchSides`, Heimteam zuerst, nie das Konto-Team |
| BUG-02 | erledigt: «Tor {Team}» in Spiel, Szenenliste, Kamera, Punkt 1; «Wir» nur bei eigenen Spielen |
| BUG-03 | erledigt: Legende mit Teamnamen (Teamfarben nicht umgesetzt, optional) |
| BUG-04 | erledigt: Kennzahlen, Laufleistung, Aufenthaltsorte, Würfe-Filter mit Teamnamen; «Spuren von {Team}» |
| BUG-05 | erledigt: Resultatfelder mit beiden Namen, Heimteam zuerst, Hinweis «Endresultat, nicht die Tore im Video»; Trikotfarben pro Team benannt |
| BUG-06 | erledigt: Prüfen und «Wurfort nachtragen» mit beiden Teams, Heimteam zuerst |
| BUG-07 | erledigt: «Tore {Team}» statt Gegentore/Eigene Tore, «Längste Phase ohne Tor ({Team})», keine «Der Gegner war besser»-Aussage; Profil für beide Teams, wenn die andere Mannschaft als Gegner bekannt ist |
| BUG-08 | erledigt: «nicht erfasst» statt «-», unter den Kennzahlen pro Team «9 Würfe: 6 Tore, 2 gehalten, 1 daneben» aus derselben Statistik; «x von y Würfen ohne Wurfposition». Offen (TXT-02, Block 3): «Wurfort» zählt Gegenstoss mit, «Wurfposition» nur Feldpunkte |
| BUG-09 | erledigt: «2 Paraden ohne Torhüter» mit Hinweis statt «keine Würfe»; beobachtete Spiele zeigen die Torhüter beider Teams nach Nummer |
| BUG-10 | erledigt: Torbild ohne erfasste Ecke ist ein Satz, kein Null-Raster (Würfe und Torhüter) |
| BUG-11 | erledigt: Ursache «Erfasst» war die längste Einzelspur, nicht die abgedeckte Videozeit. Jetzt Videozeit der Spuren; unter 2 Minuten wird ein Team nicht gezeigt, ohne Zeile «Zu wenig Laufdaten» |
| BUG-12 | erledigt: Szenen beobachteter Spiele erscheinen, Filter «Alle / Eigene / Beobachtet», Kachel mit «Beobachtet» und Jahr; Leertext nicht mehr doppelt |
| BUG-15 | erledigt: Mitteilung nur, wenn ein früheres Spiel gegen den Gegner analysiert ist (dieselbe Bedingung wie das Gegner-Profil); Test |
| BUG-16 | erledigt: Spielseite zeigt dieselbe Gesamtzahl wie der Banner, Teilschritt als «28 % dieses Schritts»; Endzeit ab 10 Minuten auf 5 Minuten gerundet |
| BUG-17 | erledigt: eigener Abschnitt «Beobachtete Spiele» mit Jahr statt Heim/auswärts; Zähler «x von y eigenen Spielen ohne Video» |
| BUG-18 | erledigt: Heimteam zuerst in Liste, Banner, Kopf, Titel, Prüfen, Szenen. Hinweis: das Formular für beobachtete Spiele fragt nicht, wer Heimteam ist; heute gilt die andere Mannschaft als Heimteam |
| BUG-20 | erledigt: Spielverlauf ohne Anpfiff über die Videominuten («Minuten im Video»), mit Anpfiff über die abgedeckten Spielminuten |
| BUG-21 | erledigt: «Szene speichern» ist umschaltbar (`aria-pressed`), danach Link «In «Szenen» ansehen» (Szenen des Spiels) |
| UX-07 | erledigt wie entschieden: Szenen (siehe BUG-12), Onboarding-Schritt «erstes Video» mit jedem Video, Abschnitt und Zähler (siehe BUG-17) |
| TXT-03 | erledigt: «Notiz zu dieser Szene», «Szene speichern», «Marken vom Spieltag» |
| TXT-06 | erledigt: Hinweis auf den handball.ch-Bericht nur bei Spielen aus dem Spielplan (`official_game`) |
| UI-02 | erledigt: «keine Positionen» als eine Zeile statt leerem Feld, Spielbericht ohne Zeilen als Satz, Torbild siehe BUG-10 |
| L4 | erledigt: in beobachteten Spielen kein Kader des Kontos (Erfassen, Spuren, Torhüter, Zahlen); beide Teams per Rückennummer, für den beobachteten Gegner die bekannten Nummern als Vorschlag; Personen-Fragen in Prüfen entfallen dort; API weist Spieler des Kontos ab |
