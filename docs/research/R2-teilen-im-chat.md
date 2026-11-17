# R2: Teilen im Teamchat

Recherche zu K20 (Teilen über WhatsApp), Stand November 2026. Frage: Wie zeigen WhatsApp,
Signal, Telegram, iMessage und Instagram einen Link, was machen gute Sport-Apps beim Teilen,
und welche Formate werden im Chat wirklich angeschaut? Am Ende: was wir daraus bauen.

## 1. Wie die Chats einen Link zeigen

| | Wer holt die Vorschau | Was gelesen wird | Bild | Video |
|---|---|---|---|---|
| **WhatsApp** | Absender-Gerät beim Tippen (GET, User-Agent `WhatsApp/2.x`, `Accept-Language` des Empfängers) | `og:title`, `og:description`, `og:url`, `og:image` (absolut), im `<head>` und dort in den ersten 300 KB des HTML | gross ab 300 px Breite, Seitenverhältnis bis 4:1, Datei unter 600 KB (offiziell; in der Praxis zuverlässig erst unter etwa 300 KB). Sonst kleines quadratisches Vorschaubild | kein Abspielen im Chat, nur Bild und Titel |
| **Signal** | Absender-App selbst, über einen Proxy, der die IP verbirgt; nur HTTPS | Open Graph; die Android-App ruft mit der Kennung `WhatsApp/2` ab (Quellcode `LinkPreviewRepository`) | grosses Bild wie WhatsApp | nein |
| **Telegram** | Telegram-Server | Open Graph, sonst `<title>` | gross ab etwa 200 × 200 px, breite Bilder als grosse Karte, `og:site_name` steht fett über dem Titel | YouTube und ähnliches eingebettet; für eigene MP4 nicht verlässlich |
| **iMessage** | Absender-Gerät, ohne JavaScript, ohne Meta-Weiterleitung | `og:title` (ohne Marke), `og:site_name`, `og:image`, `og:video` | Bild mindestens 900 px breit, HTML höchstens 1 MB, Bild + Icon + Video zusammen höchstens 10 MB | **ja**: `og:video` mit direkter, herunterladbarer MP4 spielt im Chat automatisch ohne Ton; HLS braucht einen Tipp |
| **Instagram DM** | Meta-Crawler, gleicher Cache wie Facebook (rund 30 Tage) | Open Graph; ohne `og:image` nur Text | wie Facebook, 1200 × 630 | nein |

Gemeinsame Punkte:

- **Alles muss im Server-HTML stehen.** Kein Chat führt JavaScript aus (Apple sagt es
  ausdrücklich). Next.js streamt Metadaten für normale Browser in den Body; für bekannte Bots
  (WhatsApp, facebookexternalhit, Twitterbot, Slackbot …) setzt es sie in den `<head>`. Signal
  gibt sich als WhatsApp aus, Telegram als «TelegramBot (like TwitterBot)»: beide landen in der
  blockierenden Variante. Prüfen mit einem Skript, das die Seite mit diesen Kennungen abruft.
- **Vorschau wird gecacht.** WhatsApp und Instagram merken sich die Vorschau beim ersten Senden;
  ein neues Bild erscheint in alten Nachrichten nicht. Neue Bild-URL (z. B. `?v=2`) bei neuer
  Gestaltung, damit neue Nachrichten das neue Bild holen.
- **Der Crawler ist kein Zuschauer.** Jeder Abruf der Vorschau würde sonst als «geöffnet» zählen.
- **Bildtext liest sich klein.** Apple rät von Text im Bild ab, weil das Bild je nach Gerät
  klein erscheint. Für uns heisst das: wenige, sehr grosse Elemente (Resultat, Minute, Zahl),
  keine Sätze im Bild; der Satz gehört in `og:title`.
- **Quadrat mitdenken.** WhatsApp zeigt das kleine Vorschaubild (wenn das grosse nicht passt,
  bei Antworten, auf manchen Geräten) als Quadrat aus der Mitte. Das Wichtigste gehört in die
  mittleren 630 × 630 px des 1200 × 630-Bildes.
- **Titel kurz, Beschreibung eine Zeile.** WhatsApp zeigt den Titel fett in höchstens zwei
  Zeilen, die Beschreibung in ein bis zwei Zeilen (rund 80 Zeichen genügen). Keine Marke im
  Titel; die gehört in `og:site_name`.

