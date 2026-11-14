# Echttest: zwei echte Spielclips durch die Analyse

Stand 13. November 2026, Code `claude/site-anlauf` @ 1b62a5c (App und Website nach drei
UX-Testrunden). Zum ersten Mal lief echtes Hallenvideo durch den neu gebauten Ablauf. Die Clips
und alle Bilder mit Personen liegen nicht im Repository.

## Material

Zwei Ausschnitte von je fünf Minuten, 1280 × 720, Schweizer NLB 2017, SG Horgen als Heimteam.

| | Clip 1, gegen Lakers Stäfa | Clip 2, gegen TV Möhlin |
|---|---|---|
| Kamera | Person schwenkt auf der Tribüne, keine Schnitte, keine Einblendung | Person schwenkt, tiefer, hinter den Bänken |
| Anzeigetafel der Halle | lesbar, wenn die Kamera nach links zeigt | dunkel, nicht lesbar |
| Trikots | Horgen rot, Stäfa gelb/schwarz | Horgen rot, Möhlin weiss |
| Tore, von Hand gezählt | 8 (3 Horgen, 5 Stäfa), 7 davon an der Tafel bestätigt | 3 (2 Horgen, 1 Möhlin), nur aus dem Spielverlauf, unsicher |

## Urteil

**Teilweise, und für den Trainer nahe an «nein».** Die Analyse lief auf beiden Clips ohne Fehler
durch und erzeugt in den Daten Brauchbares. Was der Trainer danach sieht, ist aber fast leer: Die
Analyse findet selbst kein Tor, es entstehen keine drei Dinge, und selbst nach allen beantworteten
Prüf-Fragen sagen «Spiel» und «Video» weiter «Noch keine Tore gefunden».

## Zahlen

| | Clip 1 | Clip 2 |
|---|---|---|
| Status | fertig, kein Fehler | fertig, kein Fehler |
| Dauer der Analyse (4 Kerne, keine Grafikkarte) | 22 Minuten | 27 Minuten |
| Feld | automatisch gefunden, hintere Ecken, Tore und Mittellinie auf etwa 1 m | automatisch gefunden, 1,5 m (rechts) bis 4 m (links) daneben |
| Verfolgte Spuren | 163 (Heim 62, Gast 69, Torhüter 15 und 4, Schiri 13) | 171 (Heim 57, Gast 77, Torhüter 20 und 0, Schiri 17) |
| Spuren mit gelesener Rückennummer | 9 | 15 |
| Selbst gefundene Tore | 0 | 0 |
| Tor-Kandidaten / Wurf-Kandidaten | 20 / 29 | 20 / 30 |
| Echte Tore unter den Kandidaten | 8 von 8, mit richtigem Team | 3 von 3 |
| Drei Dinge | keine | keine |
| Mail | «Analyse … ist fertig. Sie hat noch keine Tore gefunden. 51 Fragen» | dasselbe, «52 Fragen» |

## Was gut funktioniert

- Einstieg mit echten Verbandsdaten: `/einstieg` findet «SG Wädenswil/Horgen» auf handball.ch,
  Anmeldung per Link, Start mit echter Tabelle, Torschützen und Spielplan.
- Spiele anlegen und Videos hochladen über die Oberfläche.
- Die Kandidatenliste enthält jedes von Hand gezählte Tor.
- Spieler werden verfolgt, die Teamfarben stimmen in Clip 1 (pro Angriff rund sechs gegen sechs).
- Die Mail sagt ehrlich, dass keine Tore gefunden wurden.

## Fehler in Oberfläche und Datenweg (ohne neue Erkennung behebbar)

1. **Bestätigte Tore kommen nie in «Spiel» und «Video» an.** Nach acht (Clip 1) und drei (Clip 2)
   Bestätigungen liefert die Grafik weiter keine Tore: `services/graphics.py` lässt Tore ohne
   Wurfposition oder Schützennummer weg, und die Ereignisse behalten `clock_s = null`, auch
   nachdem der Anwurf gesetzt ist.
2. **Taktikkamera sagt «keine Positionen», obwohl die Szene 16 Spuren liefert.** `cameraScene` in
   `apps/web/src/lib/graphics.ts` gibt nichts zurück, wenn `clock_s` fehlt.
