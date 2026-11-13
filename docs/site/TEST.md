# Website: Test (12./13. November 2026, Nachtrag Team-Feld am 13. November)

Geprüft: statischer Export von `apps/site` (`pnpm --filter @handball/site build`), ausgeliefert
mit einem komprimierenden Server (`npx serve out`), alle Seiten in de, fr, en. Bilder in
`shots/` (Desktop 1280, Handy 390, ganze Seite), Übersicht in `shots/bogen.jpg`, der alte Stand
in `shots/bestand/`.

## Ergebnisse

| Prüfung | Ergebnis |
|---|---|
| `pnpm lint`, `pnpm typecheck`, `pnpm test` (18 Tests) | sauber |
| axe 4.10 (WCAG 2.0 bis 2.2 A/AA, best practice), 45 Seiten bei 390 und 1280 | 0 Verstösse |
| Kein waagrechter Überlauf bei 320, 390, 768, 1280 (320 = 400 % Zoom) | 45 von 45 Seiten |
| Grosse Systemschrift (Grundschrift 150 %) bei 390, 16 Seiten | kein Überlauf; Kopfzeile bricht um, Resultat passt sich an |
| Text unter 16 px (sichtbar, ausserhalb von Grafiken) | keiner |
| Ziele unter 44 px (Links ausserhalb von Fliesstext, Knöpfe, Felder) | keines; Knöpfe 56 px, Links 48 px |
| Interne Links (92 verschiedene) | alle 200; Links in die App (`/register`, `/login` mit `?lang=`) nicht abgerufen |
| Tastatur | Reihenfolge Sprunglink, Logo, Navigation, Anmelden, Starten, Inhalt; Fokus überall sichtbar (3 px); Farbwahl mit Pfeiltasten; «Menü» mit Enter; die drei Dinge im Demo als Knöpfe mit `aria-pressed` |
| `prefers-reduced-motion` | Taktikkamera steht auf dem letzten Bild mit «Abspielen», Bündel sofort gezeichnet |
| Lighthouse 12 (Handy, simuliert gedrosselt) | Start mit Team-Feld 96 / 100 / 100 / 100 (de und fr), Demo 98 / 100 / 100 / 100, So funktioniert es (en) 99 / 100 / 100 / 100, Filmen (fr) 98 / 100 / 100 / 100 (Leistung / Barrierefreiheit / Best Practices / SEO); LCP 2.1 bis 2.8 s, CLS 0 |
| Metadaten | Titel, Beschreibung, kanonische Adresse und Sprachalternativen pro Seite; Open-Graph-Bild aus `brand2/taktik/final/open-graph.png`; Sitemap mit 25 Adressen (nicht gelistete Hilfe und `/funktionen/` ausgenommen, beide `noindex`); `/funktionen/` leitet weiter |

Ohne komprimierenden Server (Python `http.server`) fällt die Leistung auf 85: die Seiten sind
ungepackt bis 200 KB gross. Jeder übliche Webserver oder CDN packt; das ist kein Fehler der Site.

## Hans, 58, am Handy

| Schritt | Was er sieht | Hängt er? |
|---|---|---|
| Seite öffnen | Logo, «Menü», im blauen Kopf «Dein Spiel. Und drei Dinge zum Mitnehmen.», der Satz «Du filmst das Spiel mit dem Handy …» und, noch im ersten Bildschirm, «Wie heisst dein Team?» mit «Zeigen» | Nein. In zehn Sekunden klar: filmen, hochladen, drei Dinge. Er tippt seinen Teamnamen und landet in der App bei seinem Team, ohne Konto (die Seite `/einstieg` baut die App). |
| Weiter nach unten | zwei grosse Knöpfe, «30 Tage alles gratis, ohne Kreditkarte», dann «Welche Farbe trägt dein Team?» | Die Farbwahl macht Spass und zeigt sofort, dass es um sein Team geht. |
| Drei Dinge | «5 von 24 Gegentore aus dem Rückraum rechts», mit Anläufen | Die Zahl mit Basis versteht er. Die Linien brauchen die Legende darunter. **War ein Hänger:** «5 Szenen» sah aus wie ein Knopf und tat nichts. Jetzt führt es ins Demo-Spiel. |
| Taktikkamera | spielt, mit «Pause» | Versteht «von oben». Der Satz «Den Ball erkennt die Analyse noch nicht» steht direkt darunter. |
| So kommst du dahin | 1 Filmen, 2 Hochladen, 3 Prüfen und teilen | Klar. «So filmst du richtig» führt zum Hallenplan. |
| Filmen | Hallenplan, Liste, Aushang zum Drucken | Er weiss, wo das Stativ hin muss und dass 10 GB frei sein sollen. |
| Zeigen / Kostenlos starten | `/einstieg` der App, mit dem Teamnamen | Hier endet die Website. Die App zeigt das Team aus den Verbandsdaten und fragt erst beim Speichern nach der E-Mail. |

