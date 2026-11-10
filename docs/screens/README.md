# Screenshots der App

Stand: 10. November 2026 (main nach PR 33). Lokaler Stack mit dem Demo-Verein aus
`scripts/seed.py` (synthetische Testvideos), erfundene Namen. Offizielle Daten (handball.ch)
und Wurf-Vorschläge kommen aus aufgezeichneten Testantworten, weil der lokale Stack
handball.ch nicht erreicht.

Jeder Screen als Desktop (1440 px) und Phone (390 px), die ganze Seite. Neu erzeugen, bei
laufendem Stack (`make up`, `make seed`) und Web-App:
`cd apps/web && npx playwright test -c screens.config.ts`, dann
`python3 docs/screens/build.py` (wandelt in JPEG und schreibt diese Seite).

## Inhalt

- [Einstieg](#einstieg) (9 Screens)
- [Trainer/in](#trainerin) (42 Screens)
- [Spieler/in](#spielerin) (9 Screens)
- [Eltern](#eltern) (4 Screens)
- [Öffentlich](#öffentlich) (2 Screens)

## Einstieg

Anmelden, registrieren und der erste Start mit der Teamsuche auf handball.ch.

### anmelden

<a href="1-einstieg/01-anmelden-desktop.jpg"><img src="1-einstieg/01-anmelden-desktop.jpg" width="560" alt="anmelden, desktop"></a> <a href="1-einstieg/01-anmelden-phone.jpg"><img src="1-einstieg/01-anmelden-phone.jpg" width="180" alt="anmelden, phone"></a>

### registrieren

<a href="1-einstieg/02-registrieren-desktop.jpg"><img src="1-einstieg/02-registrieren-desktop.jpg" width="560" alt="registrieren, desktop"></a> <a href="1-einstieg/02-registrieren-phone.jpg"><img src="1-einstieg/02-registrieren-phone.jpg" width="180" alt="registrieren, phone"></a>

### passwort vergessen

<a href="1-einstieg/03-passwort-vergessen-desktop.jpg"><img src="1-einstieg/03-passwort-vergessen-desktop.jpg" width="560" alt="passwort vergessen, desktop"></a> <a href="1-einstieg/03-passwort-vergessen-phone.jpg"><img src="1-einstieg/03-passwort-vergessen-phone.jpg" width="180" alt="passwort vergessen, phone"></a>

### onboarding mannschaft suchen

<a href="1-einstieg/04-onboarding-mannschaft-suchen-desktop.jpg"><img src="1-einstieg/04-onboarding-mannschaft-suchen-desktop.jpg" width="560" alt="onboarding mannschaft suchen, desktop"></a> <a href="1-einstieg/04-onboarding-mannschaft-suchen-phone.jpg"><img src="1-einstieg/04-onboarding-mannschaft-suchen-phone.jpg" width="180" alt="onboarding mannschaft suchen, phone"></a>

### onboarding suchergebnis

<a href="1-einstieg/05-onboarding-suchergebnis-desktop.jpg"><img src="1-einstieg/05-onboarding-suchergebnis-desktop.jpg" width="560" alt="onboarding suchergebnis, desktop"></a> <a href="1-einstieg/05-onboarding-suchergebnis-phone.jpg"><img src="1-einstieg/05-onboarding-suchergebnis-phone.jpg" width="180" alt="onboarding suchergebnis, phone"></a>

### onboarding verein von hand

<a href="1-einstieg/06-onboarding-verein-von-hand-desktop.jpg"><img src="1-einstieg/06-onboarding-verein-von-hand-desktop.jpg" width="560" alt="onboarding verein von hand, desktop"></a> <a href="1-einstieg/06-onboarding-verein-von-hand-phone.jpg"><img src="1-einstieg/06-onboarding-verein-von-hand-phone.jpg" width="180" alt="onboarding verein von hand, phone"></a>

### onboarding team

<a href="1-einstieg/07-onboarding-team-desktop.jpg"><img src="1-einstieg/07-onboarding-team-desktop.jpg" width="560" alt="onboarding team, desktop"></a> <a href="1-einstieg/07-onboarding-team-phone.jpg"><img src="1-einstieg/07-onboarding-team-phone.jpg" width="180" alt="onboarding team, phone"></a>

### onboarding kader

<a href="1-einstieg/08-onboarding-kader-desktop.jpg"><img src="1-einstieg/08-onboarding-kader-desktop.jpg" width="560" alt="onboarding kader, desktop"></a> <a href="1-einstieg/08-onboarding-kader-phone.jpg"><img src="1-einstieg/08-onboarding-kader-phone.jpg" width="180" alt="onboarding kader, phone"></a>

### onboarding einladen

<a href="1-einstieg/09-onboarding-einladen-desktop.jpg"><img src="1-einstieg/09-onboarding-einladen-desktop.jpg" width="560" alt="onboarding einladen, desktop"></a> <a href="1-einstieg/09-onboarding-einladen-phone.jpg"><img src="1-einstieg/09-onboarding-einladen-phone.jpg" width="180" alt="onboarding einladen, phone"></a>

## Trainer/in

Demo-Verein mit analysierten Testvideos: Übersicht, Spiele, Match-Arbeitsplatz Schritt für Schritt, Analyse, Bibliothek, Training, Team, Einstellungen.

### uebersicht

<a href="2-trainer/01-uebersicht-desktop.jpg"><img src="2-trainer/01-uebersicht-desktop.jpg" width="560" alt="uebersicht, desktop"></a> <a href="2-trainer/01-uebersicht-phone.jpg"><img src="2-trainer/01-uebersicht-phone.jpg" width="180" alt="uebersicht, phone"></a>

### spielplan

<a href="2-trainer/02-spielplan-desktop.jpg"><img src="2-trainer/02-spielplan-desktop.jpg" width="560" alt="spielplan, desktop"></a> <a href="2-trainer/02-spielplan-phone.jpg"><img src="2-trainer/02-spielplan-phone.jpg" width="180" alt="spielplan, phone"></a>

### neues spiel

<a href="2-trainer/03-neues-spiel-desktop.jpg"><img src="2-trainer/03-neues-spiel-desktop.jpg" width="560" alt="neues spiel, desktop"></a> <a href="2-trainer/03-neues-spiel-phone.jpg"><img src="2-trainer/03-neues-spiel-phone.jpg" width="180" alt="neues spiel, phone"></a>

### spiel vor dem anpfiff

<a href="2-trainer/04-spiel-vor-dem-anpfiff-desktop.jpg"><img src="2-trainer/04-spiel-vor-dem-anpfiff-desktop.jpg" width="560" alt="spiel vor dem anpfiff, desktop"></a> <a href="2-trainer/04-spiel-vor-dem-anpfiff-phone.jpg"><img src="2-trainer/04-spiel-vor-dem-anpfiff-phone.jpg" width="180" alt="spiel vor dem anpfiff, phone"></a>

### spiel video spielfeld

<a href="2-trainer/05-spiel-video-spielfeld-desktop.jpg"><img src="2-trainer/05-spiel-video-spielfeld-desktop.jpg" width="560" alt="spiel video spielfeld, desktop"></a> <a href="2-trainer/05-spiel-video-spielfeld-phone.jpg"><img src="2-trainer/05-spiel-video-spielfeld-phone.jpg" width="180" alt="spiel video spielfeld, phone"></a>

### spiel video anwurf

<a href="2-trainer/06-spiel-video-anwurf-desktop.jpg"><img src="2-trainer/06-spiel-video-anwurf-desktop.jpg" width="560" alt="spiel video anwurf, desktop"></a> <a href="2-trainer/06-spiel-video-anwurf-phone.jpg"><img src="2-trainer/06-spiel-video-anwurf-phone.jpg" width="180" alt="spiel video anwurf, phone"></a>

### spiel video tore pruefen

<a href="2-trainer/07-spiel-video-tore-pruefen-desktop.jpg"><img src="2-trainer/07-spiel-video-tore-pruefen-desktop.jpg" width="560" alt="spiel video tore pruefen, desktop"></a> <a href="2-trainer/07-spiel-video-tore-pruefen-phone.jpg"><img src="2-trainer/07-spiel-video-tore-pruefen-phone.jpg" width="180" alt="spiel video tore pruefen, phone"></a>

### spiel video spieler zuordnen

<a href="2-trainer/08-spiel-video-spieler-zuordnen-desktop.jpg"><img src="2-trainer/08-spiel-video-spieler-zuordnen-desktop.jpg" width="560" alt="spiel video spieler zuordnen, desktop"></a> <a href="2-trainer/08-spiel-video-spieler-zuordnen-phone.jpg"><img src="2-trainer/08-spiel-video-spieler-zuordnen-phone.jpg" width="180" alt="spiel video spieler zuordnen, phone"></a>

### spiel video ereignisse

<a href="2-trainer/09-spiel-video-ereignisse-desktop.jpg"><img src="2-trainer/09-spiel-video-ereignisse-desktop.jpg" width="560" alt="spiel video ereignisse, desktop"></a> <a href="2-trainer/09-spiel-video-ereignisse-phone.jpg"><img src="2-trainer/09-spiel-video-ereignisse-phone.jpg" width="180" alt="spiel video ereignisse, phone"></a>

### spiel video wuerfe

<a href="2-trainer/10-spiel-video-wuerfe-desktop.jpg"><img src="2-trainer/10-spiel-video-wuerfe-desktop.jpg" width="560" alt="spiel video wuerfe, desktop"></a> <a href="2-trainer/10-spiel-video-wuerfe-phone.jpg"><img src="2-trainer/10-spiel-video-wuerfe-phone.jpg" width="180" alt="spiel video wuerfe, phone"></a>

### spiel video abwehrsysteme

<a href="2-trainer/11-spiel-video-abwehrsysteme-desktop.jpg"><img src="2-trainer/11-spiel-video-abwehrsysteme-desktop.jpg" width="560" alt="spiel video abwehrsysteme, desktop"></a> <a href="2-trainer/11-spiel-video-abwehrsysteme-phone.jpg"><img src="2-trainer/11-spiel-video-abwehrsysteme-phone.jpg" width="180" alt="spiel video abwehrsysteme, phone"></a>

### spiel video kommentare

<a href="2-trainer/12-spiel-video-kommentare-desktop.jpg"><img src="2-trainer/12-spiel-video-kommentare-desktop.jpg" width="560" alt="spiel video kommentare, desktop"></a> <a href="2-trainer/12-spiel-video-kommentare-phone.jpg"><img src="2-trainer/12-spiel-video-kommentare-phone.jpg" width="180" alt="spiel video kommentare, phone"></a>

### spiel video feedback

<a href="2-trainer/13-spiel-video-feedback-desktop.jpg"><img src="2-trainer/13-spiel-video-feedback-desktop.jpg" width="560" alt="spiel video feedback, desktop"></a> <a href="2-trainer/13-spiel-video-feedback-phone.jpg"><img src="2-trainer/13-spiel-video-feedback-phone.jpg" width="180" alt="spiel video feedback, phone"></a>

### spiel wuerfe vollbild

<a href="2-trainer/14-spiel-wuerfe-vollbild-desktop.jpg"><img src="2-trainer/14-spiel-wuerfe-vollbild-desktop.jpg" width="560" alt="spiel wuerfe vollbild, desktop"></a> <a href="2-trainer/14-spiel-wuerfe-vollbild-phone.jpg"><img src="2-trainer/14-spiel-wuerfe-vollbild-phone.jpg" width="180" alt="spiel wuerfe vollbild, phone"></a>

### spiel analyse uebersicht

<a href="2-trainer/15-spiel-analyse-uebersicht-desktop.jpg"><img src="2-trainer/15-spiel-analyse-uebersicht-desktop.jpg" width="560" alt="spiel analyse uebersicht, desktop"></a> <a href="2-trainer/15-spiel-analyse-uebersicht-phone.jpg"><img src="2-trainer/15-spiel-analyse-uebersicht-phone.jpg" width="180" alt="spiel analyse uebersicht, phone"></a>

### spiel analyse laufleistung

<a href="2-trainer/16-spiel-analyse-laufleistung-desktop.jpg"><img src="2-trainer/16-spiel-analyse-laufleistung-desktop.jpg" width="560" alt="spiel analyse laufleistung, desktop"></a> <a href="2-trainer/16-spiel-analyse-laufleistung-phone.jpg"><img src="2-trainer/16-spiel-analyse-laufleistung-phone.jpg" width="180" alt="spiel analyse laufleistung, phone"></a>

### spiel szenen

<a href="2-trainer/17-spiel-szenen-desktop.jpg"><img src="2-trainer/17-spiel-szenen-desktop.jpg" width="560" alt="spiel szenen, desktop"></a> <a href="2-trainer/17-spiel-szenen-phone.jpg"><img src="2-trainer/17-spiel-szenen-phone.jpg" width="180" alt="spiel szenen, phone"></a>

### spiel live erfassen

<a href="2-trainer/18-spiel-live-erfassen-desktop.jpg"><img src="2-trainer/18-spiel-live-erfassen-desktop.jpg" width="560" alt="spiel live erfassen, desktop"></a> <a href="2-trainer/18-spiel-live-erfassen-phone.jpg"><img src="2-trainer/18-spiel-live-erfassen-phone.jpg" width="180" alt="spiel live erfassen, phone"></a>

### spiel am spielfeldrand markieren

<a href="2-trainer/19-spiel-am-spielfeldrand-markieren-desktop.jpg"><img src="2-trainer/19-spiel-am-spielfeldrand-markieren-desktop.jpg" width="560" alt="spiel am spielfeldrand markieren, desktop"></a> <a href="2-trainer/19-spiel-am-spielfeldrand-markieren-phone.jpg"><img src="2-trainer/19-spiel-am-spielfeldrand-markieren-phone.jpg" width="180" alt="spiel am spielfeldrand markieren, phone"></a>

### spiel scouting

<a href="2-trainer/20-spiel-scouting-desktop.jpg"><img src="2-trainer/20-spiel-scouting-desktop.jpg" width="560" alt="spiel scouting, desktop"></a> <a href="2-trainer/20-spiel-scouting-phone.jpg"><img src="2-trainer/20-spiel-scouting-phone.jpg" width="180" alt="spiel scouting, phone"></a>

### matchblatt foto

<a href="2-trainer/21-matchblatt-foto-desktop.jpg"><img src="2-trainer/21-matchblatt-foto-desktop.jpg" width="560" alt="matchblatt foto, desktop"></a> <a href="2-trainer/21-matchblatt-foto-phone.jpg"><img src="2-trainer/21-matchblatt-foto-phone.jpg" width="180" alt="matchblatt foto, phone"></a>

### saison

<a href="2-trainer/22-saison-desktop.jpg"><img src="2-trainer/22-saison-desktop.jpg" width="560" alt="saison, desktop"></a> <a href="2-trainer/22-saison-phone.jpg"><img src="2-trainer/22-saison-phone.jpg" width="180" alt="saison, phone"></a>

### statistik matrix

<a href="2-trainer/23-statistik-matrix-desktop.jpg"><img src="2-trainer/23-statistik-matrix-desktop.jpg" width="560" alt="statistik matrix, desktop"></a> <a href="2-trainer/23-statistik-matrix-phone.jpg"><img src="2-trainer/23-statistik-matrix-phone.jpg" width="180" alt="statistik matrix, phone"></a>

### assistent

<a href="2-trainer/24-assistent-desktop.jpg"><img src="2-trainer/24-assistent-desktop.jpg" width="560" alt="assistent, desktop"></a> <a href="2-trainer/24-assistent-phone.jpg"><img src="2-trainer/24-assistent-phone.jpg" width="180" alt="assistent, phone"></a>

### bibliothek

<a href="2-trainer/25-bibliothek-desktop.jpg"><img src="2-trainer/25-bibliothek-desktop.jpg" width="560" alt="bibliothek, desktop"></a> <a href="2-trainer/25-bibliothek-phone.jpg"><img src="2-trainer/25-bibliothek-phone.jpg" width="180" alt="bibliothek, phone"></a>

### playlists

<a href="2-trainer/26-playlists-desktop.jpg"><img src="2-trainer/26-playlists-desktop.jpg" width="560" alt="playlists, desktop"></a> <a href="2-trainer/26-playlists-phone.jpg"><img src="2-trainer/26-playlists-phone.jpg" width="180" alt="playlists, phone"></a>

### playlist

<a href="2-trainer/27-playlist-desktop.jpg"><img src="2-trainer/27-playlist-desktop.jpg" width="560" alt="playlist, desktop"></a> <a href="2-trainer/27-playlist-phone.jpg"><img src="2-trainer/27-playlist-phone.jpg" width="180" alt="playlist, phone"></a>

### praesentationen

<a href="2-trainer/28-praesentationen-desktop.jpg"><img src="2-trainer/28-praesentationen-desktop.jpg" width="560" alt="praesentationen, desktop"></a> <a href="2-trainer/28-praesentationen-phone.jpg"><img src="2-trainer/28-praesentationen-phone.jpg" width="180" alt="praesentationen, phone"></a>

### praesentation bearbeiten

<a href="2-trainer/29-praesentation-bearbeiten-desktop.jpg"><img src="2-trainer/29-praesentation-bearbeiten-desktop.jpg" width="560" alt="praesentation bearbeiten, desktop"></a> <a href="2-trainer/29-praesentation-bearbeiten-phone.jpg"><img src="2-trainer/29-praesentation-bearbeiten-phone.jpg" width="180" alt="praesentation bearbeiten, phone"></a>

### szenensuche

<a href="2-trainer/30-szenensuche-desktop.jpg"><img src="2-trainer/30-szenensuche-desktop.jpg" width="560" alt="szenensuche, desktop"></a> <a href="2-trainer/30-szenensuche-phone.jpg"><img src="2-trainer/30-szenensuche-phone.jpg" width="180" alt="szenensuche, phone"></a>

### training plan

<a href="2-trainer/31-training-plan-desktop.jpg"><img src="2-trainer/31-training-plan-desktop.jpg" width="560" alt="training plan, desktop"></a> <a href="2-trainer/31-training-plan-phone.jpg"><img src="2-trainer/31-training-plan-phone.jpg" width="180" alt="training plan, phone"></a>

### training uebungen

<a href="2-trainer/32-training-uebungen-desktop.jpg"><img src="2-trainer/32-training-uebungen-desktop.jpg" width="560" alt="training uebungen, desktop"></a> <a href="2-trainer/32-training-uebungen-phone.jpg"><img src="2-trainer/32-training-uebungen-phone.jpg" width="180" alt="training uebungen, phone"></a>

### training spielzuege

<a href="2-trainer/33-training-spielzuege-desktop.jpg"><img src="2-trainer/33-training-spielzuege-desktop.jpg" width="560" alt="training spielzuege, desktop"></a> <a href="2-trainer/33-training-spielzuege-phone.jpg"><img src="2-trainer/33-training-spielzuege-phone.jpg" width="180" alt="training spielzuege, phone"></a>

### training aufgaben

<a href="2-trainer/34-training-aufgaben-desktop.jpg"><img src="2-trainer/34-training-aufgaben-desktop.jpg" width="560" alt="training aufgaben, desktop"></a> <a href="2-trainer/34-training-aufgaben-phone.jpg"><img src="2-trainer/34-training-aufgaben-phone.jpg" width="180" alt="training aufgaben, phone"></a>

### team kader

<a href="2-trainer/35-team-kader-desktop.jpg"><img src="2-trainer/35-team-kader-desktop.jpg" width="560" alt="team kader, desktop"></a> <a href="2-trainer/35-team-kader-phone.jpg"><img src="2-trainer/35-team-kader-phone.jpg" width="180" alt="team kader, phone"></a>

### team saisonverlauf spielerin

<a href="2-trainer/36-team-saisonverlauf-spielerin-desktop.jpg"><img src="2-trainer/36-team-saisonverlauf-spielerin-desktop.jpg" width="560" alt="team saisonverlauf spielerin, desktop"></a> <a href="2-trainer/36-team-saisonverlauf-spielerin-phone.jpg"><img src="2-trainer/36-team-saisonverlauf-spielerin-phone.jpg" width="180" alt="team saisonverlauf spielerin, phone"></a>

### team termine

<a href="2-trainer/37-team-termine-desktop.jpg"><img src="2-trainer/37-team-termine-desktop.jpg" width="560" alt="team termine, desktop"></a> <a href="2-trainer/37-team-termine-phone.jpg"><img src="2-trainer/37-team-termine-phone.jpg" width="180" alt="team termine, phone"></a>

### team abgleich handball ch

<a href="2-trainer/38-team-abgleich-handball-ch-desktop.jpg"><img src="2-trainer/38-team-abgleich-handball-ch-desktop.jpg" width="560" alt="team abgleich handball ch, desktop"></a> <a href="2-trainer/38-team-abgleich-handball-ch-phone.jpg"><img src="2-trainer/38-team-abgleich-handball-ch-phone.jpg" width="180" alt="team abgleich handball ch, phone"></a>

### team beitrittsanfragen

<a href="2-trainer/39-team-beitrittsanfragen-desktop.jpg"><img src="2-trainer/39-team-beitrittsanfragen-desktop.jpg" width="560" alt="team beitrittsanfragen, desktop"></a> <a href="2-trainer/39-team-beitrittsanfragen-phone.jpg"><img src="2-trainer/39-team-beitrittsanfragen-phone.jpg" width="180" alt="team beitrittsanfragen, phone"></a>

### einstellungen

<a href="2-trainer/40-einstellungen-desktop.jpg"><img src="2-trainer/40-einstellungen-desktop.jpg" width="560" alt="einstellungen, desktop"></a> <a href="2-trainer/40-einstellungen-phone.jpg"><img src="2-trainer/40-einstellungen-phone.jpg" width="180" alt="einstellungen, phone"></a>

### profil

<a href="2-trainer/41-profil-desktop.jpg"><img src="2-trainer/41-profil-desktop.jpg" width="560" alt="profil, desktop"></a> <a href="2-trainer/41-profil-phone.jpg"><img src="2-trainer/41-profil-phone.jpg" width="180" alt="profil, phone"></a>

### mitteilungen

<a href="2-trainer/42-mitteilungen-desktop.jpg"><img src="2-trainer/42-mitteilungen-desktop.jpg" width="560" alt="mitteilungen, desktop"></a> <a href="2-trainer/42-mitteilungen-phone.jpg"><img src="2-trainer/42-mitteilungen-phone.jpg" width="180" alt="mitteilungen, phone"></a>

## Spieler/in

Ein Spielerkonto, mit dem Kadereintrag verknüpft.

### uebersicht

<a href="3-spielerin/01-uebersicht-desktop.jpg"><img src="3-spielerin/01-uebersicht-desktop.jpg" width="560" alt="uebersicht, desktop"></a> <a href="3-spielerin/01-uebersicht-phone.jpg"><img src="3-spielerin/01-uebersicht-phone.jpg" width="180" alt="uebersicht, phone"></a>

### meine szenen

<a href="3-spielerin/02-meine-szenen-desktop.jpg"><img src="3-spielerin/02-meine-szenen-desktop.jpg" width="560" alt="meine szenen, desktop"></a> <a href="3-spielerin/02-meine-szenen-phone.jpg"><img src="3-spielerin/02-meine-szenen-phone.jpg" width="180" alt="meine szenen, phone"></a>

### termine

<a href="3-spielerin/03-termine-desktop.jpg"><img src="3-spielerin/03-termine-desktop.jpg" width="560" alt="termine, desktop"></a> <a href="3-spielerin/03-termine-phone.jpg"><img src="3-spielerin/03-termine-phone.jpg" width="180" alt="termine, phone"></a>

### team

<a href="3-spielerin/04-team-desktop.jpg"><img src="3-spielerin/04-team-desktop.jpg" width="560" alt="team, desktop"></a> <a href="3-spielerin/04-team-phone.jpg"><img src="3-spielerin/04-team-phone.jpg" width="180" alt="team, phone"></a>

### aufgaben

<a href="3-spielerin/05-aufgaben-desktop.jpg"><img src="3-spielerin/05-aufgaben-desktop.jpg" width="560" alt="aufgaben, desktop"></a> <a href="3-spielerin/05-aufgaben-phone.jpg"><img src="3-spielerin/05-aufgaben-phone.jpg" width="180" alt="aufgaben, phone"></a>

### spiel

<a href="3-spielerin/06-spiel-desktop.jpg"><img src="3-spielerin/06-spiel-desktop.jpg" width="560" alt="spiel, desktop"></a> <a href="3-spielerin/06-spiel-phone.jpg"><img src="3-spielerin/06-spiel-phone.jpg" width="180" alt="spiel, phone"></a>

### mein saisonverlauf

<a href="3-spielerin/07-mein-saisonverlauf-desktop.jpg"><img src="3-spielerin/07-mein-saisonverlauf-desktop.jpg" width="560" alt="mein saisonverlauf, desktop"></a> <a href="3-spielerin/07-mein-saisonverlauf-phone.jpg"><img src="3-spielerin/07-mein-saisonverlauf-phone.jpg" width="180" alt="mein saisonverlauf, phone"></a>

### profil

<a href="3-spielerin/08-profil-desktop.jpg"><img src="3-spielerin/08-profil-desktop.jpg" width="560" alt="profil, desktop"></a> <a href="3-spielerin/08-profil-phone.jpg"><img src="3-spielerin/08-profil-phone.jpg" width="180" alt="profil, phone"></a>

### einwilligungen

<a href="3-spielerin/09-einwilligungen-desktop.jpg"><img src="3-spielerin/09-einwilligungen-desktop.jpg" width="560" alt="einwilligungen, desktop"></a> <a href="3-spielerin/09-einwilligungen-phone.jpg"><img src="3-spielerin/09-einwilligungen-phone.jpg" width="180" alt="einwilligungen, phone"></a>

## Eltern

Ein Elternkonto für ein Kind im Kader.

### uebersicht

<a href="4-eltern/01-uebersicht-desktop.jpg"><img src="4-eltern/01-uebersicht-desktop.jpg" width="560" alt="uebersicht, desktop"></a> <a href="4-eltern/01-uebersicht-phone.jpg"><img src="4-eltern/01-uebersicht-phone.jpg" width="180" alt="uebersicht, phone"></a>

### termine

<a href="4-eltern/02-termine-desktop.jpg"><img src="4-eltern/02-termine-desktop.jpg" width="560" alt="termine, desktop"></a> <a href="4-eltern/02-termine-phone.jpg"><img src="4-eltern/02-termine-phone.jpg" width="180" alt="termine, phone"></a>

### einwilligungen fuer das kind

<a href="4-eltern/03-einwilligungen-fuer-das-kind-desktop.jpg"><img src="4-eltern/03-einwilligungen-fuer-das-kind-desktop.jpg" width="560" alt="einwilligungen fuer das kind, desktop"></a> <a href="4-eltern/03-einwilligungen-fuer-das-kind-phone.jpg"><img src="4-eltern/03-einwilligungen-fuer-das-kind-phone.jpg" width="180" alt="einwilligungen fuer das kind, phone"></a>

### szenen des kindes

<a href="4-eltern/04-szenen-des-kindes-desktop.jpg"><img src="4-eltern/04-szenen-des-kindes-desktop.jpg" width="560" alt="szenen des kindes, desktop"></a> <a href="4-eltern/04-szenen-des-kindes-phone.jpg"><img src="4-eltern/04-szenen-des-kindes-phone.jpg" width="180" alt="szenen des kindes, phone"></a>

## Öffentlich

Seiten ohne Anmeldung.

### systemstatus

<a href="5-oeffentlich/01-systemstatus-desktop.jpg"><img src="5-oeffentlich/01-systemstatus-desktop.jpg" width="560" alt="systemstatus, desktop"></a> <a href="5-oeffentlich/01-systemstatus-phone.jpg"><img src="5-oeffentlich/01-systemstatus-phone.jpg" width="180" alt="systemstatus, phone"></a>

### verband

<a href="5-oeffentlich/02-verband-desktop.jpg"><img src="5-oeffentlich/02-verband-desktop.jpg" width="560" alt="verband, desktop"></a> <a href="5-oeffentlich/02-verband-phone.jpg"><img src="5-oeffentlich/02-verband-phone.jpg" width="180" alt="verband, phone"></a>
