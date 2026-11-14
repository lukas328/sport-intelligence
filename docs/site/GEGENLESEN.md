# Website gegengelesen: Trainer-Blick, SEO und KI, Fakten und Französisch

Stand 14. November 2026. Gegengelesen wurde der Stand von `claude/site-seo` @ 09585f2, ausgecheckt
auf `claude/site-review`. Am Code der Seite ist nichts geändert. Die Seite wurde gebaut
(`pnpm --filter @handball/site build`: 152 Seiten, 122 indexierbar). `out/` lief lokal, und die
Seiten wurden mit Playwright bei 390 px und 1280 px fotografiert und angesehen. Die Prüfung von
`out/` lief mit eigenen Skripten, nicht mit dem Prüfskript der Bau-Session.

## Gesamteinschätzung

Als Trainerin würde ich nach dieser Seite **ein Spiel ausprobieren, aber mit gebremster Erwartung
und noch nicht als Verein zahlen**. Der Filmen-Ratgeber ist gut: Nach zwei Minuten weiss ich, was
ich am Samstag tue. Die Seite sagt auch ehrlicher als die meisten Anbieter, was die Analyse nicht
kann.

Am ehesten hält mich ab, dass zwei Dinge nicht zusammenpassen. Die Seite verspricht auf jeder Seite
«ein paar Minuten prüfen» und als Hauptbild «drei Dinge zum Mitnehmen». Der Echttest belegt das
nicht: 6 bis 7 Minuten für einen Ausschnitt von 5 Minuten, und keine drei Dinge. Das Demo zeigt
dazu eine Art «Ding», die die App gar nicht erzeugt.

Als Vereinspräsident halten mich das Impressum ohne Betreiberin, AGB und Datenschutz als
«Entwurf», der Datenstandort «vorgesehen» und eine «Über uns»-Seite ohne einen einzigen Namen ab.

## Was selbst geprüft ist und was nicht

**Selbst geprüft:**
- Build und das ausgelieferte `out/`.
- Bildschirmfotos von Start, Filmen-Ratgeber, Einwilligungs-Ratgeber, Einwilligungs-Vorlage,
  Fakten, Über uns, Preise und Demo (de) sowie Start (fr), je bei 390 px und 1280 px.
- Titel, Beschreibung, h1 und Überschriftenfolge, canonical, hreflang (gegenseitig, x-default),
  Sitemap gegen die gebauten Seiten, robots.txt, JSON-LD (parst, Typen), Open Graph, Alt-Texte,
  interne Links (tote Links, eingehende Links aus dem Inhalt), Druck der Vorlagen als A4-PDF.
- llms.txt, llms-full.txt und /de/fakten/ gelesen.
- Produkt-Aussagen gegen `docs/ux-test/echttest/BERICHT.md`, `docs/OPEN_QUESTIONS.md` und den Code
  (`apps/web/src/lib/three-things.ts`, `apps/site/src/lib/demo.ts`, Upload per Link und Import des
  Spielberichts in `apps/api`).
- Französisch: Start, Fakten, Ratgeber «Filmen», «Gegentore nach Position» und «Begriffe», die
  Einwilligungs-Vorlage, dazu eine Suche nach vous/tu über alle fr-Texte.
- Englisch: nur Start, als Stichprobe.

**Extern geprüft am 14. November 2026, über einen Hilfsauftrag mit Webabruf:**
- Jede Anbieter-Aussage im Ratgeber «Wege zur Videoanalyse».
- EDÖB (beide Seiten), Swiss-Olympic-Merkblatt, LfDI BW, BayLDA, Art. 8 DSGVO und Horizont/RED+.

**Nicht geprüft:**
- Wortlaut von Art. 28 ZGB und DSG auf fedlex: Die Seite braucht JavaScript.
- «Informationsblatt Datenschutz aufgezeichnete Spiele» von Handball Schweiz und die verlinkten
  SHV-Vorlagen: HTTP 503 und TLS-Fehler, nur Suchtreffer gesehen.