Noch möglich, aber nicht behoben: Hans könnte «Prüfen» für eine Prüfung halten, bevor er es
erlebt. Die Erklärung steht bei Schritt 3 und unter «So funktioniert es».

## Art Director, Durchgang 1: Sieht es nach Vorlage aus?

- Nein. Keine Karten, keine Schatten, keine Rundungen, keine Verläufe, keine Icon-Kacheln, keine
  Fotos. Der Kopf in der Farbe des Besuchers, die schräge Kanit und der Keil unter jedem
  Seitenkopf sind dieselbe Welt wie die App.
- Gefunden und behoben: doppelte Linie über den drei Dingen; Anläufe am unteren Rand
  abgeschnitten (Feld jetzt bis zur Mittellinie); Navigation bricht bei 1280 um (fr zusätzlich
  gekürzt); doppelter Knopf durch eine Klasse in der falschen Ebene; Zonen-Zahlen zu klein.
- Bleibt: der Kopf ist auf breiten Bildschirmen rechts unter dem Resultat leer, wie in der App.
  Die Echos hinter dem Resultat überlappen die Namen am Handy leicht, wie in der App.

## Art Director, Durchgang 2: Würde ein Trainer das seinem Vorstand zeigen?

- Ja, mit zwei Vorbehalten. «Für den Vorstand» beantwortet Preis, Speicherort und Einwilligung,
  «Daten und Einwilligung» lässt sich Eltern weiterleiten, das Demo-Spiel ist sichtbar erfunden
  und trotzdem überzeugend.
- Vorbehalt 1: «Die Preise sind noch nicht endgültig» (gelb) und «Wer wir sind: folgt vor dem
  Start» sind ehrlich, aber ein Vorstand fragt nach. Beides wartet auf Lukas (Q-SITE-1, Q-SITE-3).
- Vorbehalt 2: die Rechtstexte sind Entwürfe; die Seite sagt das.
- Gefunden und behoben: Beschriftung in der Taktikkamera ragte am Handy über den Rand;
  Ballverluste hatten «8 Szenen», obwohl sie nur Zeitpunkte aus dem Spielbericht sind (so auch
  Befund B41 der Testerin für die App); zwei gleiche Links hintereinander.

## Abstimmung mit dem Einstieg der App

Gelesen: `docs/ux-test/runde1/BEFUNDE.md` auf `origin/claude/ux-test` (Stand 13. November). Einen
Abschnitt «Einstieg, wie er sein sollte» gibt es dort noch nicht; abgestimmt ist auf die Befunde
zu Aufgabe 1 (B24 bis B27) und SPEC 7.12.

Was die Website jetzt erklärt, muss der Einstieg der App nicht mehr erklären:
- was das Produkt ist und was man bekommt (drei Dinge, Szenen, Taktikkamera, Zahlen, Link);
- wie man filmt (Hallenplan, Einstellungen, Aushang);
- was es kann und was nicht (Ball, Paraden, Tore ohne Bericht, Schätzungen);
- Preise und Testphase, Daten und Einwilligung für Eltern.

Was die App dafür tun sollte (an die Session der App, nicht hier umgesetzt):
- Registrierung: «Nutzungsbedingungen» und «Datenschutzerklärung» auf `/{de,fr,en}/agb/` und
  `/datenschutz/` der Website verlinken (B25).
