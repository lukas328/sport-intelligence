# Handball Intelligence: Logo, Feld «Dinge des Sports und Schrift»

Sechs Logo-Ideen, jede auf einer eigenen Tafel in `index.html` (im Browser öffnen): Zeichen gross,
Wortmarke, App-Icon (gross, 32 px, 16 px), einfarbig schwarz und weiss, eine echte Situation
(Hallenbanner, Homescreen, Trinkflasche, Trainerjacke) und der Satz «Das sieht man». Am Ende die
Rangfolge mit Begründung. Bilder in `shots/`, alle Logos als SVG in `logos/`.

| Nr. | Idee | Art | Schrift | Das sieht man |
|---|---|---|---|---|
| 1 | Pfosten | Wortmarke | Anton, Archivo Expanded | das Wort «handball», die zwei l sind ein rot-weisses Tor |
| 2 | Winkel | Zeichen und Wortmarke | Bricolage Grotesque | ein Handballtor von vorn, der Ball im Winkel |
| 3 | Taktik | Zeichen und Wortmarke | Archivo | ein Spielzug von der Taktiktafel: Tor, Kreis, Kreuz, Pfeil |
| 4 | Sucher | Zeichen und Wortmarke | Sora | ein Ball im Sucher einer Kamera, die aufnimmt |
| 5 | Skript | Wortmarke | Yellowtail, Archivo Expanded | der Schriftzug «Handball» wie auf einem Trikot, mit Schwung |
| 6 | Time-out | Zeichen und Wortmarke | Rubik | die grüne Time-out-Karte mit dem T |

**Rangfolge:** 1 Time-out, 2 Pfosten, 3 Skript, 4 Winkel, 5 Taktik, 6 Sucher. Begründung in
`index.html` und `shots/rangfolge.jpg`. Nach drei Runden ausgeschieden: Wurf (Ball mit
Tempostrichen), ersetzt durch Time-out.

## Dateien

- `logos/<idee>-zeichen.svg`, `-wortmarke.svg`, `-einfarbig-schwarz.svg`, `-einfarbig-weiss.svg`,
  `-app-icon.svg`. Alle Schrift ist in Pfade umgewandelt; die SVGs brauchen keine Schrift.
- `fonts/`: die verwendeten Schriften, alle SIL Open Font License, von Google Fonts.
- `build.js` erzeugt Logos und Seite: `npm i opentype.js@1.3.4`, dann
  `node docs/design/brand2/dinge/build.js`. `shots.js` rendert die Tafeln mit Playwright.
- `rangfolge.html` ist der Text der Rangfolge, den `build.js` in die Seite setzt.

## Abgrenzung

Nicht verwendet: schräges H, Linie mit Punkt, HI-Block, Feld als H (die verworfene erste Runde),
Gehirn, Schaltkreis, Funkeln, Auge, Wett-Look. Die Verbandszeichen (IHF, EHF, HBL, DHB, Swiss
Handball) habe ich in dieser Runde nicht im Netz nachgeprüft. Aus dem Gedächtnis arbeiten die
meisten mit Ball, Schriftzug oder Hoheitszeichen. Darum ist hier der Ball nie die Hauptform: Bei
Winkel und Sucher steht er in einem Tor oder Sucher. Eine Prüfung gegen die echten Zeichen und eine
Markenrecherche stehen vor einem Entscheid noch aus.