- Der Veo-Support-Artikel «capabilities by sport»: HTTP 403.
- Wie lange die Prüfung bei einem ganzen Spiel dauert: Dafür gibt es keinen Test.
- Ob die App die Wurfposition beim Prüfen abfragt: Davon hängen die drei Dinge ab.
- Lighthouse ist nicht neu gelaufen.

## Die zehn KI-Fragen: was die Seite heute hergibt

Die Antworten stammen nur aus /llms.txt, /llms-full.txt und /de/fakten/.

| Frage | Antwort aus der Seite | Beurteilung |
|---|---|---|
| Was kostet Handball Intelligence? | Gratis ohne automatische Analyse. Team CHF 39 im Monat, Verein CHF 199 im Monat für bis zu 10 Teams, «noch nicht endgültig». | Klar und zitierbar. In llms.txt und Fakten fehlen «30 Tage gratis» und die Jahrespreise (CHF 390 / 1990), die nur auf /preise/ stehen. |
| Erkennt es Tore automatisch? | Nein, es schlägt Momente vor, du bestätigst sie. Die Anzeigetafel liest es nicht. | Klar. Es fehlt der Satz aus «So funktioniert es»: «Beantworte auch die freiwilligen Fragen, sonst kann ein Tor fehlen» (R2). |
| Brauche ich eine Kamera? | Nein, ein Handy mit Full HD, ein erhöhter Platz an der Mittellinie, eine Datei. | Klar. Der Weitwinkel (0,5×) steht in den Fakten nicht, nur im Ratgeber. |
| Wie lange dauert das Prüfen? | «ein paar Minuten» | Nicht belegt. Echttest: 6 bis 7 Minuten für 5 Minuten Spiel (R2). |
| Wie lange rechnet die Analyse? | «Das hängt von der Länge des Videos ab», danach kommt eine Mail. | Keine Zahl (R11). |
| Wo liegen die Daten? | «Vorgesehen: App und Datenbank in der Schweiz, Videos in einem Speicher in der EU», die Anbieter folgen vor dem Start. | Ehrlich, aber vorläufig. Der Einwilligungs-Ratgeber nennt Löschfristen im Präsens (R20). |
| Für welche Ligen? | «Amateur- und Nachwuchsteams, zuerst in der Schweiz» | Ungenau und widersprüchlich: Start sagt «2. bis 4. Liga», Über uns «Junioren bis 1. Liga» (R16). |
| Gibt es das auf Französisch? | «Deutsch, Französisch und Englisch» | Unklar, ob die App oder die Website gemeint ist. Englisch hat nur 3 von 10 Ratgebern. |
| Was ist der Unterschied zu Veo? | Weder Fakten noch llms.txt sagen etwas dazu. Ein Assistent findet nur über den Ratgeber «Wege»: Veo = eigene Kamera plus Abo; HI = Handy plus Bestätigen; Upload eines Veo-Download-Links geht. | Fehlt (R13). |
| Kann ich es heute schon nutzen? | Die Knöpfe sagen «Kostenlos starten». Datenstandort «vorgesehen», Anbieter «vor dem Start», Impressum ohne Betreiberin. | Widersprüchlich (R4). |

Zitierbare Einzelsätze mit Stand-Datum gibt es auf Fakten, llms.txt und allen Ratgebern. Das ist
gut gemacht.

## Befunde

Schwere: **A** blockiert Vertrauen oder ist falsch · **B** stört · **C** Kleinigkeit.

### A: blockiert Vertrauen oder ist falsch

**R1 · A · Start, /de/demo/, Preise: «Drei Dinge, so wie die App sie zeigt» stimmt nicht.**

Was ich gesehen habe:
- Start: Überschrift «Drei Dinge, so wie die App sie zeigt». Demo: «Die Zahlen sind mit demselben
  Code gerechnet wie in der App» (Bild `gegenlesen/demo-390.png`).
- Das Demo rechnet aber mit eigenem Code (`apps/site/src/lib/demo.ts`, `demoThings`):
  1. Gegentore aus der häufigsten Zone,
  2. **eigene** Tore nach Gegenstoss,
  3. **Ballverluste aus dem Spielbericht**.