- Nach dem Einstieg eine Aufgabe: «Video hochladen» und «Demo-Spiel ansehen» (B26). Dieselben
  zwei Wege wie auf der Website, dieselben Wörter.
- Ein öffentliches Demo-Spiel der App ohne Konto (Q-SITE-5) würde das erfundene Spiel der Website
  ersetzen; bis dahin bleibt es dort, als erfunden markiert.
- `help-map.ts` auf die neuen Seiten der App umstellen; dann können die nicht gelisteten Anleitungen
  weg (Q-SITE-6).
- Wörter, die beide gleich brauchen: «Kostenlos starten», «Demo-Spiel», «Prüfen», «Spielbericht»,
  «Taktikkamera», «geschätzt», «Ball in dieser Szene nicht erkannt».

## Nachtrag 13. November: Team-Feld, Wortmarke, Belege

Nach `docs/ux-test/runde1/EINSTIEG.md` und der Rückmeldung der App-Session:
- «Wie heisst dein Team?» mit «Zeigen» im Kopf der Startseite (am Handy im ersten Bildschirm, über
  der Farbwahl) und unten noch einmal; GET auf `<App-URL>/einstieg?q=…&lang=…`. «Kostenlos starten»
  führt überall auf `/einstieg?lang=…`.
- Wortmarke zweizeilig, Zeichen rund 45 px hoch.
- Nicht belegt und darum entfernt: «ohne Kreditkarte» (Q-SITE-7). «30 Tage gratis» nur noch auf
  der Preisseite beim Plan. «Du bekommst eine Mail, wenn die drei Dinge da sind» steht wieder: die
  App baut diese Mail (Q-SITE-8). Alle Wege in die App tragen `farbe=` mit, sobald eine Farbe
  gewählt ist (Q-SITE-9). «Ab CHF 39» und «30 Tage gratis» stammen aus
  `packages/plans/plans.json` (`price_chf_month`, `trial_days`) und stehen nur mit «Die Preise sind
  noch nicht endgültig».
- Speicherort «App und Datenbank in der Schweiz, Videos in der EU»: belegt in
  `docs/adr/025-azure-app-hosting.md` (Punkt 1: Azure Switzerland North),
  `infra/terraform/azure/variables.tf` (`location`, Vorgabe `switzerlandnorth`) und
  `docs/adr/002-hosting-region.md` (Punkt 1: Cloudflare R2 mit EU-Jurisdiktion). Noch nicht in
  Betrieb; Q-SITE-4 bleibt offen.
- Wiederholt: axe 0, kein Überlauf (320 bis 1280, grosse Schrift), Tastatur (Feld und «Zeigen»
  direkt nach der Kopfzeile), Lighthouse 96 / 100 / 100 / 100.

## Nachtrag 13. November, morgens: Adressen ohne Sprache, 404 (Runde 2, N06)

- `/aufnahme/` und alle anderen Inhaltsseiten ohne Sprachpfad leiten auf die Sprache des Browsers
  (sonst de) weiter, mit `?query` und `#anker`: geprüft mit den Browsersprachen de-CH, fr-CH, en-GB
  und it-CH (fällt auf de) für `/aufnahme/`, `/aufnahme`, `/hilfe/einwilligungen/` und
  `/preise/?x=1#faq`.
- Eigene 404-Seite mit Start, Demo-Spiel und Fragen, Sprache aus dem Pfad oder dem Browser,
  Status 404 (mit `npx serve`); axe 0 Verstösse, kein Überlauf bei 390 und 1280.
- Fürs echte Hosting: Server-Weiterleitung und `error_page`, siehe README, Abschnitt «Hosting».

## Nicht geprüft

- Echte Geräte (iPhone Safari, Android Chrome) und echte Bildschirmleser (VoiceOver, NVDA): nur
  Chromium mit Playwright und axe.
- Die Links in die App gegen eine laufende App (`/einstieg?q=`, `/login`, `?lang=`); `/einstieg` wird gerade gebaut.
- Druck des Aushangs auf Papier (nur Druckansicht im Code: Kopf, Fuss und Rest ausgeblendet).
- Die französischen und englischen Texte durch Muttersprachige.
- Windows-Hochkontrastmodus.
