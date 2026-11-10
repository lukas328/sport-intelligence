# UX-Assessment und Zielbild

Stand: 10. November 2026. Grundlage: alle 66 Screens in `docs/screens` (Desktop 1440 px und Phone
390 px), `docs/DESIGN.md`, `apps/web/src/lib/nav-model.ts`. Diese Datei hält die Befunde pro
Screen fest. Wie es künftig aussieht, steht in `SPEC.md` (verbindlich) und `zielbild.html` (das
Bild dazu); wo der Abschnitt «Zielbild» unten davon abweicht, gilt die Spezifikation. Nichts
davon ist umgesetzt.

## Kurzfassung

Die App hat nicht zu viele Funktionen. Sie hat drei Strukturprobleme und ein Gestaltungsproblem:

1. **Sie zeigt die Maschine statt das Ergebnis.** Versprochen ist «alles andere passiert
   automatisch». Die Spielseite beginnt mit vier Pflichtschritten und neun Reitern.
2. **Sie ist nach Ablage sortiert, nicht nach der Woche des Trainers.** Wichtige Seiten haben
   keinen Navigationspunkt, andere gibt es doppelt.
3. **Sie benutzt mehrere Wörter für dasselbe Ding.** Jedes Wort klingt nach einer eigenen Funktion.
4. **Sie erklärt in Text, was sie in Bild zeigen müsste.** In 66 Screens gibt es kein
   Vorschaubild in einer Liste. Dazu kommt eine Identität aus einem einzigen Motiv (roter Block
   mit Kreisbogen) und Sätze aus der Schablone.

## Befunde pro Bereich

### Einstieg (9 Screens)

- Anmeldung und Onboarding sind blau, die App ist danach in Vereinsfarbe. Der Moment, in dem die
  App zum eigenen Verein wird (Farbe, Wappen), findet nicht statt.
- Vier Schritte, obwohl handball.ch laut eigenem Text «Spielplan, Resultate und Kader» liefert.
  Schritt 3 (Kader von Hand oder CSV) ist dann überflüssig.
- Schritt 4 lädt einzeln per E-Mail ein. Amateurteams leben im Teamchat: es fehlt ein Link und
  ein QR-Code.
- Nach Schritt 4 landet man auf «Zum Team», nicht beim ersten Video. Der Kern des Produkts kommt
  im Einstieg nicht vor.

### Trainer: Übersicht

- Die Bühne nimmt 480 px und sagt «Deutlich gewonnen gegen TSV Demo-Thalwil.» neben 26:18. Das
  Spiel ist acht Tage her, heute ist Training um 19:00 mit 0 Übungen und zwei Ausfällen. Das
  steht ganz unten.
- «Was auffällt: Für dieses Spiel gibt es noch keine Erkenntnisse.» ist die wichtigste Stelle der
  App und leer.
- «Frag deine Daten» steht zweimal auf derselben Seite.
- Darüber liegt auf allen 42 Trainer-Screens das 2FA-Banner.

### Trainer: Spiele und Spielseite

- Spielliste: gut lesbar, aber ohne Bild. «Matchbogen fotografieren» und «Datei importieren»
  stehen als Nebenlinks unter dem Titel.
- «Spiel anlegen» enthält einen Umschalter «Spiel | Training» und fünf Trikotfarben. Zu viel für
  den Moment; Farben gehören ans Team mit Ausnahme pro Spiel.
- Spielseite: roter Kopf (265 px) auf jedem Reiter, dann Video · Analyse · Szenen, dann im Video
  neun Unterreiter (vier nummerierte Schritte plus Ereignisse, Würfe, Abwehrsysteme, Kommentare,
  Feedback). Der letzte ist abgeschnitten.
- «Anwurf fehlt» steht dreimal auf einem Screen.
- «Spieler zuordnen»: 36 Dropdowns «Person 9 · 60 s im Bild» ohne Bild der Person.
- Unter dem Video ein nackter Balken. Es gibt keine Zeitleiste mit Ereignissen.
- Analyse: «Den Ball erkennt die Videoanalyse noch nicht.» Laufleistung hat die Überschrift «…».
- Szenen: der Reiter enthält «Reels» und «Markiert während des Spiels», keine Szenen.
- Acht Wege für dieselben Daten: Videoanalyse, Matchbericht per Link, Abgleich handball.ch,
  Matchbogen-Foto, Datei-Import, Live erfassen, Am Spielfeldrand markieren, Ereignisse von Hand.
- **Gut:** «Würfe prüfen» im Vollbild (eine Frage, Tastenkürzel) und «Markieren» mit sechs Tasten.
  Das ist das Muster für alle Korrekturen.

### Trainer: Saison, Matrix, Assistent, Bibliothek

- Saison: Bühne «Mehr Siege als Niederlagen.» Darunter Wurfquote «–», Paradenquote «–» und als
  Bestwert «Wenigste Ballverluste: 0». Fehlende Daten erscheinen als Rekord. Die Tabelle «Alle
  Spiele im Detail» besteht aus Strichen.
