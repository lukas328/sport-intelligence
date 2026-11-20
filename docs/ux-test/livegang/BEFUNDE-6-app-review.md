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
| TXT-01 «die drei Dinge» in «Muster» umbenennen | **erledigt (19.11.): Muster (ohne Zahl)** | Lukas, 19.11. spät: nur «Muster», ohne die Zahl drei, weil es beliebig viele sein können: «die Muster», «ein Muster» (en «the patterns», «a pattern», fr «les tendances», «une tendance»); eine Zahl nur, wo sie die echte Anzahl ist. Umgesetzt in App, Website, Demo, Hilfe, Ratgeber, Blog, Mails, PDF; Begriff in `docs/design/ux-reset/SPEC.md` Abschnitt 9. Erster Entscheid war «die drei Muster»; nur sichtbare Texte, URLs wie `?ding=1` bleiben. Als letzter Schritt, weil es fast jede Datei berührt. Ursprüngliche Einschätzung der Hauptsitzung:  «Die drei Dinge» ist das Kernversprechen auf Website, Demo und App (Lukas' Konzept). Ein Umbenennen müsste Lukas entscheiden. Stattdessen beim ersten Auftreten konkret sagen, was ein Ding ist («ein Muster, das sich wiederholt, z. B. drei Gegentore aus derselben Ecke»), den Satz «Ein Ding entsteht, sobald …» verständlich machen. |
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
4. Zum Schluss: «drei Dinge» wird «Muster», ohne Zahl (TXT-01), auch auf der Website. Erledigt.

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

## UI-Check 20.11.
Wie: lokaler Stack ohne Docker (`docs/runbooks/local-stack-ohne-docker.md`), Produktions-Build,
Seed-Daten (HC Tannengrün, Herren 1), dazu für den Check ein beobachtetes Spiel «HSG Sturmfalke
gegen SC Eisberg» (HSG Sturmfalke Heimteam, synthetisches Video, 97 Ereignisse ohne Spieler; danach
wieder gelöscht, damit die Produktbilder die Seed-Daten zeigen). Als Trainerin durchgegangen:
Startseite (Spiele), Spielseite Spiel/Video/Zahlen, Prüfen, Szenen, Saison, Team; je Desktop
1280 x 800 und Handy 390 x 844, Bilder angeschaut, Texte nach «drei Dinge», «Wir», «Gegentor»,
«Eigene», «undefined», «NaN» und Querscroll durchsucht. Kein «drei Dinge» mehr gefunden, kein
Querscroll, keine Fehler in der Browser-Konsole.

Behoben:
| Was | Befund | Behebung |
|---|---|---|
| Resultat beobachteter Spiele | Titel «HSG Sturmfalke gegen SC Eisberg», aber Resultat 24:26 und Legende «SC Eisberg, HSG Sturmfalke»: die Zahlen standen in Datenreihenfolge (die andere Mannschaft als eigene Seite), nicht Heimteam zuerst (BUG-18) | Kopf (Spiel, Streifen in Video/Zahlen), Prüfen und «Wurfort nachtragen» zeigen 26:24, die Legende, der Spielverlauf (Heimteam oben) und «Halbzeit»/«Schluss» folgen. Eigene Spiele bleiben «wir zuerst» wie bisher. `oppFirst` in `lib/match-sides.ts` mit Test |
| Kennzahlen beobachteter Spiele | Tabelle «Kennzahlen im Vergleich» und die Zeilen «38 Würfe: …» mit dem Auswärtsteam zuerst | Spalten und Zeilen Heimteam zuerst |
| Spieleliste | Beim beobachteten Spiel «Muster 1: Gegentore aus Gegenstössen» | «Muster 1: Tore HSG Sturmfalke aus Gegenstössen» (die Zeile kennt jetzt die neutrale Perspektive) |
| Erklärsatz der Muster | «etwa über welche Seite die meisten Gegentore fielen» auch im beobachteten Spiel | eigener Satz für beobachtete Spiele: «über welche Seite ein Team die meisten Tore warf» (de, fr, en) |
| Szenen | Mit Filter «Alle» zählte die Startfrage «Gegentor, aussen rechts, letzte 3 mit Video» das beobachtete Spiel mit: «25 von 81» statt «26 von 77»; «Gegentor» hiess dort «Tor des beobachteten Gegners». Widerspricht dem Entscheid «zählen nicht in Saison und Mustern des eigenen Teams» | Unter «Alle» meinen «letztes Spiel», «letzte 3» und die Startantwort die eigenen Spiele; Gegentor, Tor, Parade, Ballverlust suchen dort nur in eigenen Spielen. Unter «Beobachtet» bleibt alles wählbar |
| Handy, Spielseite | «Prüfen», «Teilen», «Mehr» brauchten 358 px bei 358 px Platz; «Mehr» rutschte allein auf eine zweite Zeile | kleinerer Abstand am Handy, eine Zeile |

Offen (mit Empfehlung):
| Was | Empfehlung |
|---|---|
| Saison-Titel «Fünf Spiele. Und aussen rechts bleibt offen.» Der Entscheid TXT-08 sagt «Fakten zuerst, ohne Urteil»; umgesetzt ist das nur, wenn sich nichts wiederholt. Mit Muster bleibt der Satz mit «bleibt offen» (auch die Geschichte der Website und das Produktbild «get-season»). | Lukas entscheiden lassen. Vorschlag: so lassen, weil es eine Tatsache aus den Daten ist und kein Urteil über das Team; sonst Website-Text und Produktbild mit ändern. |
| Video-Tab beobachteter Spiele: die Rail unter dem Video zeigt die Datenseite (andere Mannschaft) oben, auch wenn das beobachtete Team Heimteam ist. | Klein; mit der Frage «wer ist Heimteam» im Formular für beobachtete Spiele lösen (offen seit BUG-18). |
| «Ballverluste nach Typ: Schritte 1 · Fehlpass 5 · …»: die Zahl steht weit weg vom Wort, liest sich wie «1 Fehlpass». | Zahl vor das Wort («1 Schritte», besser «Schritte: 1»), P3. |
| «Aus: Video · 56 Tore von dir bestätigt, bei 56 mit Wurfort ⓘ»: am Handy steht das Info-Zeichen allein auf einer Zeile. | Zeichen mit dem letzten Wort zusammenhalten (`whitespace-nowrap`), P3. |
| Ein Torhüter ohne Nummer und ohne bekannten Namen erscheint im Spielbericht als «#?». Im Check künstlich (Testdaten mit einer erfundenen `goalkeeper_id`, die die API ungeprüft in `attributes` annimmt). | «ohne Nummer» statt «#?»; prüfen, ob die API `goalkeeper_id` gegen den Kader prüfen soll. P3. |
| Die Spielseite zeigt im Seed-Demo «1 Frage offen» (Feld prüfen); die Analyse des synthetischen Videos braucht immer die Feldbestätigung. | Für die Demo so lassen; ehrlich. |

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
| TXT-02 | erledigt als Übergang | Datenmodell bleibt (Gegenstoss und 7 m sind Zonen). Anzeige «Situation: Gegenstoss» statt «Wurfort: Gegenstoss»; im Dialog stehen die beiden Tasten unter «Oder die Situation:». Auch der Antworten-Rückblick im Prüfen sagt «Situation: …». |
| TXT-04 | erledigt | Ohne zugeordnete Spieler keine «Spur 306»-Zeilen und kein «kurze Spuren zeigen», sondern ein Satz mit dem Weg («im Tab Video unter «Einrichten von Hand»»); «(am Handy 6)» weg; «Angriffe … geschätzt» als Erklärung am Wert «Effizienz». |
| TXT-05 | erledigt | Unter dem konkreten Befund nur noch, was die Übungen trainieren («Diese Übungen trainieren Ablauf, Täuschung und Ruhe am Siebenmeterpunkt.»), kein «Der Befund oben betrifft «7 m»». |
| TXT-08 | erledigt wie entschieden | Saisontitel ohne Urteil: «4 Siege, 5 Niederlagen.» (Unentschieden nur, wenn es welche gibt); Trainingstipps stehen daneben im Kopf. handball.ch-Daten überall «abgeglichen vor …» (Startseite, Saison-Tabelle, Teamseite). |
| LEGAL-01 | erledigt | Schmaler Footer in der App mit Impressum, Datenschutz, AGB, Kontakt als Links auf die Website (Sprache des Nutzers), keine Inhalte. |
| L5 | erledigt (Teil Block 3) | Unter dem Kopf jeder Spielseite eine nächste Aufgabe mit Knopf: «2 Fragen offen» › Fragen beantworten, «Bei 3 Toren fehlt der Wurfort» › Wurforte nachtragen, «Noch kein Video» › Video hochladen, vor dem Spiel › Auf den Gegner vorbereiten; nichts, solange die Analyse läuft. Die Werkbank heisst überall «Einrichten von Hand». Offen: der UI-Check der ganzen Spielanalyse nach Block 1 bis 3; der Zähler «Prüfen» oben in der Tab-Zeile bleibt neben der Aufgabe stehen. |
| Website: `?src=` | erledigt | Die App merkt sich `?src=<Ort>` im sessionStorage des Tabs (kein Cookie) und schickt es bei der Registrierung und beim Anlegen des Vereins mit; die API speichert es an Konto und Verein (Migration 0052, unbrauchbare Werte werden verworfen, nie abgelehnt), sichtbar in /ops als Spalte «Herkunft». Bei Anmeldung über Google/Apple kommt es über das Anlegen des Vereins an. |
| Website: «Gemacht mit» | erledigt | Geteilte Seiten zeigen unten dezent «Gemacht mit Handball Intelligence», Link auf die Website in der Sprache des Betrachters mit `?src=shared`. |
| Website: «AGB» | erledigt | App sagt «AGB» (en «terms», fr «CG») statt «Nutzungsbedingungen»; e2e angepasst. |

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

- L1 (19.11.): Kurzfristiger Teil umgesetzt. Ein Tor des Spielberichts wird ohne Frage auf seinen
  Tor-Kandidaten gelegt, nur wenn die Uhr zu dieser Zeit im Video gelesen wurde, genau ein Kandidat
  und genau ein Spielbericht-Tor beieinander liegen und das Team passt; in Prüfen und in der
  Kandidatenliste «aus dem Spielbericht übernommen», mit «Rückgängig». Alles Unsichere bleibt eine
  Frage. Befund dabei: Kandidaten an Spielbericht-Toren wurden schon vorher nicht gefragt («schon
  erfasst»), aber an der aus dem Anwurf gerechneten Zeit, die nach einem Time-out danebenliegt.
  Zahlen nur aus Tests, keine echten Spiele gemessen. Regel und Messung:
  `docs/plans/produkt-analyse-integration.md`, Abschnitt «Tore aus dem Spielbericht ohne Frage».
  Offen: bessere Tor-Kandidaten (mittelfristig).
