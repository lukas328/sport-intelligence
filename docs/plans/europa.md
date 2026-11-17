# Europa statt Schweiz: Positionierung, Sprachen, Märkte

Stand 17. November 2026. Auslöser: Lukas will weg vom starken Swiss-Branding. Das Produkt soll
für Vereine in ganz Europa sein (Frankreich, Spanien, Skandinavien, Deutschland, ...).
«Entwickelt in der Schweiz» darf bleiben, als Qualitätsmerkmal und nicht als Identität.

## Was heute schweizerisch ist

| Bereich | Heute | Gewicht |
|---|---|---|
| Website-Texte | rund 120 Stellen: «Schweiz», «Swiss», «Suisse», CHF, handball.ch, DSG, SHV | hoch, sofort sichtbar |
| App-Texte | Sprache `de-CH` (ss statt ß), CHF in Abo und Preisen, 30 Stellen handball.ch | mittel |
| Teamsuche (Einstieg) | sucht nur in den Verbandsdaten von handball.ch; Platzhalter mit Schweizer Ort | hoch: ein Verein aus Bremen findet sich nicht und erfährt nicht, warum |
| Verbandsdaten | Spielplan, Resultate, Kader und Spielbericht nur von handball.ch | Funktion |
| Preise | CHF 39 im Monat, CHF 390 im Jahr | Abrechnung |
| Recht | AGB und Datenschutz nach Schweizer Recht (DSG) | Pflicht vor Verkauf in der EU |
| Hosting | Azure Switzerland North, Videos bei Cloudflare R2 (EU) | für die EU unkritisch: die Schweiz hat einen Angemessenheitsbeschluss der EU |

## Vorschlag in drei Schritten

1. **Positionierung und Texte (sofort, ohne Funktionsänderung).**
   - Website und App sprechen von «Vereinen» und «Trainerinnen und Trainern», nicht von der Schweiz.
   - Datenschutz heisst «DSGVO und Schweizer DSG», Daten «in der Schweiz und der EU».
   - «Entwickelt in der Schweiz» steht an einer Stelle im Footer und auf «Über uns».
   - Die Teamsuche sagt ehrlich, wofür sie gilt: «Für Teams aus der Schweiz übernehmen wir Spielplan und Resultate automatisch. Alle anderen legen ihr Team in einer Minute von Hand an.»
   - Beispiele und Platzhalter sind erfunden und neutral.
2. **Preise und Recht (vor dem ersten Verkauf ausserhalb der Schweiz).**
   - Preise in EUR und CHF; die Währung wird aus dem Land gewählt, der Preis ist umschaltbar.
   - AGB und Datenschutzerklärung zusätzlich nach DSGVO, mit EU-Vertretung falls nötig (Art. 27 DSGVO).
   - Mehrwertsteuer im EU-Verkauf (OSS) über den Zahlungsanbieter.
3. **Sprachen und Verbandsdaten (nach Marktpotenzial).**
   - Sprachen: Deutsch für Deutschland (`de-DE`, mit ß) neben `de-CH`; dann Französisch für Frankreich (das heutige `fr` passt weitgehend), Spanisch, Dänisch, Norwegisch, Schwedisch.
   - Verbandsdaten: Die Schnittstelle zu handball.ch ist eine Quelle von mehreren. Weitere Verbände folgen nach Markt, z. B. DHB (handball.net), FFHandball, RFEBM, DHF, NHF, SHF, sobald es Zugang gibt; bis dahin funktioniert alles ohne Verbandsdaten.

## Entscheide (17.11., von Claude im Auftrag von Lukas: «alle Fragen gerne selber beantworten»)

| # | Frage | Entscheid |
|---|---|---|
| EU1 | Welche Märkte zuerst? | Deutschland und Frankreich (gross, Sprache schon da), dann Skandinavien (handballstärkste Länder), dann Spanien |
| EU2 | Deutsch für Deutschland mit ß (`de-DE`) neben `de-CH`? | ja, sobald der erste deutsche Verein testet; bis dahin ein neutrales Deutsch ohne Helvetismen |
| EU3 | Preise in EUR? Gleicher Betrag oder umgerechnet? | EUR 39 und CHF 39 (runde Zahl je Währung) |
| EU4 | Zeile «Entwickelt in der Schweiz»: wo? | Footer und «Über uns», nicht im Hero |
| EU5 | Rechtliche Prüfung AGB und Datenschutz für die EU | vor dem ersten zahlenden EU-Verein, durch eine Fachperson (nicht durch Claude ersetzbar) |

## Erste Umsetzung

Strang «Europa-Texte» nach der laufenden Website-Runde (W2): Schritt 1 komplett auf Website und
App (de, fr, en), ohne Preise, Recht und Verbände. Die Teamsuche bekommt den ehrlichen Satz und
einen direkten Weg zum Anlegen von Hand.

## Weitere Entscheide aus derselben Runde

- **Echte Namen in Tests und aufgezeichneten Verbandsdaten:** werden durch erfundene ersetzt (Strang N), auch Spielerinnen und Spieler in den handball.ch-Aufzeichnungen.
- **Git-Verlauf:** wird nicht umgeschrieben. Die alten Stände mit echten Namen bleiben im privaten Repository. Ein Umschreiben würde alle offenen Zweige und Sitzungen brechen. Wird das Repository je öffentlich, braucht es vorher eine Bereinigung (git filter-repo) oder ein neues Repository ohne Verlauf.