- Matrix und «Frag deine Daten» sind nur über Knöpfe in der Saison-Bühne erreichbar. Beide
  beantworten dieselbe Art Frage wie die Szenensuche.
- Bibliothek: ein Link zur Szenensuche und zwei Listen. Playlist und Präsentation sind fast
  dasselbe; eine Aufgabe (Training › Aufgaben) ist eine Playlist mit Empfänger und Datum.
- Playlist-Detail: «Playlist löschen» ist der einzige farbige Knopf.

### Trainer: Training

- Planung: 78 Einheiten als Textzeilen (10 nächste, 58 weitere, 10 vergangene), jede mit PDF,
  Bearbeiten, Anwesenheit, Löschen. Das Saison-Setup (Trainingszeiten, Feiertage, «Einheiten
  erzeugen») steht dauerhaft über der Liste. Alle Einheiten sind «noch leer».
- Übungen: Aufbau und «Worauf achten» ausgeschrieben in der Liste. Innerhalb von Training gibt es
  ein zweites «Bibliothek».
- Spielzüge: die Skizzen sind das Schönste in der App.
- Aufgaben: Formular rechts, leere Liste links mit einem Satz aus Spielersicht («die dir der
  Trainer gibt»).

### Trainer: Team, Einstellungen

- Kader: zuerst ein Absatz mit 14 Namen ohne Einwilligung, dann die Mannschaft. Die Matrix mit
  70 mal «fehlt» ist zum Glück eingeklappt.
- Termine: für die Trainerin leer («Keine Termine in den nächsten 30 Tagen»), während die
  Spielerin zehn sieht. Bitte prüfen, das sieht nach einem Fehler aus.
- Abgleich mit handball.ch und Beitrittsanfragen haben keinen Navigationspunkt.
- Einstellungen: eine Seite, 3355 px am Desktop, 4737 px am Phone. Vereinsfarbe, Abo, Rechnung,
  Mitglieder, Passwort, Geräte, 2FA, «Verein löschen». «Konto» und «Daten und Konto» sind zwei
  Abschnitte.
- Personen verwaltet man an vier Orten: Kader, Einstellungen › Personen, Beitrittsanfragen,
  Abgleich.

### Spielerin, Eltern

- Spieler-Übersicht: richtig gedacht (nächster Termin, zwei Knöpfe). Dann «9 Termine beantworten»,
  dann dieselben Knöpfe dreimal, auf «Termine» zehnmal. Bei festen Trainings sollte Dabeisein der
  Normalfall sein.
- Die Spielerin sieht die Spielseite mit denselben drei Reitern wie der Trainer.
- Sidebar zeigt `player-179429520121…` als zweite Zeile unter dem Namen.
- Eltern: Navigation nur «Übersicht», obwohl Termine, Einwilligungen und Szenen existieren.
  Einwilligung ist die wichtigste Handlung dieser Rolle und liegt im Kontomenü.

### Öffentlich

- Der Screenshot «Verband» zeigt die Anmeldeseite (Weiterleitung). Der Lauf in
  `apps/web/screens/capture.spec.ts` sollte das abfangen.

## Zielbild

### Der Faden

Ein Trainer öffnet die App zwischen zwei Spielen etwa sechsmal: Spieltag, Hochladen, Drei Dinge,
Besprechung, Training, nächster Gegner. «Heute» zeigt genau eine Karte für den aktuellen Moment,
darunter «Offen».

### Navigation

| Rolle | Heute | Neu |
|---|---|---|
| Trainer, Analyst, Teammanager, Admin | Übersicht · Spiele · Training · Team | Heute · Spiele · Szenen · Training · Team |
| Spieler, Torhüter | Übersicht · Szenen · Termine · Team | Heute · Szenen · Termine · Team |
| Eltern | Übersicht (· Termine · Team) | Heute · Termine · Kind |

- **Offen** (Sammelstelle, Zähler in der Navigation): Prüfen-Fragen, Beitrittsanfragen, Konflikte
  aus dem Abgleich, fehlende Einwilligungen, 2FA, erste Schritte.
- **Spiele:** Liste mit Standbild oder Minifeld; Ansichten Saison und Gegner.
- **Spielseite:** Anzeigetafel (kompakt, bleibt stehen), Reiter Spiel · Video · Zahlen, «Prüfen n»
  nur wenn etwas offen ist. Vor dem Spiel ist die Seite eine Vorbereitung (Gegner, wer ist da,
  «Spieltag starten»).
- **Prüfen:** eine Warteschlange im Vollbild für Spielfeld, Anwurf, Tore, Würfe, Personen. Eine
  Frage pro Bildschirm, wahrscheinlichste Antwort zuerst, jederzeit abbrechbar.
- **Szenen:** Suchfeld für Filter und Fragen (ersetzt Szenensuche, Matrix, Assistent),
  Besprechungen, Highlights.
