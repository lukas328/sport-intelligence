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

## Stand Block 3 (19.11.2026)
| Ticket | Stand | Was |
|---|---|---|
| UX-05 | erledigt | «Nächster Gegner» steht auf der Startseite direkt unter dem Kopf (breit: rechts neben der Liste), mit Link «Auf den Gegner vorbereiten» (über `/scouting` zum Gegner-Profil); die Ein-Zeilen-Tabelle ist weg, der Rang steht in den Fakten. |
| UX-06 | erledigt | Ist der Verein nicht bestätigt, ist «Teilen» sichtbar aus, daneben «Erst nach Vereinsbestätigung. So geht es» (Link auf Verein › Verband). «Highlights teilen» erscheint erst, wenn ein Highlight fertig ist. Die übrigen Gründe (Jugendschutz, Einwilligung, Rolle) erklärt weiter der Dialog. |
| UX-08 | erledigt | Zahlen: «Alle Zahlen» ist offen, nichts mehr aufzuklappen; die Tore nach Position stehen nur noch einmal (Zahlen, Seitenspalte, beide Teams). Im Tab Spiel sind die Torkarten weg; oben die nächste Aufgabe (L5). |
| UX-09 | erledigt wie entschieden | Abschnitt «Konto schützen» auf der Teamseite und das (ungenutzte) Banner entfernt; Punkt und Karte im Konto-Menü bleiben. Positionen sind ein eigener Modus: zu bei Ankunft, eine Zeile «Positionen festlegen». |
| UX-10 | erledigt | Spielbericht-Mitteilungen nannten das Spiel schon (Gegner, Datum, eine pro Spiel); neu nennt «Vorschläge aus den offiziellen Daten» das Team. Ungelesen-Zähler und «Alle als gelesen markieren» gab es schon. |
| UX-11 | erledigt | Gegner-Profil markiert keinen Tab mehr. Menüs (auch Konto-Menü) sind nie abgeschnitten: höchstens so hoch wie Platz ist, der Rest scrollt. «Später weiter» im Prüfen führt im Code schon zur Spielseite zurück (nicht geändert, Block 2). |
| UI-01 | erledigt | Das Wurfbild (Zahlen › Würfe, auch im Erfassen) zeigt das Tor oben wie alle anderen Felder. Der Wurfort-Dialog folgt bewusst dem Video und sagt es: «So wie im Video: das Tor links. In den Grafiken steht es oben.» Verhalten von A22 (Vorschlag vorgewählt) unverändert. |
| UI-03 | erledigt | Wurfbild und Laufwege-Heatmap auf hellem Papier statt dunklem Block. |
| UI-04 | erledigt | Ein Aufklapp-Stil (`.fold`, Chevron rechts) für «Neue Highlights erstellen», «Tore im Spiel», «Alle Tore», «Mehr zum Spiel», Saison «Mehr»; «Video 0:45» und der Mitteilungszähler in der App-Schrift; das alleinstehende «Mehr» unter dem Video heisst «Einrichten von Hand»; «Datei entfernen» rot (Bestätigung gab es schon). |
| BUG-22 | erledigt | In den Torkarten nach Position steht die Zahl über und der Name unter den Punkten der Zone; das Bild ist unten etwas höher, «Gegenstoss» bleibt im Feld. |
| TXT-02 | erledigt als Übergang | Datenmodell bleibt (Gegenstoss und 7 m sind Zonen). Anzeige «Situation: Gegenstoss» statt «Wurfort: Gegenstoss»; im Dialog stehen die beiden Tasten unter «Oder die Situation:». Offen: der Antworten-Rückblick im Prüfen (Block 2) sagt noch «Wurfort: …». |
| TXT-04 | erledigt | Ohne zugeordnete Spieler keine «Spur 306»-Zeilen und kein «kurze Spuren zeigen», sondern ein Satz mit dem Weg («im Tab Video unter «Einrichten von Hand»»); «(am Handy 6)» weg; «Angriffe … geschätzt» als Erklärung am Wert «Effizienz». |
| TXT-05 | erledigt | Unter dem konkreten Befund nur noch, was die Übungen trainieren («Diese Übungen trainieren Ablauf, Täuschung und Ruhe am Siebenmeterpunkt.»), kein «Der Befund oben betrifft «7 m»». |
| TXT-08 | erledigt wie entschieden | Saisontitel ohne Urteil: «4 Siege, 5 Niederlagen.» (Unentschieden nur, wenn es welche gibt); Trainingstipps stehen daneben im Kopf. handball.ch-Daten überall «abgeglichen vor …» (Startseite, Saison-Tabelle, Teamseite). |
| LEGAL-01 | erledigt | Schmaler Footer in der App mit Impressum, Datenschutz, AGB, Kontakt als Links auf die Website (Sprache des Nutzers), keine Inhalte. |
| L5 | erledigt (Teil Block 3) | Unter dem Kopf jeder Spielseite eine nächste Aufgabe mit Knopf: «2 Fragen offen» › Fragen beantworten, «Bei 3 Toren fehlt der Wurfort» › Wurforte nachtragen, «Noch kein Video» › Video hochladen, vor dem Spiel › Auf den Gegner vorbereiten; nichts, solange die Analyse läuft. Die Werkbank heisst überall «Einrichten von Hand». Offen: der UI-Check der ganzen Spielanalyse nach Block 1 bis 3; der Zähler «Prüfen» oben in der Tab-Zeile bleibt neben der Aufgabe stehen. |
| Website: `?src=` | erledigt | Die App merkt sich `?src=<Ort>` im sessionStorage des Tabs (kein Cookie) und schickt es bei der Registrierung und beim Anlegen des Vereins mit; die API speichert es an Konto und Verein (Migration 0052, unbrauchbare Werte werden verworfen, nie abgelehnt), sichtbar in /ops als Spalte «Herkunft». Bei Anmeldung über Google/Apple kommt es über das Anlegen des Vereins an. |
| Website: «Gemacht mit» | erledigt | Geteilte Seiten zeigen unten dezent «Gemacht mit Handball Intelligence», Link auf die Website in der Sprache des Betrachters mit `?src=shared`. |
| Website: «AGB» | erledigt | App sagt «AGB» (en «terms», fr «CG») statt «Nutzungsbedingungen»; e2e angepasst. |