## 2. Was gute Sport-Apps beim Teilen machen

- **Veo:** «Teilen» über dem Video: WhatsApp, Facebook, X, E-Mail oder Link kopieren. Empfänger
  sehen Vorschaubild und Titel und schauen ohne Konto; nur die schon geschnittenen Clips, nur
  ansehen, kein Herunterladen.
- **Hudl:** Highlights als Link oder auf Facebook und X mit einem Klick; öffentlich oder «nicht
  gelistet» (nur wer den Link hat). Ganze Spiele lassen sich nicht öffentlich einbetten.
- **Strava:** teilt nicht den Link, sondern ein **Bild**: «Sticker Stats» legt Zahlen und Karte
  als transparenten Sticker über ein eigenes Foto, direkt in Instagram Stories; verborgene Werte
  erscheinen nicht. Das Bild ist die Werbung, der Link ist Nebensache.
- **Spond:** Einladung über einen Gruppenlink, den man im bestehenden Chat teilt; der Chat
  bleibt der Ort, Spond liefert den Link.
- **FotMob, Sportnews:** teilen den Link der Spielseite über das System-Teilen; die Vorschau
  zeigt Teams und Resultat. Andere (z. B. Mingle Sport) bauen eine Resultatkarte als Bild.

Muster: ein einziger «Teilen»-Knopf, dahinter das System-Teilen des Telefons, der Empfänger
braucht kein Konto, nur ansehen, und wo es um Stolz und Gesprächsstoff geht (Resultat, Leistung)
ein fertiges Bild statt eines Links.

## 3. Welche Formate im Chat angeschaut werden

Belastbare Zahlen für Teamchats gibt es nicht; die folgende Einschätzung folgt aus der Mechanik
der Chats:

- **Bild:** wird ohne Tipp im Chat gross angezeigt, wird von allen gesehen (auch von denen, die
  nichts öffnen). Bestes Format für Resultat und «drei Dinge» nach dem Spiel.
- **Kurzes Video als Datei:** wird je nach Einstellung erst geladen; spielt nach einem Tipp im
  Chat. Gut für eine einzelne Szene, aber jede Datei verlässt unsere Kontrolle (kein Ablauf,
  kein Sperren, keine Rückennummern statt Namen mehr steuerbar) und wird weitergeleitet.
- **Link mit grosser Vorschau:** braucht einen Tipp und öffnet den Browser, dafür bleibt der
  Inhalt widerrufbar, läuft ab, zählt Aufrufe und kann mehrere Szenen der Reihe nach zeigen.
  Für Szenen und Sammlungen das richtige Format, wenn die Vorschau neugierig macht.
- **Text:** Der Begleitsatz entscheidet, ob getippt wird («Schaut euch Szene 2 bis Donnerstag
  an»). Kurz, eine Aufforderung, höchstens ein Emoji.

## 4. Empfehlungen für Handball Intelligence

1. **Jede geteilte Seite hat eine perfekte Vorschau:** `og:title` macht neugierig und nennt das
  Konkrete («Szene 23. Min: Gegenstoss», «TV Thalwil 28:24 SG Horgen»), `og:description` in
  einer Zeile (Team, Anzahl Szenen, Länge, «ohne Konto ansehen»), `og:site_name` = Verein,
  `og:image` absolut, 1200 × 630, PNG unter 300 KB, flache Farben, Vereinsfarben, das Wichtige
  in der Mitte. Dazu `twitter:card = summary_large_image`. Keine Gesichter, keine Videobilder,
  keine Namen: nur Teamnamen, Resultat, Minute, Zonen, Spielzug-Skizze.
2. **Highlights mit `og:video`:** direkte MP4 (`/reel.mp4`) mit Typ und Grösse, damit iMessage
  sie im Chat abspielt; der Server muss dafür Byte-Bereiche (Range) können, sonst spielt Safari
  die Datei auch auf der Seite nicht.
