# Website: Suchmaschinen und KI-Assistenten

Stand 13. November 2026, Branch `claude/site-seo`. Ziel: Trainerinnen und Trainer von
Amateur-Handballteams (zuerst Deutschschweiz, dann Romandie, Deutschland, Österreich), Vorstände und
Eltern finden die Website über eine Suche oder über die Antwort eines KI-Assistenten, und was sie dort
lesen, hält das Produkt.

Grundlage für jede Aussage über das Produkt: `docs/ux-test/echttest/BERICHT.md` und
`docs/OPEN_QUESTIONS.md` (Q-REC-*, Q-VIDEO-PARTS, Q-SITE-*). Kurz: Die Analyse findet das Feld und
verfolgt Spieler; Tore findet sie nicht sicher von selbst, sondern schlägt Momente vor, die die
Trainerin in ein paar Minuten bestätigt; danach gibt es Resultat, Verlauf, Tore als Szenen und
Positionen von oben. Kein Ball, keine Pässe, nur die erste Videodatei eines Spiels wird ausgewertet.

## 1. Bestand

Gebaut (`pnpm --filter @handball/site build`), mit `npx serve out` ausgeliefert, alle 45 Seiten je
Sprache mit einem eigenen Prüfskript (Titel, Beschreibung, h1, Überschriftenfolge, Canonical,
hreflang, Open Graph, JSON-LD, Bild-Texte) und Lighthouse 12 (Handy, simuliert gedrosselt).

**Was gut war**
- Statischer Export, keine Cookies, nichts von Dritten, selbst gehostete Schriften.
- Eine h1 pro Seite, keine Sprünge in der Überschriftenfolge, alle Bilder mit Alt-Text.
- Canonical und Sprachalternativen pro Seite, 404-Seite, Weiterleitungsseiten ohne Sprachpfad.
- Lighthouse Start 96 / 100 / 100 / 100, LCP 2.7 s, CLS 0.

**Was fehlte oder falsch war**

| Nr. | Befund | Wo |
|---|---|---|
| B1 | hreflang `fr` statt `fr-CH` (die Seite sagt `lang="fr-CH"`) | alle Seiten, Sitemap, `public/index.html` |
| B2 | Sitemap listet nur die `/de/`-Adressen; fr und en nicht als eigene Einträge, ohne `x-default`, ohne `lastmod` | `src/app/sitemap.ts` |
| B3 | Titel zu allgemein und mehrfach: «Filmen», «Preise», «Blog» (dreimal derselbe Titel), «Highlights» | alle Unterseiten |
| B4 | Beschreibungen aus Bausteinen zusammengesetzt; drei Rechtsseiten mit derselben Beschreibung; Start 187 bis 222 Zeichen | `pageMeta`-Aufrufe |
| B5 | Open Graph auf Unterseiten ohne `og:site_name`, `og:locale`, `og:type` (Next ersetzt das Objekt des Layouts ganz) | `src/lib/seo.ts` |
| B6 | JSON-LD nur auf Start (Organization, SoftwareApplication ohne Pläne), Blog und Hilfe; kein WebSite, keine Brotkrümel, keine Fragen | Seiten |
| B7 | Weiterleitungsseiten und `/` mit relativem Canonical und relativem hreflang (Suchmaschinen verlangen absolute Adressen) | `scripts/redirects.mjs`, `public/index.html` |
| B8 | Kein `llms.txt`, keine Seite mit den Fakten zum Zitieren | |
| B9 | Kein sichtbares «Stand»-Datum auf Kernseiten | |
| B10 | Kaum Inhalt, der Fragen beantwortet, die jemand ohne das Produkt sucht (nur zwei Blogbeiträge) | |
| B11 | Seiten beginnen mit einem Satz über die Seite («Die häufigsten Fragen zuerst»), nicht mit der Antwort | Fragen, So funktioniert es, Filmen |
| B12 | Aussagen, die der Echttest nicht hält: «Tore aus einer Spielstand-Anzeige», «Mail, wenn die drei Dinge da sind», «Das bekommst du nach jedem Spiel», Blog: «erkennt … daraus abgeleitete Tore»; Speicherort als Tatsache, obwohl noch nicht in Betrieb (Q-SITE-4) | Texte de/fr/en, Hilfe, Blog |

## 2. Recherche

Es gab kein Werkzeug für Suchvolumen. Als Beleg für eine Frage gilt nur, dass ein Verband, ein
Anbieter, ein Forum oder eine Vereinsseite die Formulierung tatsächlich verwendet. Urteile sind als
solche markiert. Recherche am 13. November 2026.

### 2.1 Wonach diese Leute suchen