- Die App (`apps/web/src/lib/three-things.ts`) kennt nur:
  1. Gegentore aus einer Zone,
  2. **Gegentore** nach Gegenstoss,
  3. eigene Tore aus einer Zone.
- Ballverluste gibt es dort nicht.
- Im Echttest entstanden nie drei Dinge: Durchlauf 1 «keine», Durchläufe 2 und 3 erwähnen sie
  nicht. Sie hängen an der Wurfzone jedes Tors.
- Preise verkauft «Automatische Analyse: drei Dinge, Szenen, Taktikkamera».

Vorschlag:
- Das Demo mit `threeThings` aus der App rechnen, oder die Sätze «so wie die App sie zeigt» und
  «mit demselben Code» streichen.
- In Titel, h1 und Preisliste «drei Dinge» erst wieder versprechen, wenn sie an einem echten Video
  entstanden sind.
- Bis dahin z. B. «Resultat, Verlauf und jedes Tor als Szene».

**R2 · A · überall (Start, So funktioniert es, Fakten, llms.txt, Hilfe, Über uns, Beschreibung der Startseite): «in ein paar Minuten bestätigen».**

Was ich gesehen habe:
- Echttest, dritter Durchlauf: 22 Fragen, «etwa 6 bis 7 Minuten» für **einen Ausschnitt von 5
  Minuten** mit 9 Toren.
- Ein Spiel hat 50 bis 60 Tore. Wie viele Fragen das ergibt, ist ungetestet; linear wären es weit
  mehr als «ein paar Minuten».
- Dazu: Echte Tore stecken in den freiwilligen Fragen. Wer bei den Pflichtfragen aufhört, sieht 2:5
  statt 4:5.
- Nur «So funktioniert es» warnt davor. Fakten, llms.txt und der Start nicht.

Vorschlag:
- «ein paar Minuten» ersetzen durch eine belegte Angabe, z. B. «Bei einem Testausschnitt von fünf
  Minuten dauerte das Prüfen 6 bis 7 Minuten; für ein ganzes Spiel messen wir es noch.»
- Oder ein ganzes Spiel testen und dann die Zahl nennen.
- Den Satz zu den freiwilligen Fragen in Fakten und llms.txt aufnehmen.

**R3 · A · Start, Demo: «8 Ballverluste · Aus dem Spielbericht».**

Was ich gesehen habe:
- Die eigene Begriffsseite (/de/ratgeber/handball-begriffe/) beschreibt den Spielbericht als
  Protokoll «mit Toren, Torschützen, Zeitstrafen und Spielzeit».
- Ein Spielbericht im Amateurbetrieb führt keine Ballverluste. Das Statistik-Manual von Handball
  Schweiz gilt für den Liveticker der oberen Ligen.
- Eine Trainerin der 3. Liga merkt das sofort.

Vorschlag:
- Das dritte Beispiel-Ding durch eines ersetzen, das die App wirklich rechnet (R1).
- Oder schreiben: «von Hand markiert».

**R4 · A · Impressum, AGB, Datenschutz, Über uns, Fakten: Gibt es das schon, und wer steht dahinter?**

Was ich gesehen habe:
- Impressum: «Die Angaben zur Betreiberfirma werden vor dem Start ergänzt.»
- Titel: «AGB (Entwurf)», «Datenschutzerklärung (Entwurf)».
- Fakten: Datenstandort «Vorgesehen».
- Über uns: kein Name, keine Firma, kein Ort (Q-SITE-3).
- Gleichzeitig steht überall «Kostenlos starten», und Preise nennt «30 Tage gratis».
- Ein Vereinspräsident, der Kinderbilder hochladen lassen soll, steigt hier aus.
- Ein Assistent kann nicht sagen, ob das Produkt verfügbar ist.

Vorschlag:
- Vor jeder Werbung für die Seite: Betreiberin und Adresse ins Impressum, die geprüften AGB und
  den Datenschutz, auf «Über uns» mindestens eine verantwortliche Person mit Funktion.
