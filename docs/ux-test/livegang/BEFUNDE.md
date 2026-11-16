# Livegang: Befunde auf der echten Umgebung

Gesammelt ab 2026-11-16 auf https://app.handball-intelligence.com (Azure «hb-stg») und
https://handball-intelligence.com (Cloudflare). **Erst sammeln, dann in einem Rutsch beheben**
(Wunsch von Lukas). Quelle: L = Ende-zu-Ende-Test vom 16.11. (Handy 390 und Desktop 1280,
synthetisches Video), K = Lukas beim Probieren.

Schwere: 🔴 blockiert einen Trainer · 🟡 stört · ⚪ Kleinigkeit. Stand: offen, behoben (wo).

## Blockiert

| # | Befund | Wo | Stand |
|---|---|---|---|
| L1 | Upload aus dem Browser scheitert: der Video-Bucket `handball-testdata` erlaubte Uploads (CORS) nur für `test.` | R2 | behoben 16.11. (CORS für `app.` gesetzt), von Lukas nachprüfen |
| L2 | Kein Mail-Versand (`HB_EMAIL_BACKEND=console`), aber die App sagt «Link geschickt» / «Du bekommst eine Mail»: Einstieg «Speichern», «Passwort vergessen», «Ohne Passwort anmelden», Video-Tab und Fortschritt. Wer über «Speichern» kommt, hat ein Konto ohne Passwort und keinen Weg hinein (`services/auth.py` `start`) | App, Mail | offen: braucht einen Mail-Anbieter (Entscheid Lukas), bis dahin ehrliche Sätze |
| L3 | Sporadisch HTTP 500 (8×): `POST /v1/auth/login` 2×, `POST /v1/auth/magic-link` 1×, `GET /v1/public/teams` 5×; die Wiederholung klappt. Der Einstieg zeigt dann «handball.ch antwortet gerade nicht» (`entry-view.tsx` zeigt jeden Fehler ausser 429 so) | API | offen: Ursache in den Azure-Logs suchen (Verdacht: Rate-Limiter/Redis nach dem Aufwachen) |

## Stört

| # | Befund | Wo | Stand |
|---|---|---|---|
| L4 | Nach gescheitertem Upload gleichzeitig «Upload läuft» und «Upload fehlgeschlagen»; nach Neuladen nur «Upload läuft» ohne Knopf; «Fortsetzen» hilft nicht | Video-Tab | offen |
| L5 | Prüfen, «Wenn du magst: 6 weitere Fragen»: sechsmal «Wer ist das?» bei leerem Kader (nur «Andere aus dem Kader» / «Weiss nicht»); nach sechsmal «Weiss nicht» wieder «Frage 1 von 6»: Endlosschleife. Gelber Kasten teils neben dem Spieler | Prüfen | offen |
| L6 | Spiel- und Zahlen-Tab nach dem Prüfen ohne Tore fast leer (blauer Kopf ohne Resultat, nur «Highlights teilen»); der Satz «keine Tore gefunden» steht nur im Video-Tab | Spiel | offen |
| L7 | Nach «Verein löschen» Sackgasse auf /onboarding: kein Kontomenü, kein Abmelden, kein «Konto löschen» (liegt nur unter `/app/[orgId]/me/data`) | Onboarding | offen |
| L8 | Website über `http://` ohne Weiterleitung auf `https://` | Cloudflare | behoben 16.11. («Always Use HTTPS») |

## Kleinigkeiten

| # | Befund | Wo | Stand |
|---|---|---|---|
| L9 | Rechtslinks im Einstieg zeigen kurz relativ auf `app…/de/agb` (404), bis `/v1/public/config` geladen ist (`entry-view.tsx`, `legal()`) | Einstieg | offen |
| L10 | Der Console-Mailer schreibt Mailtext samt Anmelde- und Reset-Token ins Log (`core/email.py`) | API | offen |
| L11 | App: `/robots.txt`, `/sitemap.xml`, `/favicon.ico` antworten 404 | App | offen |
| L12 | Einstieg ohne direkten Weg zu «Konto mit Passwort» (nur über «Anmelden»); Logo auf der Login-Seite doppelt | Einstieg, Login | offen |
| L13 | «Alles geprüft» listet nur den Anwurf (ohne Zeit), nicht das Feld; die Glocke meldet weiter «2 Fragen an dich» | Prüfen, Glocke | offen |
| L14 | «E-Mail noch nicht bestätigt» nur versteckt unter Ich › Profil | Profil | offen |
| L15 | Torschützen beim ersten Abruf einige Sekunden «kommen gleich» | Start | offen |
| L16 | Anpfiff-Feld im US-Format «11/16/2026, 02:23 PM» (vermutlich nur im Test-Browser) | Neues Spiel | prüfen |

## Aufräumen

- Testkonto `e2e-entry-…@example.com` (passwortlos, ohne Verein, aus «Speichern») liegt noch in der
  Datenbank; ohne Mail kommt niemand hinein. Bei Gelegenheit löschen.
- Cloudflare-DNS: `test.handball-intelligence.com` (CNAME) und `asuid.test…` (TXT) zeigen ins Leere.

## Von Lukas beim Probieren

| # | Befund | Wo | Stand |
|---|---|---|---|