3. **Verschobene Feldecken lassen sich nicht speichern.** `POST …/calibration` antwortet 422
   («image point must be inside the frame»), weil die eigene nahe Ecke der Oberfläche ausserhalb
   des Bildes liegt. Die Oberfläche übergeht den Fehler und zählt die Frage als beantwortet.
4. **Der vierte Griff ist nicht erreichbar**, die nahen Ecken liegen ausserhalb des Bildes. Das
   Hallenbild ist klein (660 px, am Handy 320 px) und liegt unter 16 px breiten weissen Linien.
5. **«Wer ist das?» zeigt keinen Rahmen um die Person.** Vermutete Ursache: Der Rahmen wird mit
   der Homographie des Panoramas auf das bewegte Videobild gelegt.
6. **«Analyse fertig», während sie läuft:** im Video-Tab und in der Spielliste, dort für die
   ganzen 27 Minuten.
7. **Die Zahl der Fragen widerspricht sich:** Mail und Zähler 51, Prüfen 22, nach der Feldfrage 27;
   später Zähler 35 gegen Prüfen 12. Wurf-Kandidaten werden gezählt, aber nie gefragt.
8. **«Die Tore aus dem Spielbericht stehen schon im Verlauf»** bei einem Spiel ohne Spielbericht.
9. **Die Trikotfarbe aus dem Einstieg gilt nicht fürs Spiel.** Der Verein ist rot, neue Spiele
   bekommen die Vorgaben blau und rot (`KIT_DEFAULTS` in `new-match-form.tsx`), und die Analyse
   erhält diese.
10. **Nach bestätigten Toren steht kein Resultat im Kopf;** das 3:5 steht nur unter «Mehr zum
    Spiel», auf einer Achse von 0 bis 60 Minuten.
11. **Der Hallenname stimmt nicht** («Horgen Waldegg» für beide Clips).
12. Vermutung: Benachbarte Kandidatenfenster überlappen, ein Tor kann in zwei Fragen erscheinen
    und doppelt gezählt werden.

## Schwächen der Erkennung (gehört zur späteren Logik)

- Die Analyse findet selbst kein Tor. Die Anzeigetafel der Halle wird in Clip 1 nicht gelesen,
  obwohl 8:7 bis 11:11 gut lesbar sind.
- Die Güte der Felderkennung wird nicht gemessen: `observe.py` setzt den Fehler fest auf 0, das
  Vertrauen ist für beide Clips 1,0, auch für den Clip, der 2 bis 5 m daneben liegt.
- Clip 2: Die Seite, die das Heimteam verteidigt, wechselt zweimal, obwohl die Teams nie die
  Seiten tauschen; an einer Stelle zählt die Zuordnung Gast 9, Heim 2, Schiri 3 (echt 7, 6, 2).
- Die Zeiten der Tor-Kandidaten liegen 4 bis 7 Sekunden nach dem Tor (Zeitpunkt des Anwurfs).
  «Der Weg vor dem Tor» würde so den Rückweg zeigen.
- Auf der Taktikkamera stehen an einer geprüften Stelle 8 rote Punkte statt 6 und 1 Schiri statt 2;
  der Angriff wird am linken Tor gezeichnet, das Video zeigt das rechte.

## Grenzen dieses Tests

- Fünf-Minuten-Ausschnitte, kein ganzes Spiel; ohne Ton; die Torzählung stammt aus Standbildern.
- Kein Spielbericht zu diesen Spielen, das Datum ist angenommen, der Kader ist der heutige von
  handball.ch. Personen-Fragen wurden deshalb mit «Weiss nicht» beantwortet.
- Positionen auf der Taktikkamera erschienen erst, nachdem ein Tor über die API von Hand eine
  Wurfposition und Spielzeit bekam. Der Weg über die Oberfläche wurde dafür nicht gefunden.
- Wurf-Kandidaten und die Taktikkamera in Clip 2 wurden nicht geprüft.
- Die Analysedauer gilt für vier Prozessorkerne ohne Grafikkarte und sagt wenig über den Betrieb.

---

# Zweiter und dritter Durchlauf (13. November 2026)

Dieselben zwei Clips, nach den Korrekturen. Zweiter Durchlauf auf `claude/trikot-ui` @ 0c91404
(nur Clip 1, dann von einem Nutzungslimit gestoppt), dritter Durchlauf auf @ 41cc31b (beide Clips,
frischer Verein). Die Erkennung selbst ist unverändert.

## Urteil