- Solange das fehlt, oben und in den Fakten einen Satz zum Stand, z. B. «Testphase: …», und die
  Knöpfe entsprechend benennen.

**R5 · A · Start («Und dazu»), So funktioniert es: «Die Taktikkamera … So siehst du, wo eine Lücke aufging.»**

Was ich gesehen habe:
- Echttest, dritter Durchlauf: Die Szene zeigt die sechs Sekunden **vor der Kandidatenzeit**. Diese
  liegt 4 bis 7 Sekunden **nach** dem Tor (Q-REC-CANDTIME). Also zeigt sie «meist den Rückweg».
- Bis 14 rote statt 7 Punkte; Zuschauer und Bank werden gezeichnet.
- «Jedes Tor als Szene» und «wo eine Lücke aufging» versprechen genau das, was der Test nicht
  zeigt.
- Die Seite sagt zwar «geschätzt» und «Spieler sicher von Zuschauern trennen: noch nicht». Das
  hebt das Versprechen aber nicht auf.

Vorschlag:
- «Lücke» streichen, bis die Szenenzeit korrigiert ist.
- In «Das noch nicht» ergänzen: «Die Szene beginnt nicht immer genau vor dem Tor.»

### B: stört

**R6 · B · Einwilligung (Ratgeber, Fakten, Daten, Vorlage, llms.txt): drei verschiedene Altersregeln.**

Was ich gesehen habe:
- Ratgeber: keine feste Grenze, urteilsfähig, «ungefähr 15» (Swiss Olympic; belegt).
- Fakten und App: «Für Kinder unter 16 entscheiden die Eltern.»
- llms.txt (Kurzantwort zum Ratgeber) und Über uns: «Für Kinder entscheiden die Eltern.»
- Vorlage: «Unterschrift (bei Kindern: Eltern)».
- Die 16 kommt aus Art. 8 DSGVO, den der Ratgeber selbst als nicht einschlägig erklärt.

Vorschlag:
- Einmal festlegen und überall gleich sagen, z. B.: «Das Gesetz kennt keine feste Grenze; in der
  App entscheiden bis 16 die Eltern, weil das einfacher ist.»
- In der Vorlage zwei Unterschriftsfelder: Jugendliche selbst und Eltern.

**R7 · B · /de/ratgeber/video-im-verein-einwilligung/: einzelne Sätze absoluter als die Quellen oder falsch zugeordnet.**

Was ich gesehen habe:
- «Informieren musst du immer» (FAQ): Swiss Olympic schreibt «grundsätzlich immer …, wenn sie
  darauf identifizierbar ist». Personen als «Beiwerk» bei öffentlichen Anlässen sind ausgenommen.
  Die Aussage stammt nicht vom EDÖB.
- «Veröffentlichen … nur mit Einwilligung»: Die Quellen lassen ein überwiegendes Interesse zu
  (Berichterstattung). «Immer» gilt nur für Werbung.
- «Im Zweifel die Einwilligung einholen» steht unter den Grundsätzen, «die der EDÖB für Vereine
  nennt». Der Satz steht aber auf der EDÖB-Seite «Umgang mit Fotos», nicht auf «Datenschutz in
  Vereinen».
- «Das steht im Zivilgesetzbuch (Art. 28 ZGB)»: Art. 28 schützt die Persönlichkeit. Das Recht am
  Bild wird daraus abgeleitet (Swiss Olympic: «durch den Persönlichkeitsschutz gemäss Art. 28 ZGB
  geregelt»).
- «Swiss Olympic weist darauf hin, dass auch eine Rückennummer jemanden erkennbar macht»: Das
  Merkblatt sagt es nur indirekt. Es verzichtet auf die Einwilligung, wenn Gesicht und «andere
  identifizierende Merkmale (inkl. Rückennummern)» nicht erkennbar sind.
- Ohne Quelle stehen: «Viele Vereine fragen bis 16 die Eltern», «Für die interne Analyse ist das
  üblich», «einfachste und sicherste Weg».