- **Training:** Wochenansicht; Trainingszeiten einmalig im Dialog; Baukasten aus Übungen und
  Spielzügen als Bildkacheln.
- **Team:** Personen, Einladung per Link und QR, Einwilligung als Zeichen pro Person und Filter.
- **Ich** und **Verein** statt einer Einstellungsseite.

### Ein Wort pro Ding

| Bisher | Künftig |
|---|---|
| Szene, Clip, Reel, Markierung | Szene |
| Reel, Highlight | Highlights (der automatische Zusammenschnitt) |
| Matchbogen, Matchblatt, Matchbericht, Spielbericht | Spielbericht |
| Playlist, Präsentation, Folien, Aufgabe | Besprechung (Arbeitstitel) |
| Live erfassen, Am Spielfeldrand markieren | Spieltag |
| Frag deine Daten, Statistik-Matrix, Szenensuche | Suchen |
| Übersicht | Heute |
| Einheit | Training |

### Gestaltung

1. Bild vor Text: jede Zeile mit Video zeigt Standbild oder Minifeld (aus den Positionsdaten,
   braucht keine Bild-Einwilligung).
2. Ergebnis vor Maschine: Unsicheres wandert in «Prüfen», eine Quellenzeile pro Spiel statt
   Fussnoten an jeder Zahl.
3. Die Vereinsfarbe ist das Trikot, nicht die Tapete: Wappen, Rückennummern, aktiver Reiter,
   eigene Punkte im Feld. Papier neutral, Knöpfe in Tinte (Variante A aus
   `docs/design/identity/FOR_LUKAS.md`, Punkt 8).
4. Die Anzeigetafel: Resultate und Uhrzeiten als LED-Ziffern auf dunklem Grund, das eine laute
   Element.
5. Handschrift gehört dem Trainer: nur echte Notizen von Menschen. Automatische Aussagen sind
   konkret («9 von 18 Gegentoren über rechts aussen») oder fehlen.
6. Video ist dunkel, Arbeit ist hell.

## Raus, zusammen, neu

**Raus oder parken:** Bühne mit Schablonensatz; Erklärsätze unter Seitentiteln; Termine als
Trainerseite; Laufleistung-Reiter ohne Daten; Fernbedienung, MP4-Export und Offline für
Präsentationen (ins Menü); öffentliches Profil und Verbandsseiten; Torhüter-Modul als Zusatzpreis;
Kader-Schritt im Einstieg, wenn handball.ch liefert.

**Zusammenlegen:** Playlists + Präsentationen + Aufgaben; Szenensuche + Matrix + Assistent;
Live erfassen + Markieren; vier Importwege; vier Einrichtungsschritte + Würfe + Ereignisse;
Checkliste + Banner + Anfragen + Abgleich; Übungen + Spielzüge; Kommentare + Clips + Zeichnungen
+ Feedback.

**Fehlt:** Zeitleiste unter dem Video; Vorschaubilder; eine volle Demo (Seed mit Erkenntnissen,
Würfen, Szenen); Einladungslink und QR; Mitteilungen aufs Handy; «So filmst du richtig»; Verlauf
eines Themas über mehrere Spiele; Abwesenheit von bis durch die Spielerin.

## Reihenfolge

| Etappe | Inhalt |
|---|---|
| 0 Aufräumen | Wörter in de, fr, en vereinheitlichen. Erklärsätze streichen. Papier neutral, Knöpfe in Tinte, Löschen nie als Hauptknopf. Demo-Verein füllen, leere Kennzahlen nicht als Bestwert. |
| 1 Rahmen | Fünf Ziele, «Heute» mit sechs Momenten, «Offen». Neue Tokens, Schrift, Anzeigetafel, Wappen. Einstellungen teilen. |
| 2 Spielseite | Spiel · Video · Zahlen, Prüfen, Zeitleiste, Minifeld. Spieltag als ein Werkzeug, Spielbericht als ein Dialog. |
| 3 Szenen | Suchfeld für Filter und Fragen. Besprechung ersetzt Playlists, Präsentationen, Aufgaben. |
| 4 Rundherum | Training als Woche mit Baukasten, Team mit Einladungslink, Spieler und Eltern, Einstieg in zwei Schritten. |

`docs/DESIGN.md` und ADR 023/024 beschreiben den heutigen Stand (vier Ziele, Bühne). Sie werden
mit Etappe 1 angepasst, nicht vorher.

## Offene Entscheide

1. **Umfang:** Videoanalyse zuerst; Teamverwaltung nur Kader und Zusagen. Empfehlung: ja.
2. **Fünf Ziele statt vier** für Trainer, «Szenen» oben. Empfehlung: ja.
3. **Wörter:** Szene, Besprechung, Spieltag, Spielbericht. «Besprechung» mit zwei Trainern prüfen.
4. **Standbilder** teamintern bei vorhandener Einwilligung «Videoanalyse im Team», sonst Minifeld.
   Empfehlung: Minifeld als Standard.