**Clip 1: ja, mit einer Bedingung. Clip 2: teilweise.** Nach dem Prüfen sieht der Trainer auf
Start, «Spiel» und «Video» ein Resultat, den Verlauf, die Tore als Szenen und Positionen auf dem
Feld. Das Resultat stimmt aber nur, wenn er auch die freiwilligen Fragen beantwortet.

## Korrektur der Zählung von Hand

Clip 1 hat neun Tore, nicht acht: Horgen trifft schon bei 0:08 (die Anzeigetafel zeigt 7:7 bei
0:00 und 8:7 bei 0:37). Wahr im Ausschnitt: Horgen 4, Stäfa 5.

## Zahlen des dritten Durchlaufs

| | Clip 1, Stäfa | Clip 2, Möhlin |
|---|---|---|
| Analyse | 19:25 Minuten, fertig | 21:55 Minuten, fertig |
| Fragen laut Mail, Zähler, Prüfen | 12, 12, 12 | 12, 12, 12 |
| Freiwillige Fragen danach | 10 | 10 |
| Aufwand für alle 22 Fragen | etwa 6 bis 7 Minuten | etwa 6 bis 7 Minuten |
| Vorschlag des Teams richtig (Pflichtfragen) | 7 von 9 | 3 von 6 |
| Bestätigte Tore gegen die Zählung von Hand | 9 von 9 (7 nach den Pflichtfragen) | 3 von 3 (2 nach den Pflichtfragen) |
| Gezeigtes Resultat | 4:5, stimmt (2:5 nach den Pflichtfragen) | 2:1, entspricht der Zählung (1:1 nach den Pflichtfragen) |
| Feld | um 3 px korrigiert, gespeichert | automatisch etwa 3 m (links) und 1,5 m (rechts) daneben; durch Ziehen von drei Ecken korrigiert, die Positionen verschieben sich um mehrere Meter |

## Die zwölf Fehler des ersten Durchlaufs

Am echten Video gesehen, wenn nicht anders vermerkt.

| Nr. | Stand | Bemerkung |
|---|---|---|
| 1, 10 | behoben | Resultat, Verlauf und Torliste stehen auf Start, «Spiel» und «Video»; unter «Mehr zum Spiel» läuft der Verlauf noch über 0 bis 60 Minuten |
| 2 | behoben, Güte teilweise | Positionen erscheinen, auch ohne Spielzeit; die Anzahl der Punkte stimmt oft nicht |
| 3 | behoben | Ecken ausserhalb des Bildes werden gespeichert; die Fehlermeldung wurde nur mit einem künstlich erzeugten Fehler gesehen |
| 4 | behoben bei 1280 px | Hallenbild 1086 px breit, Linien 2 px, vier Griffe erreichbar; bei 390 px nicht geprüft |
| 5 | durch Weglassen gelöst | bei schwenkender Kamera wird die Frage «Wer ist das?» nicht gestellt |
| 6 | behoben | «Analyse läuft» überall, «fertig» nirgends, solange sie läuft |
| 7 | behoben | Mail, Start, Liste, Zähler und Prüfen nennen dieselbe Zahl |
| 8 | teilweise | der Satz ist weg; «So rechnen wir» nennt den Spielbericht aber noch ohne Bericht |
| 9 | behoben für genannte Farben | Vereinsfarbe gilt, Gegnerfarbe wird vor dem Hochladen gefragt; die gemerkte Farbe eines Gegners geht beim zweiten Spiel nicht an die Analyse |
| 11 | behoben | kein Hallenname mehr |
| 12 | nicht robust | kein Kandidat wird doppelt gefragt, aber ein Tor ist in zwei Fragen sichtbar und lässt sich doppelt bestätigen |

## Neue und offene Fehler nach dem dritten Durchlauf

1. **Echte Tore stecken in den freiwilligen Fragen.** Wer bei «Alles geprüft» aufhört, sieht in
   Clip 1 2:5 statt 4:5 und in Clip 2 1:1 statt 2:1.
2. **Ein Tor in zwei Fragen:** in Clip 1 bei 2:06 und 2:15 sowie bei 2:33 und 2:42. Eine doppelte
   Zählung ist möglich.
3. **Die Taktikkamera zeigt zu viele Punkte:** bis 14 rote statt 7. Zuschauer in Rot und die Bank
   in Weiss im Vordergrund werden als Spieler gezeichnet, ein blauer Torhüter als rot. Die Szene
   zeigt die sechs Sekunden vor der Kandidatenzeit, also meist den Rückweg. Eigene Tore werden am
   linken Tor gezeichnet, während das Video das rechte zeigt.