3. **Ein Teilen-Knopf überall** (Szene, Sammlung, Highlights, Spielzug, Spielbericht):
  auf dem Telefon das System-Teilen mit fertigem Text, daneben «In WhatsApp teilen»
  (`https://wa.me/?text=…`) und «Link kopieren». Ablauf wählbar, Vorgabe 30 Tage (SPEC 7.8),
  danach sichtbar: wie oft geöffnet, gültig bis, «Link sperren». Ein schon bestehender Link
  wird wieder angeboten statt einen zweiten zu machen.
4. **Die Spielkarte als Bild:** nach dem Spiel ein quadratisches PNG (1080 × 1080) mit
  Resultat und den drei Dingen, über das System-Teilen direkt als Bild in den Chat (Web Share
  mit Datei, sonst herunterladen). Ohne Rückennummern und Namen, deshalb auch für Junioren.
5. **Persönliche Szenen:** «Deine Szenen» eines Spielers als Sammlung «Szenen #7» teilen, nur
  mit Rückennummer; der Spieler bekommt genau seinen Link.
6. **Die Seite hinter dem Link:** schnell, fürs Telefon gebaut, Video spielt im Bild
  (`playsinline`), vorherige und nächste Szene, kein App-Rahmen, keine Anmeldung, unten dezent
  «Erstellt mit Handball Intelligence» mit Link zur Website.
7. **Ehrliche Zahlen:** Abrufe von Vorschau-Crawlern zählen nicht als «geöffnet».
8. **Jugendschutz bleibt:** Junioren-Teams teilen öffentlich nur Spielzüge (und die
  Spielkarte ohne Nummern als Bild); Highlights nur mit der Einwilligung «Highlights öffentlich»
  aller gezeigten Spieler. Der Teilen-Dialog sagt das, statt still zu scheitern.
9. **Später, nicht jetzt:** einzelne Szene als MP4-Datei (braucht Schnitt in der Pipeline),
  «Spiel in 60 Sekunden» automatisch, Aufgabe «schau bis Donnerstag» mit Erinnerung.

## Quellen

- WhatsApp, Link-Vorschau (Business-Doku): https://developers.facebook.com/documentation/business-messaging/whatsapp/link-previews/
- Apple TN3156 «Create rich previews for Messages» (früher TN2444): https://developer.apple.com/documentation/technotes/tn3156-create-rich-previews-for-messages
- Signal, Link-Vorschau über Proxy, nur HTTPS: https://www.androidpolice.com/2019/02/06/signal-adds-optional-link-previews-for-imgur-instagram-reddit-and-youtube/
- Telegram, Link-Vorschau: https://telegram.org/blog/link-preview
- Telegram, Vorschau mit Open Graph, Mindestgrösse: https://wildandfreetools.com/blog/meta-tags-social-media-whatsapp-discord
- Instagram DM und Open Graph: https://creatorflow.so/blog/instagram-dm-link-preview-og-image/ und https://link.boo/guides/instagram-link-preview-not-showing
- Cache der Vorschau, `?v=2`: https://wildandfreetools.com/blog/whatsapp-link-preview-wrong-image-fix und https://hirevire.com/helpdesk/fix-whatsapp-link-preview-showing-old-job-title-g3d27
- WhatsApp und Bildgrösse 300 KB in der Praxis: https://screenhance.com/blog/og-image-size-guide
- Next.js, blockierende Metadaten für Bots (`htmlLimitedBots`): https://nextjs.org/docs/app/api-reference/config/next-config-js/htmlLimitedBots
- Web Share API mit Dateien: https://web.dev/articles/web-share
- WhatsApp «Click to Chat» (`wa.me/?text=`, Text nur vorausgefüllt, gesendet wird von Hand): https://bird.com/explained/whatsapp/what-is-a-whatsapp-click-to-chat-link
- Veo, Aufnahmen teilen: https://support.veo.com/hc/en-us/articles/4451490513169
- Hudl, Programm bewerben und teilen: https://www.hudl.com/blog/how-to-promote-your-athletic-program-with-hudl
- Strava «Sticker Stats»: https://support.strava.com/en-us/articles/17718841-how-do-i-share-my-strava-activity-to-instagram-stories-as-a-transparent-sticker und https://www.bikeradar.com/news/strava-sticker-stats-spring-2025-updates
- Spond, Einladen per Link: https://www.spond.com/invites-reminders/
- FotMob, Teilen der Spielseite: https://lazyweb.com/canvas/flows/fotmob/share-match