| Frage | Sprache | Absicht | Wer antwortet heute | Lücke |
|---|---|---|---|---|
| Handballspiel mit dem Handy filmen, welches Stativ, welche Höhe? | de | tun | Händler und Kamera-Hersteller, nicht handballspezifisch ([xbotgo](https://xbotgo.com/de/blogs/buying-guide/handball-cameras), [insta360](https://www.insta360.com/blog-de/tipps/kamera-stativ.html)) | ja |
| Wo stelle ich die Kamera in der Halle auf? | de/en | tun | Anbieter, meist zu anderen Sportarten ([movensee](https://movensee.com/en/blog/b8a2d68c-why-shoot-from-above), [Veo Basketball](https://www.veo.com/article/how-to-record-basketball-games)) | ja |
| Ganzes Feld im Bild, nicht zoomen | de | tun | Bayerischer HV, als Regel für den Videoaustausch ([BHV](https://www.bhv-online.de/filemanager/BHV/Daten/Spielbetrieb/Saison%2023-24/richtlinien-videoaustausch-bhv.pdf)) | teilweise |
| filmer un match de handball avec un smartphone | fr | tun | Anbieter ([Dartfish](https://blog.dartfish.com/2024/06/12/interview-with-fabien-vidal-handball), [Bepro](https://fr.bepro11.com/news-updates/how-to-film-your-games)); Weiterbildung der FFHB kostenpflichtig ([AURA](https://aura-handball.fr/wp-content/uploads/2025/11/2025-2026_FPC_AURA_Outils_videos_au_service_entrainement.pdf)) | ja |
| how to film youth sports | en | tun | [Veo](https://www.veo.com/article/how-to-film-youth-sports-as-a-parent) | für de ja |
| Videoanalyse Handball, welche Software für Amateure? | de | vergleichen | Listen-Seiten ([gitnux](https://gitnux.org/best/handball-video-analysis-software/)), Hochschularbeiten | ja |
| Veo / Pixellot / Spiideo Handball, Preis, Erfahrungen | de/en | vergleichen | nur die Anbieter selbst; unabhängige Handball-Tests fehlen | ja |
| Kinovea, LongoMatch kostenlos | de/en | vergleichen | Listen, ein Gewichtheber-Verband | ja |
| Handball Statistik App | de | vergleichen | nur App-Store-Texte | ja |
| Wurfquote, Torwartquote, Paradenquote berechnen | de | verstehen, tun | HBL-Kolumne für Profis; Zählregeln im [Statistik-Manual von Handball Schweiz](https://www.handball.ch/media/wsnpvmfn/live-ticker_statistik-manual-2024-03.pdf), nicht für Trainer geschrieben | ja |
| 6:0, 5:1, 3:2:1 Abwehr, Unterschied | de/fr/en | verstehen | gut abgedeckt ([Wikibooks](https://de.wikibooks.org/wiki/Handball_%E2%80%93_Taktik_f%C3%BCr_Jugendliche:_Die_Systeme), Landessportbünde, Vereinsblogs fr) | nein, nur der Bezug zum eigenen Video fehlt |
| Gegenstoss (CH) / Tempogegenstoss (DE) trainieren | de | tun | [mobilesport.ch](https://assets01.sdd1.ch/assets/lbwp-cdn/mobilesport/files/1681422397/mobilesport-handball--gegenstoss-zweikampf.pdf), Schulmaterial | für «im Video erkennen» ja |
| Videofeedback im Training, Videositzung | de | tun | [Jugend+Sport «Lernen mit Bildern»](https://www.sport.admin.ch/js/manual/de/BR_JS_Lernen_mit_Bildern_d.pdf) (älter), Hudl-Blog (Fussball) | ja |
| Einwilligung Fotos und Videos im Verein, Minderjährige | de (DE) | verstehen, tun | Landessportbünde, Kanzleien, Musterformulare (DSGVO) | für CH ja |
| Recht am Bild im Verein (CH) | de-CH | verstehen | [Swiss Olympic](https://academy.swissolympic.ch/asset/download/68f72894659bb7917e066b74), [Pfadi](https://pfadi.swiss/de/publikationen-downloads/downloads/detail/686/merkblatt-recht-am-bild-bei-pfadi-aktivitaten) | teilweise |
| Datenschutz-Vorlagen Handballverein | de-CH/fr | tun | [Handball Schweiz](https://www.handball.ch/media/2ldbe5bh/datenschutzverordnung-fuer-handballvereine_empfehlung-shv.pdf): gute Vorlagen, nichts zum Filmen für die Analyse | ja |
| Darf der Trainer intern filmen, ohne zu veröffentlichen? | fr/de | verstehen | französische Fussball-Liga, Volleyball NRW: andere Länder und Sportarten | für CH ja |
| droit à l'image enfants club (Suisse) | fr | verstehen | verstreut (andere Verbände, Pfadi) | ja |

**Wortgebrauch:** Die Schweiz schreibt «Gegenstoss», Deutschland «Tempogegenstoß»; der SHV sagt
«Match», «Goalie», «Paraden». In Frankreich wird die Abwehr oft umgekehrt gezählt («défense 0-6,
1-5»). Die Seiten nennen beide Varianten, wo sie verschieden sind.

**Wer antwortet heute:** Zum Filmen und zu Werkzeugen fast nur Anbieter (Veo, Pixellot, Hudl,
Spiideo, Dartfish, XbotGo). Verbände liefern Vorlagen und Regeln, aber keine Anleitung zum Filmen
eigener Spiele. Foren-Diskussionen (handball-world, Reddit, gutefrage) zu diesen Fragen wurden nicht
gefunden. **Urteil:** Eine neutrale, praktische deutschsprachige Antwort fehlt bei Filmen, Einwilligung
in der Schweiz, kurzer Auswertung, Videositzung und den Grenzen automatischer Analyse.

Handball Schweiz hat ein «Informationsblatt Datenschutz aufgezeichnete Spiele» (Saison 2025/26); die
Seite lieferte am Recherchetag HTTP 503 und ist **nicht gelesen**. Vor einer Überarbeitung des
Einwilligungs-Ratgebers lesen.

### 2.2 Recht beim Filmen im Verein (für den Ratgeber)

- **EDÖB, «Umgang mit Fotos»** ([Quelle](https://www.edoeb.admin.ch/de/umgang-mit-fotos)): Recht am
  eigenen Bild; erkennbare Personen sind Personendaten; im Zweifel Einwilligung; bei Minderjährigen
  die Erziehungsberechtigten (für die Publikation); Widerspruch respektieren. Spricht nur von Fotos.
- **EDÖB, «Datenschutz in Vereinen»** ([Quelle](https://www.edoeb.admin.ch/de/datenschutz-in-vereinen)):
  erkennbarer Zweck, nur Nötiges, löschen sobald nicht mehr erforderlich, Internet kaum löschbar.
- **Swiss Olympic, Merkblatt «Recht am eigenen Bild»** (EY Law, 3.10.2025,
  [Quelle](https://academy.swissolympic.ch/asset/download/68f72894659bb7917e066b74)): gilt für Fotos,
  Videos, Livestreams; Rückennummer macht erkennbar; bei nicht öffentlichen Anlässen informiert der
  Veranstalter; urteilsfähige Minderjährige willigen selbst ein, keine feste Grenze, «üblicherweise
  mit ungefähr 15 Jahren».
- **Deutschland:** LfDI Baden-Württemberg (2018) verlangt für Mannschaftsfotos Minderjähriger stets
  die Einwilligung der Eltern; BayLDA (2019) hält Vereinsfotos mit Kindern «mit Fingerspitzengefühl»
  teils ohne Einwilligung für zulässig. Die Seite nennt den Widerspruch.
- **Österreich:** keine Behördenquelle gefunden; die Seite sagt das und empfiehlt den Landesverband.

### 2.3 Andere Wege zur Videoanalyse (nur Aussagen der Anbieter selbst)

Veo ([Handball-Kamera](https://www.veo.com/us/handball-camera): Cam 3 für Handball, Kamera plus Abo,
automatische Ereignisse nur für Fussball genannt), Pixellot ([Handball](https://www.pixellot.tv/sports/handball/):
fest oder tragbar, keine Preise), Spiideo ([AutoData](https://www.spiideo.com/handball-video-analysis-software/):
Auswertung durch Fachleute innert 24 h, auch fremde Videos), Dartfish ([Teamsport](https://www.dartfish.com/teamsports):
Markieren live oder danach, ab 40 € im Monat bei Jahreszahlung), LongoMatch ([Preise](https://longomatch.com/en/pro/):
Gratis-Version, ab 15 € im Monat), Hudl Sportscode ([Seite](https://www.hudl.com/en_gb/products/sportscode)),
Handball.ai ([Seite](https://handball.ai/)), Kinovea ([gratis, quelloffen](https://www.kinovea.org/)),
Shotcut ([gratis](https://www.shotcut.org/)). Nicht verifiziert und darum nicht genannt: Nacsport-Preise,
Hudl Assist für Handball, Sportlyzer, Coach Paint.

### 2.4 Begriffe je Sprache

Aus den IHF-Regeln 2025 ([de](https://www.ihf.info/sites/default/files/2025-07/09A%20-%20Rules%20of%20the%20Game_Indoor%20Handball_D.pdf))
und dem [EHF-Glossar](https://activities.eurohandball.com/media/n20dz43w/ehf-handball-glossary.pdf):
Spielprotokoll / score sheet, match report / feuille de match; 7-m-Wurf / 7-metre throw / jet de 7 mètres;
Anwurf / throw-off / engagement; Hinausstellung / 2-minute suspension / exclusion de 2 minutes;
Torwart / goalkeeper / gardien de but; Aussen / wing / ailier; Rückraum / back / arrière (demi-centre);
Kreisläufer / line player, pivot / pivot; Gegenstoss / fast break / contre-attaque; Ballverlust /
turnover, technical fault; Parade / save. Die Website bleibt beim Vokabular von SPEC 9
(Spielbericht, Feuille de match, Match report).

### 2.5 Wie Websites in KI-Antworten gefunden werden: belegt und behauptet

**Belegt (Betreiber-Dokumentation):**
- Google: Für AI Overviews und AI Mode gibt es «no additional requirements» und keine besondere
  Auszeichnung oder Datei; die Seite muss indexiert sein und ein Snippet zeigen dürfen, strukturierte
  Daten müssen zum sichtbaren Text passen ([AI features](https://developers.google.com/search/docs/appearance/ai-features),
  [AI optimization guide, 15.05.2026](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)).
  In der Search Console steuert die Einstellung «Search generative AI» (Standard: Include) die
  Aufnahme ([Hilfe](https://support.google.com/webmasters/answer/16908024)).
- Google-Extended steuert nur Gemini-Training und Gemini-Grounding, nicht die Google-Suche und nicht
  AI Overviews ([Crawler](https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers)).
- FAQ-Rich-Results gibt es seit 7. Mai 2026 nicht mehr, HowTo-Rich-Results seit 2023 nicht mehr,
  die Sitelinks-Suchbox seit November 2024 nicht mehr ([Changelog](https://developers.google.com/search/updates)).
  WebSite bleibt für den Website-Namen nützlich ([site names](https://developers.google.com/search/docs/appearance/site-names)).
- Das Rich Result für SoftwareApplication verlangt einen Preis und eine Bewertung oder Rezension
  ([software-app](https://developers.google.com/search/docs/appearance/structured-data/software-app)).
  Wir haben beides nicht und erfinden nichts: kein Rich Result, das Markup hilft nur beim Verstehen.
- Strukturierte Daten nur für sichtbaren Inhalt, sonst manuelle Massnahme
  ([Richtlinien](https://developers.google.com/search/docs/appearance/structured-data/sd-policies)).
- hreflang: jede Sprachfassung nennt sich selbst und alle anderen, gegenseitig, absolute Adressen,
  `de-CH`, `fr-CH`, `en`, `x-default` ([Google](https://developers.google.com/search/docs/specialty/international/localized-versions)).
- Crawler: OpenAI `GPTBot` (Training), `OAI-SearchBot` (Suche, Zitate), `ChatGPT-User` (vom Nutzer
  ausgelöst) ([OpenAI](https://developers.openai.com/api/docs/bots)); Anthropic `ClaudeBot` (Training),
  `Claude-SearchBot` (Suche), `Claude-User` ([Anthropic](https://support.claude.com/en/articles/8896518));
  Perplexity `PerplexityBot` (Suche, nicht Training), `Perplexity-User` (ignoriert robots.txt meist)
  ([Perplexity](https://docs.perplexity.ai/guides/bots)); `Applebot-Extended` ist nur ein Opt-out vom
  Training ([Apple](https://support.apple.com/en-us/119829)); `CCBot` ([Common Crawl](https://commoncrawl.org/ccbot));
  Meta `meta-externalagent` (Training, Indexierung), `meta-webindexer` (Zitate in Meta AI)
  ([Meta](https://developers.facebook.com/docs/sharing/webmasters/web-crawlers/)); Bing: ab 1.2.2027
  eigene Präferenzen für Training und Grounding ([Bing-Blog, 30.10.2026](https://blogs.bing.com/search/2026/10/your-content-your-choice-clearer-preferences-for-training-and-grounding/)).
- llms.txt ist ein Vorschlag ([llmstxt.org](https://llmstxt.org), seit 2024), kein Standard. Google
  sagt ausdrücklich, dass die Google-Suche die Datei nicht nutzt und sie weder hilft noch schadet.
  OpenAI und Anthropic erwähnen sie in ihrer Crawler-Doku nicht.
- Manipulation: versteckter Text, Stichwort-Listen, massenhaft erzeugte Seiten ohne Mehrwert und seit
  Mai 2026 ausdrücklich auch Versuche, generative Antworten zu beeinflussen, sind Spam
  ([Spam-Richtlinien](https://developers.google.com/search/docs/essentials/spam-policies)).

**Nur behauptet oder unklar:** dass FAQ-Markup KI-Zitate fördert; dass llms.txt Zitate beeinflusst
(Anbieter-Studien deuten auf kaum Abrufe); dass ChatGPT-Suche den Bing-Index nutzt; besondere «GEO»-
oder «Chunking»-Techniken (Google widerspricht).

**Folgerung für uns:** Was wirkt, ist das Übliche: indexierbare Seiten, klare Antworten im Text,
eigene Titel und Beschreibungen, korrekte Sprachfassungen, Sitemap, strukturierte Daten, die zum
Text passen, und Inhalte, die eine Frage besser beantworten als das, was es gibt. llms.txt und die
Faktenseite sind billig und schaden nicht; die Faktenseite hilft auch Menschen (Vorstand, Presse).

## 3. Begriffs- und Fragenplan

| Frage | Seite | Sprachen |
|---|---|---|
| Wie filme ich ein Handballspiel mit dem Handy? Welches Stativ, wie hoch? | `/ratgeber/handballspiel-filmen/` | de, fr, en |
| Was bringt Videoanalyse einem Amateurteam, wie viel Zeit kostet sie? | `/ratgeber/videoanalyse-amateurteam/` | de, fr, en |
| Dürfen wir im Verein filmen, auch Kinder? Wer sieht das Video, wie lange? | `/ratgeber/video-im-verein-einwilligung/` | de, fr, en |
| Wie werte ich ein Spiel in kurzer Zeit aus? | `/ratgeber/spiel-auswerten-20-minuten/` | de |
| Woher kommen unsere Gegentore? | `/ratgeber/gegentore-nach-position/` | de |
| Gegenstösse und Ballverluste auswerten | `/ratgeber/gegenstoss-und-ballverluste/` | de |
| Wurfquote und Torhüterquote berechnen | `/ratgeber/wurfquote-torhueterquote/` | de |
| Wie zeige ich Szenen im Training (Videositzung)? | `/ratgeber/szenen-im-training-zeigen/` | de |
| Was heisst Rückraum, 5:1, Wurfquote …? | `/ratgeber/handball-begriffe/` | de |
| Von Hand, Kamera, Software oder automatisch: was passt? | `/ratgeber/wege-zur-videoanalyse/` | de |
| Was ist Handball Intelligence, für wen, was kann es, was kostet es, wo liegen die Daten? | `/fakten/`, `/llms.txt` | de, fr, en |
| Erkennt die Analyse die Tore selbst? Reicht mein Handy? | `/hilfe/` (Fragen) | de, fr, en |
| Wie läuft es ab, was muss ich prüfen? | `/so-funktioniert-es/` | de, fr, en |
| Checkliste und Aushang für den Spieltag | `/aufnahme/` | de, fr, en |
| Was passiert mit dem Video (Eltern)? | `/daten/` | de, fr, en |
| Was kostet es (Vorstand)? | `/preise/` | de, fr, en |

Die Filmanleitung gibt es zweimal mit verschiedener Aufgabe: `/aufnahme/` ist die kurze Checkliste
mit Aushang (Titel «Spiel filmen: Checkliste und Aushang»), der Ratgeber die ausführliche Antwort
(«Handballspiel mit dem Handy filmen»). Beide verlinken sich.

## 4. Was umgesetzt ist

### Technik
- **Metadaten:** `src/lib/seo.ts`: eigener Titel und eine eigene Beschreibung je Seite und Sprache
  (`messages.seo`, Ratgeber im Index), höchstens 160 Zeichen (Test). hreflang `de-CH`, `fr-CH`, `en`,
  `x-default` (= de), gegenseitig, absolute Adressen; Seiten nur auf Deutsch nennen nur `de-CH` und
  `x-default`. Open Graph vollständig, Artikel mit `og:type=article` und Daten; `twitter:card`.
- **Sitemap:** jede Seite in jeder Sprache als eigener Eintrag, mit allen Alternativen und
  `lastmod` (100 Adressen); `noindex`-Seiten fehlen (nicht gelistete Hilfe, `/funktionen/`).
- **robots:** alles erlaubt, die KI-Crawler einzeln genannt (von Lukas entschieden, Abschnitt 7), Verweis auf die Sitemap.
- **Weiterleitungsseiten und `/`:** absolute Canonical und hreflang; Ratgeber, die es nur auf Deutsch
  gibt, leiten alle Sprachen auf `/de/`; die Sprachwahl im Fuss führt dort auf die Ratgeber-Übersicht
  der Sprache statt auf eine 404.
- **Strukturierte Daten** (`src/lib/schema.ts`): Organization und WebSite (Start, Fakten),
  SoftwareApplication mit den drei Plänen aus `packages/plans` als Offer ohne Preis
  (`PRICES_FINAL = false` in `src/lib/site.ts`), WebPage/AboutPage/CollectionPage, Article und
  BlogPosting und TechArticle mit Datum (Herausgeberin und Autorin ist die Organisation, keine Person),
  BreadcrumbList (sichtbare Brotkrümel auf Ratgebern, Blog, Anleitungen), FAQPage (Fragen, Preise,
  Ratgeber), HowTo (So funktioniert es, Filmen, 20 Minuten, Videositzung, Einwilligung). Kein
  AggregateRating, keine Review.
- **KI-Assistenten:** `/llms.txt` (kurz) und `/llms-full.txt` (alle drei Sprachen), erzeugt aus
  denselben Texten wie die Seiten (`src/lib/llms.ts`). Seite «Fakten auf einen Blick» je Sprache
  (`/fakten/`) mit Einleitung, Tabelle und der Liste «kann / kann noch nicht».
- **Antwort zuerst:** jede Ratgeberseite hat die Frage als Titel und zwei bis drei Sätze Antwort
  darunter; Fragen, Preise, Daten, Filmen, So funktioniert es beginnen jetzt mit der Antwort.
  Sichtbares «Stand» auf Ratgebern, Fakten, Fragen, Daten, So funktioniert es.
- Weiter statisch, keine Cookies, keine fremden Dienste, keine Analyse-Skripte.

### Inhalte
- **Ratgeber** (`content/ratgeber`, Übersicht `/ratgeber/`, in der Kopfzeile): zehn Seiten auf
  Deutsch (Tabelle oben), drei davon in fr und en. Jede Seite mit Antwort zuerst, Schritten,
  Kurzantworten, internen Links, einem ruhigen Absatz «Und Handball Intelligence?» am Ende und Datum.
  Eigene Zeichnungen als SVG im Aussehen der Website (`src/components/figures.tsx`): Hallenplan mit
  Kamera, Halle von der Seite (hoch und tief), Feld mit Positionen und Abwehrsystemen, Gegentore nach
  Zone (als Beispiel bezeichnet), Spielverlauf auf 60 Minuten. Zahlen in Beispielen sind erfunden und
  so bezeichnet. Quellen am Ende jeder Seite, wo Fakten von aussen stammen.
- **Bestehende Seiten geschärft** (de, fr, en): Start, So funktioniert es, Fragen (neu: «Erkennt die
  Analyse die Tore selbst?»), Preise, Daten, Filmen, «Das kann es, das noch nicht». Kern: Die Analyse
  schlägt Tor-Momente vor, du bestätigst sie in ein paar Minuten; freiwillige Fragen beantworten,
  sonst kann ein Tor fehlen; Mail, wenn die Analyse fertig ist (nicht «wenn die drei Dinge da sind»);
  drei Dinge nur «bei genug Toren»; Anzeigetafel der Halle wird nicht gelesen; Positionen geschätzt,
  können Zuschauer und Bank enthalten; Speicherort «vorgesehen». Dasselbe in den Anleitungen
  «Analyse lesen», «Datenschutz und Löschen» und im Blogbeitrag zur Unsicherheit.
- **«Über uns»** als eigene Seite aus der Vision von Lukas (Abschnitt 9). Keine Personen, Zahlen, Kundenstimmen oder Logos erfunden.

## 5. Prüfung (13. November 2026)

| Prüfung | Ergebnis |
|---|---|
| `pnpm --filter @handball/site lint`, `typecheck`, `test` | sauber, 24 Tests in 7 Dateien (neu: Sitemap und hreflang gegenseitig, robots, llms.txt, Ratgeber in jeder gelisteten Sprache, Beschreibung höchstens 160 Zeichen, keine Gedankenstriche und kein ß) |
| Wurzel: `ruff check`, `ruff format --check`, `make_demo.py --check`, `madge --circular` (Site) | sauber |
| Build (`pnpm --filter @handball/site build`) | sauber, 46 Weiterleitungsseiten, 404 |
| axe 4.10 (WCAG 2.0 bis 2.2 A/AA, best practice), alle Adressen der Sitemap (zuletzt 100) bei 390 und 1280 | 0 Verstösse (zuerst 2: leere Tabellenköpfe, behoben) |
| Kein waagrechter Überlauf: 320, 390, 1280 und 390 mit Grundschrift 150 % | alle (zuerst 9: breite Tabellen, Faktentabelle; jetzt eigene Scrollbox bzw. gestapelt) |
| Text unter 16 px ausserhalb von Grafiken | keiner |
| Interne Links (zuletzt 100 verschiedene, auf jeder Seite gesammelt) | alle 200 (zuerst 14 auf nicht vorhandene fr/en-Ratgeber über die Sprachwahl, behoben) |
| Sitemap und hreflang | jede Adresse in der Sitemap, jede mit `x-default` und gegenseitigen Alternativen (Test) |
| JSON-LD aller Seiten gegen das schema.org-Vokabular (`schemaorg-current-https.jsonld`) | alle Typen und Felder gültig; Pflichtfelder nach Google vorhanden; jede Frage, Antwort, jeder Schritt, Brotkrümel und Titel steht sichtbar auf der Seite; kein Preis, keine Bewertung |
| Lighthouse 12, Handy | Start 96 / 100 / 100 / 100 (LCP 2.6 s, CLS 0); Ratgeber Filmen 99 / 100 / 100 / 100 (nach der Korrektur); Fakten 98 / 100 / 100 / 100; Ratgeber Einwilligung fr 98 / 100 / 100 / 100. Ein Hydrationsfehler (Brotkrümel in einem `<p>`) drückte Best Practices zuerst auf 96, behoben |

**Zwei kritische Durchgänge**
1. *Würde ein Trainer das weiterleiten?* Die Ratgeber beantworten die Frage im ersten Absatz und
   bleiben dann bei Schritten, Listen und einem Beispiel. Gestrichen oder gekürzt: Werbesätze im Text,
   doppelte Erklärungen, Wiederholung des Stichworts. Der Hinweis aufs Produkt steht nur am Schluss.
   Der Einwilligungs-Ratgeber hat einen Mustertext, den ein Verein direkt brauchen kann; das ist der
   wahrscheinlichste Grund, ihn weiterzuleiten.
2. *Verspricht etwas mehr, als das Produkt hält?* Gefunden und geändert: «Tore aus einer
   Spielstand-Anzeige», «Mail, wenn die drei Dinge da sind», «Das bekommst du nach jedem Spiel»,
   Blog «erkennt … daraus abgeleitete Tore», Speicherort als Tatsache. Stehen gelassen, weil belegt:
   Spielbericht (Import aus `official_feed` in der API), Mail bei fertiger Analyse (Echttest),
   Prüfen in «ein paar Minuten» (Echttest: 6 bis 7 Minuten für alle 22 Fragen), «jedes Tor unter den
   Vorschlägen» nur als «in unserem ersten Test». Der Kopf der Startseite verspricht weiter «drei
   Dinge zum Mitnehmen»; der Satz darunter sagt jetzt, dass man vorher Tor-Momente bestätigt, und
   die Liste sagt «bei genug Toren».

## 5b. Zweite Runde (13./14. November 2026, nach der Rückmeldung zur ersten Fassung)

- **Ratgeber am Desktop:** ab 1024 px eine mitlaufende Seitenspalte mit «Auf dieser Seite» (Sprungmarken
  zu allen h2, ids aus `src/lib/slug.ts`) und einem ruhigen Kasten zum Start; am Handy das
  Inhaltsverzeichnis aufklappbar unter dem Vorspann. «Mehr dazu» zeigt zu jedem Artikel die Beschreibung.
- **Zeichnungen:** Hallenplan massstäblich mit Weitwinkel (etwa 120 Grad), Kamera auf der Tribüne:
  beide Tore und Torräume im Bild, die nahen Ecken nicht, Beschriftung ausserhalb des Feldes. Gilt
  auch für «Filmen», «So funktioniert es» und «Über uns». Höhe: zwei kleine Bilder (tief / hoch) mit
  je einer Zeile darunter.
- **Weitwinkel** im Ratgeber, auf «Filmen», bei den Fragen und in der Hilfe: 0,5× bzw. «Ultraweit»;
  was im Bild sein muss; was tun, wenn es nicht passt; Verzerrung am Rand. Belegt im Code:
  `packages/vision/handball_vision/calibration.py` sucht die vier Aussenlinien (Hough-Linien, gerade),
  entzerrt nicht; Ecken ausserhalb des Bildes lassen sich seit dem Echttest speichern.
- **`MULTI_FILE`** in `src/lib/site.ts` (heute `false`): schaltet jede Aussage zur zweiten Datei um
  (Fakten «Was du brauchst» und «Was es nicht kann», «Das kann es, das noch nicht», llms.txt,
  Filmen-Seite, Fragen, Spieltag-Checkliste, Filmen-Ratgeber de/fr/en, Hilfe «Spiel richtig filmen»
  und «Video hochladen» de/fr/en). Die Empfehlung, in der Pause weiterzufilmen, bleibt, ohne Drohung.
- **Ratgeber-Übersicht:** jede Zeile mit der kleinen Zeichnung des Artikels oder seiner Zahl; die
  Checkliste «Filmen» in der Rubrik Filmen; neue Rubrik «Vorlagen und Rechner».
- **Wege zur Videoanalyse:** jede Aussage über andere Anbieter am 13. November 2026 auf deren Seite
  geprüft; gestrichen: Veos «automatische Ereignisse für Fussball» (steht so nicht da), Preise ohne
  Zahl; Dartfish und LongoMatch mit Preis und Stand; Spiideo auf die AutoData-Seite; neu: iMovie,
  CapCut, XPS, Coach Paint, RED+-Livestreams in der Schweiz (Quelle Horizont 2025; handball.ch war
  nicht erreichbar, ob Vereine die Aufnahmen bekommen, ist nicht belegt). Nicht aufgenommen:
  KlipDraw (keine Herstellerquelle erreichbar), asport (laut Suchergebnissen eingestellt, nicht belegt).
- **Vorlagen zum Drucken** (de, fr, en): `/vorlagen/einwilligung/`, `/vorlagen/strichliste/`,
  `/vorlagen/spieltag/`, je ein A4-Blatt mit `@media print`; der Aushang bleibt auf `/aufnahme/`.
- **Druck nachgemessen:** `apps/site/scripts/check-print.mjs` druckt die drei Vorlagen und den Aushang
  je Sprache mit Chromium als PDF (A4 aus `@page`) und prüft: genau eine Seite. Läuft von Hand nach
  dem Build (`node scripts/check-print.mjs`), weil Playwright keine Abhängigkeit der Website ist;
  Stand: 12 von 12 Seiten passen. Im Druck mindestens 12 pt, Kästchen 6,5 bis 7 mm, Blatt gefüllt;
  der Aushang ist ganzseitig, 50 pt, ohne Silbentrennung, mit «Fragen an: ____»; die Einwilligung
  hat eine Zeile «Team / Verein» und einen Satz zum Widerruf (an wen).
- **Rechner** (de, fr, en): `/rechner/wurfquote/` (Wurf- und Torhüterquote mit Satz und Basis zum
  Kopieren) und `/rechner/speicher/` (Minuten mal Einstellung); Formeln und eine Tabelle stehen ohne
  JavaScript auf der Seite. Nichts verlässt den Browser.
- **Startseite:** «Für wen» mit drei Fällen (Juniorentrainerin, Aktive, Vereinsverantwortliche) und je
  einem Ratgeber; dazu «Aus dem Ratgeber» und «Wer dahinter steht».
- **Französisch:** alle zehn Ratgeber (sieben neu). Englisch bleibt bei den drei Kernratgebern.
- **Interne Links:** Hilfe «Spiel richtig filmen», «Einwilligungen», «Analyse lesen» verlinken den
  passenden Ratgeber; Ratgeber verlinken Vorlagen und Rechner.
- **Blog zusammengelegt:** «Spiele filmen mit dem Handy» beantwortete dieselbe Frage wie der
  Filmen-Ratgeber; die Seite leitet dorthin weiter, `noindex`, Canonical auf den Ratgeber, 301 im
  README beschrieben, nicht mehr in Sitemap, Blog-Liste und llms.txt.
- **Prüfskript** `apps/site/scripts/check-out.mjs`: läuft nach jedem Build (der Build schlägt fehl)
  und in den Tests, sobald `out/` existiert. Regeln: genau eine h1; Titel höchstens 60 und
  Beschreibung 70 bis 160 Zeichen, je Sprache einmalig; Canonical auf sich selbst; hreflang mit
  x-default, gegenseitig vollständig; JSON-LD parst und nennt nur Sichtbares, keine Bewertung;
  jeder interne Link führt zu einer Seite; jede indexierbare Seite in der Sitemap und mit
  eingehendem Link; nirgends die alte Domain. Titel über 60 Zeichen stehen ohne «| Handball
  Intelligence». Stand: 152 Seiten, 122 indexierbar, 0 Probleme.

## 6. Domain und Livegang

**Entschieden am 13. November 2026:** `handball-intelligence.com`. Seite `https://handball-intelligence.com`,
App `https://app.handball-intelligence.com`, Staging `https://staging.handball-intelligence.com`,
Support `support@handball-intelligence.com`.

In `apps/site` ist die Domain umgestellt: Vorgaben in `src/lib/site.ts` (Seite, App, Support) und
`scripts/redirects.mjs`, Tests (`site.test.ts`, `seo.test.ts`), README. Die Adresse kommt überall aus
`NEXT_PUBLIC_SITE_URL`: Canonical, hreflang, Sitemap, robots, JSON-LD, llms.txt, Weiterleitungsseiten.

**Übriges Repo:** Laut der auftraggebenden Session hat sie die Domain ausserhalb von `apps/site` und
`docs/site` selbst umgestellt (Branch `claude/compassionate-pascal-n3gl03`, Commit `f38c4d6`: API,
Web, Mobile, client-core, LIVEGANG, OPEN_QUESTIONS, DESIGN, pentest-scope). Auf diesem Branch
(`claude/site-seo`) sind diese Dateien unverändert, damit es keinen Konflikt gibt; hier nicht geprüft.

Nicht anfassen (bleibt bei Lukas): Bundle-IDs `ch.handballai.app`, Firmenname «Handball AI GmbH», Preise.

### Vor dem Livegang

1. **DNS:** `handball-intelligence.com` auf das statische Hosting der Website, `app.` und `staging.`
   auf die App. HTTPS mit gültigem Zertifikat für alle drei.
2. **Eine Schreibweise:** ohne `www`. Canonical, Sitemap und alle Links verwenden
   `https://handball-intelligence.com`. `www.handball-intelligence.com` antwortet mit 301 auf dieselbe
   Adresse ohne `www`, Pfad und Abfrage bleiben erhalten. `http://` leitet ebenso mit 301 auf `https://`.
3. **Server-Weiterleitungen** der Adressen ohne Sprachpfad und `404.html` mit Status 404 einrichten
   (`apps/site/README.md`, «Hosting»).
4. **Mail:** Für `support@handball-intelligence.com` MX, SPF, DKIM und DMARC setzen, damit Antworten
   und die Mails der App nicht im Spam landen. Die App-Mails mit derselben Absender-Domain verschicken.
5. **App-Links:** `/.well-known/apple-app-site-association` und `/.well-known/assetlinks.json` auf
   `app.handball-intelligence.com` ausliefern, passend zu `associatedDomains` und dem Intent-Host in
   `apps/mobile/app.json` (dort noch umzustellen).
6. **Search Console und Bing Webmaster Tools:** Domain-Property per DNS bestätigen, Sitemap
   `https://handball-intelligence.com/sitemap.xml` einreichen, Einstellung «Search generative AI» auf
   Include lassen. In Bing ebenfalls die Sitemap einreichen.
7. **KI-Crawler beim CDN:** Eine Bot-Sperre des CDN (zum Beispiel die KI-Bot-Sperre bei Cloudflare)
   ausschalten, sonst gilt robots.txt nicht.
8. **Alte Domain:** Falls `handball-ai.ch` je öffentlich war: 301 eins zu eins auf die neue Domain,
   mindestens ein Jahr, besser dauerhaft; in der Search Console die Adressänderung einreichen
   ([Google](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes)).
9. **Nach dem ersten Tag:** in der Search Console die Seitenindexierung und den hreflang-Bericht
   ansehen, eine Stichprobe mit dem URL-Prüftool machen (Start, ein Ratgeber, Fakten).

## 7. KI-Crawler

**Entschieden von Lukas am 13. November 2026: erlaubt.** `robots.txt` erlaubt allen alles und nennt
ausdrücklich Googlebot, Bingbot, Applebot, GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot,
Claude-SearchBot, Claude-User, PerplexityBot, Perplexity-User, Google-Extended, Applebot-Extended,
CCBot, meta-externalagent und meta-webindexer (Namen aus den Dokumentationen der Betreiber, Abschnitt
2.5; `src/app/robots.ts`). Die App liegt auf ihrem eigenen Host (`app.`) und hat ihre eigenen
robots-Regeln; die Website kann sie nicht ausschliessen und muss es auch nicht.

**Falls sich das ändert:** `Disallow: /` für die Trainings-Crawler `GPTBot`, `ClaudeBot`,
`Google-Extended`, `Applebot-Extended`, `CCBot`, `meta-externalagent` (ab Februar 2027 zusätzlich
`__usage_ai-training` für Microsoft). Suche und Zitate bleiben dann erhalten, Gemini-Grounding fällt weg.

## 8. Messung

Keine Skripte eingebaut. Zwei datensparsame Möglichkeiten, Entscheid bei Lukas:

1. **Server-Logs auswerten, zum Beispiel mit GoAccess** ([goaccess.io](https://goaccess.io)): kein
   JavaScript, keine Cookies, nichts im Browser. IP-Adressen lassen sich kürzen (`--anonymize-ip`).
   Zeigt auch, welche Crawler (Googlebot, OAI-SearchBot, ClaudeBot, PerplexityBot) wie oft kommen.
   Braucht Zugang zu den Logs des Hosts.
2. **Plausible, selbst gehostet oder in der EU** ([Datenpolitik](https://plausible.io/data-policy)):
   keine Cookies, ein Tages-Hash statt IP, Daten in der EU. Braucht ein kleines Skript auf der Seite
   und eine Zeile in der Datenschutzerklärung; ob das nach DSG ohne Einwilligung geht, sagt nur der
   Anbieter, nicht eine Behörde.

Dazu kostenlos und ohne etwas auf der Seite: **Google Search Console** (Klicks, Impressionen,
Positionen je Seite und Suchbegriff, dazu ein Bericht zu generativer KI) und **Bing Webmaster Tools**.

**Messplan: Zahlen nach drei Monaten** (ab Freischaltung der Domain in der Search Console)

| Frage | Zahl | Quelle | Woran man sieht, dass es wirkt |
|---|---|---|---|
| Wird die Seite gefunden? | indexierte Seiten von 100 | Search Console, Seitenindexierung | über 90 indexiert, keine wegen hreflang- oder Canonical-Fehlern ausgeschlossen |
| Wofür? | Impressionen und Klicks je Ratgeber | Search Console, Leistung | jeder Ratgeber mit Impressionen für seine Frage («handballspiel filmen», «wurfquote berechnen», «einwilligung video verein»); Klickrate über 3 % auf Positionen 1 bis 10 |
| Romandie und Englisch? | Impressionen auf `/fr/` und `/en/` | Search Console, nach Land und Seite | fr-Seiten mit Impressionen aus der Schweiz, nicht die de-Fassung für fr-Suchen (hreflang greift) |
| KI-Assistenten? | Abrufe durch OAI-SearchBot, Claude-SearchBot, PerplexityBot; Besuche mit Herkunft chatgpt.com, perplexity.ai, claude.ai | Server-Logs; Bericht «Generative AI» in der Search Console | regelmässige Abrufe von `/fakten/`, `/llms.txt` und Ratgebern; erste Besuche über KI-Antworten |
| Führt es zum Produkt? | Klicks auf «Kostenlos starten» und das Team-Feld von Ratgeber- und Faktenseiten | App: Aufrufe von `/einstieg` mit Herkunft der Website (Referrer) | messbarer Anteil der Einstiege kommt von Ratgebern |
| Stichprobe von Hand | Frage an ChatGPT, Claude, Perplexity, Google: «Wie filme ich ein Handballspiel mit dem Handy?», «Was ist Handball Intelligence?» | einmal im Monat, Bildschirmfoto | die Website wird genannt; die Antwort zum Produkt stimmt mit `/fakten/` überein |

## 9. «Über uns»

Neue Seite `/ueber-uns/` (de, fr, en) aus der Vision von Lukas, in «wir», ohne Namen: warum es uns
gibt (Videoanalyse war etwas für Profis; die Trainerin am Samstagabend, die am Montag wieder im Büro
ist), für wen (Ehrenamt, Junioren bis 1. Liga, wenige Schritte, drei Dinge statt hundert Zahlen),
ehrlich über Grenzen (die Analyse schlägt vor, der Mensch bestätigt), das Video gehört dem Verein
(Einwilligung per Link, kein Datenverkauf, keine Tracker, Kommunikation bleibt im Gruppenchat), aus der
Schweiz mit handball.ch, wohin es gehen soll (mehr selbst erkennen, zuerst die Tore; bis dahin fragt
sie). Dazu der Hallenplan und ein Bild aus der App (Beispieldaten). Kurzer Abschnitt «Wer dahinter
steht» auf Start und Fakten, ein Satz in `llms.txt`. Die Kontaktseite heisst jetzt «Kontakt» und
verweist auf «Über uns»; die Grundsätze stehen auf «Über uns».

**Braucht Lukas** (würde die Seite glaubwürdiger machen, steht absichtlich nicht drauf):
- Wer hinter dem Produkt steht: Namen, Rolle, Bezug zum Handball (selbst Trainer, Spieler, Verein), mit Einverständnis.
- Ort und Gründungsjahr, Rechtsform und Adresse (auch fürs Impressum: `NEXT_PUBLIC_COMPANY_*`).
- Ein Pilotverein, der genannt werden darf, und ein Satz einer echten Trainerin oder eines Trainers, schriftlich freigegeben.
- Ein eigenes Foto einer Aufnahme in einer echten Halle (Handy auf dem Stativ an der Mittellinie), ohne erkennbare Personen oder mit deren Einwilligung.
- Zahlen erst, wenn sie stimmen und gezeigt werden dürfen (Teams, analysierte Spiele).

## 10. Lighthouse vorher und nachher

Lighthouse 12, Handy, simuliert gedrosselt, mit komprimierendem Server (`npx serve out`). Reihenfolge
Leistung / Barrierefreiheit / Best Practices / SEO.

| Seite | Vorher (Stand main) | Nachher |
|---|---|---|
| Start `/de/` | 96 / 100 / 100 / 100, LCP 2.7 s, CLS 0 | 97 / 100 / 100 / 100, LCP 2.6 s, CLS 0 |
| Ratgeber `/de/ratgeber/handballspiel-filmen/` | gab es nicht | 98 / 100 / 100 / 100, LCP 2.4 s |
| Fakten `/de/fakten/` | gab es nicht | 98 / 100 / 100 / 100, LCP 2.4 s |
| Über uns `/de/ueber-uns/` | gab es nicht (Platzhalter auf «Über uns und Kontakt») | 98 / 100 / 100 / 100, LCP 2.4 s |
| Ratgeber Einwilligung fr | gab es nicht | 98 / 100 / 100 / 100 |

## 11. Prüfungen, die die CI fährt (Stand nach der letzten Änderung)

| Schritt | Ergebnis |
|---|---|
| `uv run ruff check .`, `ruff format --check .` | sauber |
| `uv run lint-imports` | 3 Verträge eingehalten |
| `make typecheck-py` (mypy) | keine Fehler in 369 Dateien |
| Generatoren `--check` (court, plans, `make_demo.py`) | aktuell |
| `uv run pytest apps packages -n auto` | 390 bestanden, 273 übersprungen (brauchen die Datenbank des Stack-Jobs; lokal nicht gestartet) |
| `pnpm lint`, `pnpm circular`, `pnpm typecheck` | sauber |
| `pnpm test` | web 217, site 24, court 20, client-core 8, tactics 8, mobile 4: alle bestanden |
| `pnpm --filter @handball/site build` | sauber, 100 Adressen in der Sitemap, 46 Weiterleitungsseiten |
| `pnpm --filter @handball/web build` | sauber (Web unverändert, zur Sicherheit gebaut) |
| Nicht lokal gefahren | Migrationen (Postgres), Container-Build und Trivy, Stack mit Playwright: nichts davon ist von der Website berührt |

## 12. Was ich nicht prüfen konnte

- Suchvolumen (kein Werkzeug); die Fragen stützen sich auf belegte Formulierungen, nicht auf Zahlen.
- Das SHV-Informationsblatt zu aufgezeichneten Spielen und die SHV-Datenschutzvorlage (HTTP 503).
- Googles Rich Results Test und den schema.org Validator online (geprüft wurde lokal gegen das
  aktuelle schema.org-Vokabular und die Pflichtfelder aus Googles Dokumentation).
- Ob KI-Assistenten die Seite wirklich aufnehmen: geht erst, wenn sie unter der echten Domain online ist.
- Die Links in die App (`/einstieg`, `/login`) und das Verhalten der echten Server-Weiterleitungen.
- Französisch und Englisch sind von mir übertragen, nicht von einer Muttersprachlerin gegengelesen.

## 13. Das muss Lukas tun oder entscheiden

1. **Domain im übrigen Repo** umstellen lassen (Tabelle in Abschnitt 6) und die Liste «Vor dem Livegang» abarbeiten.
2. **Google Search Console und Bing Webmaster Tools** einrichten, Sitemap einreichen.
3. **Messung** wählen: Server-Logs (GoAccess) oder Plausible, oder nur Search Console (Abschnitt 8).
4. **«Über uns»** ergänzen, wo es Namen und Zahlen braucht (Abschnitt 9, «Braucht Lukas»).
5. **Preise** final machen; dann `PRICES_FINAL = true` in `src/lib/site.ts` (der Preis geht dann auch
   in die strukturierten Daten) und «noch nicht endgültig» von den Seiten nehmen (Q-SITE-1).
6. **Rechtstexte** prüfen lassen (AGB, Datenschutz, Impressum; Firmenangaben per Build-Variable), den
   Speicherort bestätigen (Q-SITE-4) und danach «vorgesehen» entfernen.
7. **Einwilligungs-Ratgeber** von einer Fachperson gegenlesen lassen, das SHV-Infoblatt einarbeiten.
8. **fr und en** gegenlesen lassen (Romandie zuerst).