4. Nach jedem gespeicherten Feld kommt eine zweite Mail «Die Analyse … ist fertig».
5. Die gemerkte Gegnerfarbe geht nicht an die Analyse (im zweiten Durchlauf gesehen).
6. Saison «Wer trifft · aus 12 Spielen» zeigt 6, 5, 4 Tore, der Start aus denselben Berichten 50,
   44, 36.
7. Das Formular «Neues Spiel» füllt die Gegnerfarbe rot vor.
8. Ein übergangener Anwurf bleibt als offene Frage stehen; es gibt keine Antwort «nicht im Video».
   Ohne Anwurf fehlt im Video-Tab der Zeitstrahl, und die Szenenliste hat keine Zeiten.

Diese Punkte sind an die Bau-Session gegangen. Was danach behoben wird, ist nur noch durch
automatische Tests abgesichert, nicht mehr mit den echten Clips.

## Grenzen

- Prüfen wurde nur bei 1280 px bedient; bei 390 px wurden Start, Tabs und die erste Frage
  angesehen, aber keine Ecken gezogen.
- Die Zählung für Clip 2 stammt aus Standbildern (Anwurfmuster), die Anzeigetafel ist dunkel.
- Die Maschine startete während der Läufe dreimal neu; die Videos lagen im Arbeitsspeicher und
  mussten jedes Mal neu hochgeladen werden.
- handball.ch lieferte am Testtag ein Zertifikat ohne Zwischenzertifikat; die Teamsuche im
  Einstieg antwortete mit 503, bis das Zwischenzertifikat lokal ergänzt wurde. Die Prüfung der
  Zertifikate blieb eingeschaltet.

---

# Vierter Durchlauf (14. November 2026): Nachprüfung von G1 bis G9 am echten Video

Geprüft mit Clip 1 (SG Horgen gegen Lakers Stäfa, fünf Minuten, neun Tore, wahres Resultat im
Ausschnitt 4:5), als neuer Trainer am Handy (390 px) und am Desktop. Clip 2 wurde in diesem
Durchlauf nicht noch einmal ausgewertet, nur seine Anzeigetafel angesehen. Analyse 20 bis 21
Minuten, Prüfen 22 Fragen (12 Pflicht, 10 freiwillig) in rund 6 bis 7 Minuten.

## Urteil

G1 bis G8 sind am echten Video bestätigt behoben. Bei G9 war die Feldfrage am Handy nicht behoben
(ein Eckgriff lag unter dem Knopf «Bild vergrössern», das vergrösserte Bild liess sich nicht
verschieben); das ist in diesem Durchlauf behoben. Nach allen 22 Antworten steht 4:5, das wahre
Resultat. **Drei Dinge entstehen aber nie:** Kein bestätigtes Tor bekommt eine Wurfposition (H7).
Damit fehlt dem Trainer genau das, was Start und Website als Erstes versprechen.

## G1 bis G9

| # | Urteil | Gesehen |
|---|---|---|
| G1 | behoben | Nach dem Pflichtteil «Die wichtigsten Momente sind geprüft. 10 weitere könnten Tore sein.»; Start, Spiel und Video zeigen 2:5 mit «bisher bestätigt · 10 Momente offen»; «Alles geprüft» erst nach allen Antworten, dann 4:5. |
| G2 | behoben | Kein Pflicht-Ausschnitt zeigt ein bestätigtes Tor zweimal; bei 2:23 «In diesem Ausschnitt liegt das Tor von 2:15» mit «Nein, dasselbe Tor». Die genannte Zeit ist die späte Kandidatenzeit, das Tor fiel um 2:09. |
| G3 | behoben | Taktikkamera zeichnet das Tor auf der Seite, die das Video zeigt; die Szene enthält den Wurf; höchstens ein bis zwei Punkte zu viel. |
| G4 | behoben | Nach dem gespeicherten Feld keine zweite Mail, eine Mitteilung. |
| G5 | behoben | Die gemerkte Gegnerfarbe geht ohne neue Frage in die Analyse. |
| G6 | behoben | Saison und Start zeigen dieselben Torschützen. |
| G7 | behoben | Die Gegnerfarbe bleibt leer, bis sie gewählt ist. |
| G8 | behoben | «Der Anwurf ist nicht im Video» führt zur Spielminute des Anfangs; die Spielzeiten stimmen danach. |
| G9 | Feldfrage am Handy war nicht behoben, jetzt behoben | Zoom-Knopf unter dem Bild, Ziehen nur auf den Griffen, das vergrösserte Bild lässt sich mit einem Finger verschieben. |