- Den Hinweis «Orientierung, keine Rechtsberatung» gibt es. Rechtsberatung wird nirgends
  behauptet.

Vorschlag:
- «grundsätzlich» bzw. «wenn jemand erkennbar ist» einfügen.
- Veröffentlichen: «am sichersten mit Einwilligung».
- Die Quellen den richtigen Seiten zuordnen.
- Die Wertungen als Rat kennzeichnen («Wir empfehlen …»).

**R8 · B · Einwilligungs-Ratgeber: Handball Schweiz regelt Aufzeichnungen schon selbst, die Seite sagt es nicht.**

Was ich gesehen habe:
- Laut einer FAQ von Handball Schweiz und RED+ (16.7.2025) gibt es ein «Informationsblatt
  Datenschutz aufgezeichnete Spiele» ab Saison 2025/26.
- Eine SHV-Mustervorlage für Aufnahmeformulare sagt sinngemäss: «Die Teilnahme am Spiel gilt als
  Einwilligung zur Aufzeichnung und Übertragung».
- Beides habe ich nur über Suchtreffer gesehen; die PDFs lieferten 503.
- Die Bau-Session hat das Blatt laut SEO.md selbst nicht gelesen.
- Ein Präsident, der das kennt, hält den Ratgeber für unvollständig.

Vorschlag:
- Die PDFs lesen. Danach einen Absatz «Was Handball Schweiz schon regelt» mit der Abgrenzung:
  Livestream der oberen Ligen gegen eigene Aufnahme des Vereins.

**R9 · B · /de/vorlagen/einwilligung/: Der Ratgeber verlangt «wo gespeichert», die Vorlage sagt es nicht.**

Was ich gesehen habe:
- Ratgeber, Schritt 2: «Erklär …, wer filmt, wer das Video sieht, wo es gespeichert ist und wann es
  gelöscht wird.»
- Die Vorlage nennt weder den Verein als Verantwortlichen noch den Dienst oder Speicherort.
- Löschfrist «Ende der Saison», die App nennt 90 Tage.
- Kein Feld für urteilsfähige Jugendliche.

Vorschlag:
- Felder [Verein], [verantwortliche Person], [Dienst und Speicherort, z. B. Handball Intelligence,
  Videos in der EU].
- Zwei Unterschriften (siehe R6).

**R10 · B · /de/ratgeber/wege-zur-videoanalyse/: Fakten fast alle belegt; zwei Fehler; wertet, obwohl er sagt, er werte nicht.**

Was ich gesehen habe:

Belegt sind (Abruf 14.11.2026):
- Kinovea, Shotcut, CapCut, Veo (Cam 3 für Handball, Kauf plus Abo).
- Dartfish «Live S» 80 € im Monat bei jährlicher Abrechnung. Die «ab 40 €» in SEO.md gehören zu
  einem anderen Paket, «360 S».
- LongoMatch (Gratis mit 50 Ereignissen, Starter 15 € / 150 €), Hudl Sportscode.
- Spiideo AutoData (Fachleute, fremde Videos, 24 h je nach Auslastung).
- Handball.ai (Selbstaussage), XPS (14 Tage), Coach Paint Lite 49 $.
- RED+ (Horizont 6.8.2025) und die Tabelle «gratis bis über 100 Euro».

Fehler:
- iMovie «läuft auf iPhone, iPad und Mac»: Der verlinkte App-Store-Eintrag ist die iOS-App. Der
  Mac braucht einen eigenen Beleg.
- Pixellot «16 Sportarten»: Die FAQ sagt 16, listet aber 14 verschiedene. Die verlinkte
  Handball-Seite nennt 11.

Wertend trotz «Wir … werten nicht»:
- Die Tabellenzeilen «Stärke» und «Grenze».
- «Das ist die Arbeitsweise vieler Profi-Analysten» (ohne Beleg).
- «Gut, wenn … Mühsam, wenn …».
- FAQ: «Ein Handy hoch an der Mittellinie reicht … aber auch».
- Die Liste «Welcher Weg passt zu dir?».
- Die Zeitangaben je Weg haben keine Quelle.
- Die eigene Spalte «ein paar Minuten» ist der günstigste Wert der Tabelle und widerspricht dem
  Echttest (R2).

