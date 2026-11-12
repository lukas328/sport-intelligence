# Website: Bestand (12. November 2026)

Angesehen: `apps/site` auf Stand `f78f8e8`, lokal gebaut (`pnpm --filter @handball/site build`,
statisch aus `out/`), alle Seitentypen auf Deutsch bei 1280 und 390 px. Bilder in
`shots/bestand/`.

## Aufbau, der bleibt

- Next.js 15, statischer Export (`output: "export"`), keine Cookies, nichts von Dritten.
- Drei Sprachen unter `/de/`, `/fr/`, `/en/`, Texte in `src/messages/{de,fr,en}.ts` mit Test auf
  gleiche Schlüssel und Platzhalter, `/` wählt die Browsersprache.
- Inhalte als MDX: Hilfe (19 Artikel × 3 Sprachen), Blog (2 Beiträge), Rechtliches (AGB,
  Datenschutz, Impressum, als Entwurf gekennzeichnet).
- Preise aus `@handball/plans` (generiert aus der Plantabelle der API, CI prüft).
- Links in die App über `NEXT_PUBLIC_APP_URL` (`/register?lang=`, `/login?lang=`).
- Die App verlinkt Hilfeartikel über `apps/web/src/components/support/help-map.ts`: diese 17
  Adressen müssen bestehen bleiben (Test in `content.test.ts`).
- Sitemap, robots, kanonische Adressen und Sprachalternativen, JSON-LD.

## Bewertung

| Seite | Was gut ist | Was weg muss |
|---|---|---|
| Start | ehrlicher Ton («Ehrliche Zahlen»), klare zwei Wege | verkauft den alten Umfang: «Für den ganzen Verein», Rollen bis zu den Eltern, Präsentation mit Fernbedienung, Tags. Kein Bild vom Produkt. Weiche Karten mit Schatten, Pillen-Knöpfe in Orange: Baukasten-Look. «Gratis-Plan für immer» ist ohne Analyse, das sagt die Seite nicht |
| Funktionen | | zehn Kacheln mit Live-Erfassung, Vorbereitungsbericht, Taktiktafel, elf Rollen, xG: der alte, breite Umfang. Fällt weg |
| Preise | Zahlen aus der Plantabelle, QR-Rechnung, Fair Use, Fragen zur Testphase | Merkmalslisten mit Assistent, Taktiktafel, PDF-Berichten; «Free» ohne Hinweis, dass dort nichts analysiert wird |
| Beispielanalyse | erfundenes Spiel, sichtbar so gekennzeichnet, Zahlen mit dem echten Kennzahlen-Code | sieht nicht aus wie die App: Wurfbild in Bunt, xG, Filter-Selects. Kein Kopf, keine drei Dinge, keine Szene |
| Hilfe | Suche, Gruppen, viele Antworten | Artikel zum alten Umfang (Training, Taktiktafel, Assistent, Präsentation, Rollen); Wörter vor dem neuen Vokabular (Erkenntnisse, Ereignisse, Playlist). «Erste Schritte» lädt Spieler ein und erfasst Kader per CSV |
| Aufnahmeanleitung | knapp, praktisch, Aushang zum Drucken | kein Bild, wo die Kamera steht; sagt «nicht schwenken» ohne zu sagen, was beim Schwenken passiert |
| Blog | zwei echte Beiträge, beide passen zum Kern (Filmen, Unsicherheit) | erwähnt xG |
| Kontakt | E-Mail, Antwortzeit | keine Antwort auf «wer seid ihr?» |
| AGB, Datenschutz, Impressum | sauber als Entwurf markiert, Firma per Build-Variable | bleibt so (Lukas entscheidet) |

## Was fehlt

- Ein Bild davon, was man bekommt: die drei Dinge, die Szenen, die Taktikkamera.
- Eine Seite für Eltern und Spieler: was mit dem Video passiert, wie die Einwilligung geht.
- Eine einfache Antwort auf «reicht mein Handy, wo stelle ich es hin, welche Datei?».
- Was die Analyse heute kann und was nicht, offen auf der Seite, nicht nur im Blog.

## Technisch

- Schrift Archivo, Akzent Orange `#c93a0b`, runde Ecken: nicht die Welt der App (Anlauf: Stoff,
  Kanit schräg, Hanken Grotesk, keine Rundungen).
- Textgrössen 14 bis 16 px für Fliesstext, Navigation 14 px: zu klein für die Leitperson.
- Lighthouse laut README 92 bis 98 / 100 / 96 / 100; das soll so bleiben.