## Neue Befunde

| # | Schwere | Befund | Stand |
|---|---|---|---|
| H1 | stört | Eckgriff unter dem Zoom-Knopf, Vergrösserung nicht verschiebbar (390 px) | behoben |
| H2 | falsch | Jede Torfrage sagte «die Anzeigetafel sagt es nicht sicher», obwohl keine Tafel gelesen wurde | behoben |
| H3 | stört | Liste «Beantwortet» ohne Zeiten | behoben |
| H4 | Kleinigkeit | Prüfen-Kopf «0 Fragen» bei offenen Momenten; Listenzeile «7 Tore im Video» ohne offene Momente | behoben |
| H5 | falsche Zahl | «Längste Phase ohne eigenes Tor: 8 min» ab Anpfiff gezählt, obwohl das Video in Minute 8 beginnt | behoben |
| H6 | falsch | Zahlen-Tab nennt den Spielbericht, obwohl es keinen gibt | behoben |
| H7 | blockiert die drei Dinge | Bestätigte Tor-Momente bekommen keine Wurfposition: `shot_positions.fill` läuft nur am Ende der Analyse, nicht bei der Bestätigung, und setzt nur x/y, während `zone_of()` in graphics.py nur shot_zone und shot_type liest. Prüfen fragt nie nach dem Wurfort. Der Trainer liest «Für drei Dinge braucht es mehr Tore mit Position» und hat keinen Weg dorthin. | offen, Entscheid: Tipp «Von wo?» bei der Tor-Bestätigung |
| H8 | Kleinigkeit | Dieselbe Szene heisst 8:15 (Spiel), 8:14 (Sammlung) und «Video 0:15» (Szenen) | offen |
| H9 | Kleinigkeit | Saison: «nach 12 Spielen» (mit Cup und Freundschaftsspielen), Tabelle 8, Verlauf zeigt die letzten 10, ohne es zu sagen | offen |
| H10 | Kleinigkeit | «Welche Spielminute zeigt der Anfang?» ist bei 8:15 mehrdeutig; «Zurück» steht schon bei Frage 1 | offen |

## Anzeigetafel der Halle (gemessen)

Clip 1: Die Tafel hängt links oben an der Wand und ist rund 100 von 300 Sekunden im Bild, immer
wenn die Kamera nach links schwenkt. Im 720p-Bild ist sie etwa 100 × 70 Pixel gross, die Ziffern
12 bis 15 Pixel hoch, für das Auge gut lesbar (7:7, 8:7, 8:8, 9:8, 10:10, 11:11; Spieluhr =
Videozeit + 8:15). Die Analyse liest trotzdem nichts: Die Texterkennung gibt die Uhr ohne
Doppelpunkt zurück («849» statt 8:49), darum greift die Uhr-Regel in `hallboard.py` nie, und die
einzelnen Leuchtziffern des Spielstands findet sie gar nicht. Ansatz: drei- und vierstellige
Uhrfelder als mm:ss gelten lassen, die Tafel über Rot auf Schwarz finden, eine eigene Erkennung für
Sieben-Segment-Ziffern. Clip 2: Tafel angeschnitten und dunkel, keine Quelle.

## Erkennung, beobachtet

Tor-Momente liegen weiter 4 bis 7 Sekunden nach dem Tor; das Fenster der Frage (10 s davor bis 2 s
danach) fängt es meist auf, schneidet aber einzelne Tore ab. In den zwei geprüften Szenen höchstens
ein bis zwei Personen zu viel, ein Schiedsrichter fehlt meist. Die Seite kippte in Clip 1 nicht.

## Grenzen

Ein Ausschnitt von fünf Minuten, kein ganzes Spiel: Wie lange das Prüfen bei 50 bis 60 Toren
dauert, ist nicht gemessen. Kein Spielbericht zu diesen Spielen: Der Weg «Tore aus dem
Spielbericht» ist weiter nur mit automatischen Tests geprüft. Clip 2 nicht noch einmal
ausgewertet. Die Wurforte der neun Tore sind am Standbild nur unsicher zu bestimmen.