Vorschlag:
- Den Mac-Link ergänzen oder «Mac» streichen. Pixellot: «laut FAQ 16 Sportarten» oder ohne Zahl.
- Den Satz «wir werten nicht» ersetzen durch «Die Spalten Stärke und Grenze sind unsere
  Einschätzung».
- Die Zeiten als Schätzung kennzeichnen.
- Die eigene Zeile mit der belegten Prüfzeit.

**R11 · B · Hilfe, Fakten, llms.txt: Keine Angabe, wie lange die Analyse rechnet.**

Was ich gesehen habe:
- «Das hängt von der Länge des Videos ab.»
- Echttest: 19 bis 27 Minuten für 5 Minuten Video, auf 4 Kernen ohne Grafikkarte. Das sagt wenig
  über den Betrieb, aber die Trainerin will wissen, ob die Mail am Samstagabend oder am Montag kommt.

Vorschlag:
- Sobald der Betrieb steht, eine Zahl: «in der Regel bis …».
- Bis dahin: «Wir nennen die Dauer, sobald wir sie im Betrieb gemessen haben.»

**R12 · B · Startseite kalt (Bild `gegenlesen/start-390.png`): In zehn Sekunden unklar, was es ist und was es kostet.**

Was ich gesehen habe:
- Über der h1 steht «Erfundenes Beispielspiel, so wie es die App zeigt».
- Die h1 lautet «Dein Spiel. Und drei Dinge zum Mitnehmen.» Das Wort Videoanalyse fehlt, und was
  ein «Ding» ist, versteht man nicht.
- Das erste Eingabefeld fragt «Wie heisst dein Team?», ohne dass klar ist, was danach passiert.
- Der Preis steht bei 390 px erst auf dem neunten von zwölf Bildschirmen («Ab CHF 39»).

Vorschlag:
- In der h1 oder direkt darunter ein Satz wie «Videoanalyse für dein Handballteam: mit dem Handy
  filmen, Tore bestätigen, Szenen und Verlauf sehen. Ab CHF 39 im Monat, 30 Tage gratis.»
- Den Hinweis «Erfundenes Beispielspiel» an das Beispiel heften, nicht über die h1.

**R13 · B · Fakten, llms.txt: Der Vergleich mit Veo und Co. fehlt dort, wo ein Assistent sucht.**

Was ich gesehen habe:
- «Unterschied zu Veo» ist eine der häufigsten Fragen. Die Antwort steht nur verstreut im Ratgeber.
- Belegt ist: Veo filmt Handball. Automatische Ereignisse nennt Veo nur für Fussball. Für Handball
  gibt es keinen Beleg, aber auch keinen ausdrücklichen Ausschluss.

Vorschlag:
- In den Fakten eine Zeile «Andere Wege»: «Kameras wie Veo oder Pixellot filmen mit eigener Kamera
  und Abo; Handball Intelligence braucht nur ein Handy und wertet Videos aus, auch einen
  Download-Link von Veo. Ob Veo Handball-Ereignisse automatisch erkennt, gibt Veo nicht an
  (Stand …).» Dazu der Link auf den Ratgeber.

**R14 · B · Länge und Wiederholung am Handy.**

Was ich gesehen habe:

Seitenhöhe bei 390 px:

| Seite | Höhe | Bildschirme |
|---|---|---|
| Start | 10'463 px | ~12 |
| Filmen-Ratgeber | 12'363 px | ~15 |
| Einwilligungs-Ratgeber | 11'373 px | ~13 |

- Der Block «Das kann es / Das noch nicht» steht wortgleich auf Start, So funktioniert es und
  Fakten.
- «Darf ich filmen?» steht in Filmen-Ratgeber, Aufnahme und Einwilligung.
- Schrift: Fliesstext 16 bis 19 px, Kontrast des grauen Lead-Texts rund 6:1. Lesbar mit Brille.

