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
