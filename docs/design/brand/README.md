# Marke Handball Intelligence

Stand 12. November 2026. **Entscheid offen.** Der Name ist «Handball Intelligence»; «Handball AI»
fällt weg (auch weil es «handball.ai» als Analyseplattform schon gibt). An `apps/` ist nichts
geändert.

`index.html` im Browser öffnen: der ganze Weg auf einer Seite. Bilder in `shots/`, alle Zeichen
als SVG in `logos/`.

## Prozess

1. **Grundlage:** für wen (Trainerinnen im Amateurhandball), was die Marke verspricht (drei Dinge
   aus dem Video, die stimmen), drei Eigenschaften (genau, zur Hand, zurückhaltend), was sie nicht
   sein soll (Wettanbieter, Tech-Startup, Verbandslogo), Umgang mit dem Namen (Schreibweise,
   Kurzform «HI», zweizeilig, de/fr/en ohne Übersetzung).
2. **Umfeld:** IHF, EHF, HBL, Schweizerischer Handball-Verband, handball.ai, Analysewerkzeuge,
   Wettanbieter; was ihre Zeichen ausmacht und wovon wir Abstand halten. Keine rechtliche
   Markenprüfung.
3. **Skizzenbogen:** 22 Skizzen, fünf gehen weiter, bei jeder verworfenen der Grund.
4. **Fünf Richtungen**, je mit Zeichen auf dem Raster, Wortmarke, Kombinationen (quer,
   zweizeilig, gestapelt, nur Zeichen), App-Icon iOS und Android, Favicon 16 und 32 px in
   Originalgrösse, im Kopf der App (Desktop, Handy, Anmeldung), auf der Vorschau eines geteilten
   Links, einfarbig schwarz und weiss, auf sechs Vereinsfarben, auf T-Shirt und Kleber:
   1. **Anlauf**: ein Tor, wie die App es zeichnet; Lauf, Wurfposition, Strich ins Tor.
   2. **Feld**: das Handballfeld von oben als H, Torraumbögen oben und unten.
   3. **Keil**: der Block mit der Wurf-Schräge, «HI» ausgestanzt.
   4. **Rückennummer**: «HI» mit zwei versetzten Konturen.
   5. **H im Lauf** (eigene Idee): ein schräges H, dessen Querstrich ein Anlauf ist und als
      Wurfposition vor dem rechten Stamm endet.
5. **Bewertung** als Tabelle (sieben Kriterien), dazu die Frage der Farbe.
6. **Zwei Durchgänge als Art Director** (generiert oder beliebig? würde ein Verein es auf einen
   Kleber drucken?) und was sich danach geändert hat.
7. **Empfehlung:** H im Lauf. Zweite Wahl: Feld. Anlauf bleibt als Bildsprache.

## Farbe

Keine eigene Markenfarbe. Feste Fassung: Tinte `#16171a` auf Stoff `#eceae5` (und umgekehrt fürs
Icon). In der App darf das Zeichen die Vereinsfarbe des angemeldeten Teams annehmen; auf der
Website darf es durch Vereinsfarben wechseln, aber nie als einzige Fassung.

## Dateien

| Pfad | Inhalt |
|---|---|
| `index.html` | die Seite mit dem ganzen Prozess |
| `logos/<richtung>-zeichen.svg`, `-zeichen-weiss.svg` | das Zeichen, Raster 48 |
| `logos/<richtung>-quer.svg`, `-zweizeilig.svg`, `-gestapelt.svg` | Zeichen mit Wortmarke (Schrift in Pfaden) |
| `logos/<richtung>-app-icon.svg`, `-favicon.svg` | Vorlagen für Icon und Favicon |
| `shots/` | `seite.jpg`, `skizzen.jpg`, `richtung-1.jpg` bis `richtung-5.jpg` |
| `src/marks.py`, `src/page.py`, `src/build.py` | Geometrie, Seite, Build (`pip install fonttools uharfbuzz`, dann `python3 docs/design/brand/src/build.py`) |
| `src/fonts/` | Kanit (SIL OFL, mit `OFL.txt`) für die Wortmarken |

`<richtung>`: `anlauf`, `feld`, `keil`, `nummer`, `hlauf`.

## Nächste Schritte

1. Entscheid zwischen H im Lauf und Feld (oder Feld mit schrägen Stämmen).
2. Feinschliff mit eigenen Zeichnungen für 16, 24, 32 und 512 px, Schutzzone, Mindestgrösse.
3. Marken- und Domainprüfung durch eine Fachperson.
4. Dateien: PNG für iOS und Android, favicon.ico, Open-Graph-Bild, ein Blatt Markenregeln.
5. Umbenennung in der App in einer eigenen Session (Texte, Titel, Manifest, E-Mails, Stores).