Vorschlag:
- Auf Start den Kann/Kann-nicht-Block auf drei Zeilen kürzen und auf Fakten verlinken.
- Im Filmen-Ratgeber die Abschnitte «Was du brauchst» und «Welche Einstellungen» zusammenlegen.
  Die Kurzfassung oben ist gut.

**R15 · B · Französisch (Start, Fakten, Ratgeber Filmen, Gegentore, Begriffe, Vorlage): Fachbegriffe richtig, einige Sätze aus dem Deutschen übersetzt.**

Richtig:
- ailier, arrière gauche/droit, demi-centre, pivot, gardien de but, jet de 7 mètres,
  contre-attaque, feuille de match, séance vidéo, concierge.
- Konsequent geduzt. «vous» steht nur als Plural fürs Team.

Holprig:
- «chaque but en scène» (Start, Fakten): «chaque but en séquence vidéo».
- «Touche une couleur. L'en-tête, les chiffres et les lignes la prennent.»: «Choisis une couleur :
  l'en-tête, les chiffres et les lignes s'y adaptent.»
- «tu n'as jamais besoin de pivoter» (Filmen): verwechselbar mit dem Pivot; besser «tu n'as jamais
  besoin de faire de panoramique».
- «zone de but»: Die Regeln sagen «surface de but», auf dem Feld sagt man «la zone».
- «ligne de côté»: In den Regeln heisst es «ligne de touche».
- «téléverser» ist in der Romandie unüblich: «charger la vidéo».
- «Course jusqu'à la position de tir, confirmée par toi» klingt übersetzt.
- «Interroger vos données» (Hilfe) mitten im Duz-Text.

Vorschlag: Diese Stellen ersetzen; eine Trainerin aus der Romandie einmal querlesen lassen.

### C: Kleinigkeiten

**R16 · C · Ligen.** Start: «Aktive, 2. bis 4. Liga». Über uns: «von den Junioren bis zur
1. Liga». Fakten: «Amateur- und Nachwuchsteams». *Vorschlag:* eine Formulierung, z. B. «Junioren
und Aktive von der 1. bis zur 5. Liga». Für Deutschland die Ligen nicht nach Schweizer Zählung
nennen.

**R17 · C · Über uns, «Woran wir uns halten»: «Ohne Handarbeit: Jede Seite ist nützlich, auch wenn du nichts eingetippt hast.»** Daneben steht «Paraden markierst du von Hand», und Tore werden bestätigt. *Vorschlag:* «Wenig Handarbeit».

**R18 · C · Hilfe: Aussagen, die der Echttest nicht hält.**
- «Highlights: Automatische Highlights» (/de/hilfe/highlights/, llms-full.txt): Ohne bestätigte
  Tore gibt es keine.
- «Erste Schritte»: «fragt sie dich, zum Beispiel «Wer ist das?»». Bei schwenkender Kamera wird die
  Frage laut Echttest nicht gestellt.

*Vorschlag:* «Highlights aus den bestätigten Toren»; das Beispiel «Wer ist das?» ersetzen durch
«Tor oder nicht?».

**R19 · C · Filmen-Ratgeber, Absatz «Warum beide Torräume?»** «rechnet mit geraden Linien und
entzerrt das Bild nicht selbst» ist für die Zielgruppe zu technisch. Sonst trägt der Ratgeber den
Weg (a) gut: Kurzantwort oben, Bild, Checkliste, Druckvorlage. Zum Produkt führt er unaufdringlich.
*Vorschlag:* «Die Analyse braucht die Linien beider Torräume, um das Feld zu finden. Fehlen sie,
fragt sie dich beim Prüfen.»

**R20 · C · Einwilligungs-Ratgeber, «Wie es Handball Intelligence macht»:** «Das Originalvideo
wird nach 90 Tagen gelöscht», «Wer nein sagt, erscheint nicht in Highlights» stehen im Präsens,
obwohl der Betrieb noch nicht läuft (vgl. «vorgesehen» in den Fakten). *Vorschlag:* «So ist es in
der App eingestellt: …» oder «ab dem Start».

