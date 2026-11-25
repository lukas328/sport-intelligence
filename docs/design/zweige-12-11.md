# Drei Design-Zweige vom 12. November 2026

Stand: 25. November 2026, verglichen mit `main` (Commit `7c062322`).

Die drei Zweige enthalten nur Entwürfe in `docs/design/`: Logo-Ideen, Skizzen für das Aussehen der
App, Bilder und Schriften dazu. Am Code der App, der Website oder der API ändern sie nichts. Seit
dem 12. November sind auf `main` zwei Entscheide gefallen, die fast alles davon erledigen:

- **Logo:** «Taktik» ist gewählt und in App, Website und Handy-App eingebaut (seit dem
  17. November nur noch in einer Farbe, Entscheid E10). Regeln in `docs/design/brand2/taktik/README.md`.
- **Aussehen der App:** die Richtung «Anlauf» ist gewählt und gebaut (`docs/design/ux-reset/`,
  in der App unter anderem `lib/color.ts` mit Vereinsfarbe, Gegnerfarbe und Kollisionsregel).

Übernommen wurde darum nichts. Alles Brauchbare ist schon auf `main` oder in Anlauf aufgegangen.

## Zweig `claude/trikot-zielbild` (8 Commits)

| Commit | Inhalt | Entscheid |
|---|---|---|
| `028f68fe`, `c1bd118f` | Runde 2 Aussehen: «Flutlicht» (dunkle Halle, Anzeigetafel) und «Plakat» (zwei Farbfelder, riesige Zahl) | veraltet, weil Anlauf gewählt ist. Beide sind als Voreinstellung im Mischpult (`docs/design/ux-reset/mischpult/`) gelandet, von dort ging das Beste in Anlauf. |
| `1dfc844b` | Runde 4 Aussehen: «Linie» (der Spielverlauf als breite Linie) und «Hallenlicht» (Hallenboden mit Licht, Taktiktafel) | veraltet, weil Anlauf gewählt ist. Der Verlauf als Linie steht heute im Wurf-Kopf, Hallenlicht ist im Mischpult und in der Anlauf-Skizze (`runde5/anlauf/`). |
| `7906271a` | Sechs Logo-Ideen «Dinge des Sports»: Pfosten, Winkel, Taktik, Sucher, Skript, Time-out | verworfen, ausser Taktik. Taktik ist das gewählte Logo. |
| `e52e0925`, `d429b480`, `1c50311c`, `5bc3def6` | Taktik ausgearbeitet: zehn Varianten, Wahl v06, alle Dateien, Teilen-Bild | schon auf main als `docs/design/brand2/taktik/` (unverändert übernommen am 12. November, seither weiterentwickelt: eine Farbe, Teilen-Bild je Sprache, `publish.js`). |

Kurz: Das Logo aus diesem Zweig ist längst auf `main`, der Rest sind überholte Skizzen.
**Zweig kann gelöscht werden.**

## Zweig `claude/design-runde2-sport` (4 Commits)

| Commit | Inhalt | Entscheid |
|---|---|---|
| `0d9a1b15`, `3d0f4175` | Runde 2 Aussehen: «Sendung» (Fernsehgrafik, Endstand-Tafel, Laufband) und «Wurf» (alles lehnt nach vorn, Resultat mit Echo) | veraltet, weil Anlauf gewählt ist. Von «Wurf» lebt in Anlauf weiter: schräge Titel, das Resultat mit zwei versetzten Umrissen, der Verlauf als Linie im Kopf. «Sendung» ist nicht weiterverfolgt worden. |
| `304e2ec6` | Runde 4 Aussehen: «Profil» (gezeichnete Köpfe der Spielerinnen) und «Schal» (gestricktes Resultat in Vereinsfarben) | veraltet, weil Anlauf gewählt ist. Aus «Profil» blieb im Mischpult die Regel «Nummern und Vornamen, keine Gesichter». |
| `668e65bf` | Sechs Logo-Ideen «mit Charakter»: Fuchs, Abklatschen, hi, Murmeli, Wimpel, Harzabdruck | verworfen, weil Taktik gewählt ist. |

Kurz: Alles hier ist Vorarbeit für Entscheide, die gefallen sind. Die Skizzen zeigen ausserdem noch
Vereine mit echten Ortsnamen, die es auf `main` nicht mehr gibt.
**Zweig kann gelöscht werden.**

## Zweig `claude/design-runde2-video` (2 Commits)

| Commit | Inhalt | Entscheid |
|---|---|---|
| `b0ef3ef7` | Erste Logo-Runde: Grundlage der Marke, Umfeld, 22 Skizzen, fünf Richtungen (Anlauf, Feld, Keil, Rückennummer, H im Lauf), Bewertung | verworfen, weil Taktik gewählt ist. Der Name «Handball Intelligence» und der Abstand zu handball.ai stehen auf main (Q-PROD-1, `docs/PLAN.md`). Die Grundsätze der Marke sind im Taktik-Logo eingehalten (siehe unten). |
| `836441ca` | Runde 2 davon: acht Fassungen von «H im Lauf», Empfehlung Fassung G, Pixel-Favicons | verworfen, weil Taktik gewählt ist. Favicons und Regeln für kleine Grössen hat Taktik eigene. |

Kurz: Das ist die erste Logo-Runde, die schon in der zweiten Runde verworfen wurde («Nicht
verwendet: schräges H, Feld als H» in den späteren Ideen).
**Zweig kann gelöscht werden.**

## Was davon in Worten bleibt

Die Grundlage der Marke aus der ersten Logo-Runde stand nirgends als Entscheid, passt aber zu
allem, was seither gebaut ist. Zum Nachlesen, falls sie wieder gebraucht wird:

- **Für wen:** Trainerinnen und Trainer im Amateurhandball.
- **Versprechen:** Aus dem Video eines Spiels werden drei Dinge, die stimmen, und die Szenen dazu.
  Gezeigt wird nur, was gemessen ist.
- **Drei Eigenschaften:** genau (jede Linie ein gemessener Weg), zur Hand (nah an der Halle, nicht
  am Labor), zurückhaltend (die Farben gehören den Teams).
- **Was sie nicht sein soll:** Wettanbieter (kein Schwarz-Gelb, keine Leuchtfarbe, kein Blitz),
  Tech-Startup (kein Netz aus Punkten, kein Gehirn, kein Auge, kein «AI» im Zeichen), Verbandslogo
  (kein Wappen, kein Ball mit Nähten, kein Rot-Weiss, kein Kreuz).

Die Bilder und Skizzen der drei Zweige gehen mit dem Löschen verloren. Gebraucht werden sie nicht:
Die Entscheide und ihre Begründung stehen in `docs/design/brand2/taktik/README.md` und
`docs/design/ux-reset/README.md`.