**R21 · C · Open Graph:** Alle 122 indexierbaren Seiten haben dasselbe Bild `/og.png`. Titel und
Beschreibung sind je Seite eigen. *Vorschlag:* für die drei Ratgeber, die am meisten gesucht werden
(Filmen, Einwilligung, Wege), ein eigenes Bild.

**R22 · C · hreflang nur `de-CH`, `fr-CH`, `en`, plus `x-default` → de.** Die Verweise sind
gegenseitig und vollständig: 0 Fehler bei allen indexierbaren Seiten. Zielgruppe ist aber auch
Deutschland und Österreich. *Vorschlag:* so lassen, solange es nur eine deutsche Fassung gibt.
Es ist kein Fehler, nur ein Hinweis, falls später de-DE kommt.

**R23 · C · Hilfe-Seiten zu Funktionen ausserhalb des Kerns** (Taktiktafel, Training planen,
Präsentation, Frag deine Daten, Statistik-Matrix, Rollen, Vorbereitungsbericht, Meine Szenen):
noindex und aus dem Inhalt nicht verlinkt (0 eingehende Links), aber gebaut. *Vorschlag:* in Ordnung
so (Q-SITE-6). Sie sollten nicht aus der Hilfe-Übersicht heraus wieder sichtbar werden, solange die
Funktionen nicht zum Kern gehören.

**R24 · C · /de/vorlagen/strichliste/ druckt in Chromium auf zwei A4-Seiten**, die Seite verspricht
«ein A4-Blatt». Einwilligung und Spieltag passen auf eine Seite, fr Einwilligung ebenfalls.
*Vorschlag:* Die Notizzeilen im Druck kürzen.

**R25 · C · Englisch (Stichprobe Start):** «Tap a colour. The head, the numbers and the lines take
it on.» und «three things to take home» klingen übersetzt. Nur 3 von 10 Ratgebern sind englisch,
die Ratgeber-Übersicht verlinkt korrekt nur diese. *Vorschlag:* «Pick a colour: the header, numbers
and lines change to match.»

## Was in Ordnung ist (selbst geprüft)

- Eine h1 pro Seite, keine Sprünge in der Überschriftenfolge, alle `<img>` mit Alt-Text,
  0 tote interne Links.
- Canonical absolut und richtig. Die Weiterleitungsseiten (`/de/funktionen/`, alter Blogbeitrag)
  haben noindex mit Canonical aufs Ziel.
- Sitemap: 122 Adressen, genau die indexierbaren Seiten, keine noindex-Seite, mit hreflang und
  lastmod.
- robots.txt erlaubt alles und nennt die Sitemap.
- JSON-LD parst überall. Die Typen passen zum Inhalt (Article, FAQPage, HowTo, BreadcrumbList,
  AboutPage, SoftwareApplication mit Offer). Keine Bewertungen, nichts Erfundenes gefunden. Die
  Offer-Preise müssen mit /preise/ mitgezogen werden, solange sie «nicht endgültig» sind.
- Titel einmalig je Sprache. Gleich sind nur Seiten über Sprachen hinweg («Impressum», «Contact»,
  «Highlights»).
- Beschreibungen einmalig, ausser bei den noindex-Weiterleitungen.
- Gewicht: HTML von Start und Demo rund 210 kB, `_next` gesamt 1,3 MB. Keine Tracker, keine
  Drittanbieter.
- Handball-Fachliches:
  - Wurfquote und Torhüterquote richtig, Siebenmeter getrennt.
  - Positionen aus Sicht der Angreifer richtig erklärt.
  - Gegenstoss (CH) und Tempogegenstoss (DE) beide genannt.
  - Keinen Fehler gefunden.
- Upload per Link (Veo, Spiideo) und Übernahme der Tore aus dem Spielbericht gibt es im Code
  (`apps/api/.../videos.py`, `official_report.py`). Im Echttest waren beide nicht dabei.
