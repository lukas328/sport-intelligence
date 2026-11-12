# Screenshots der App

Stand: 12. November 2026 (Branch claude/trikot-ui, Look «Anlauf» auf «Stoff», Marke
«Handball Intelligence»). Lokaler Stack mit dem Demo-Verein aus
`scripts/seed.py` (synthetische Testvideos), erfundene Namen. Offizielle Daten (handball.ch)
und Wurf-Vorschläge kommen aus aufgezeichneten Testantworten, weil der lokale Stack
handball.ch nicht erreicht.

Jeder Screen als Desktop (1440 px) und Phone (390 px), die ganze Seite. Neu erzeugen, bei
laufendem Stack (`make up`, `make seed`) und Web-App:
`cd apps/web && npx playwright test -c screens.config.ts`, dann
`python3 docs/screens/build.py` (wandelt in JPEG und schreibt diese Seite).
Mails liest die Aufnahme über die Mailpit-Schnittstelle (Port 8025).

Die Screens des Looks in allen sechs Prüffarben und die Vergleiche mit dem Zielbild
(links App, rechts Vorlage) liegen in [anlauf/](anlauf/) und [anlauf/vergleich/](anlauf/vergleich/).

## Inhalt

- [Einstieg](#einstieg) (10 Screens)
- [Trainer/in](#trainerin) (41 Screens)
- [Spieler/in](#spielerin) (10 Screens)
- [Eltern](#eltern) (4 Screens)
- [Öffentlich](#öffentlich) (2 Screens)

## Einstieg

Anmelden, registrieren und der erste Start: Teamsuche auf handball.ch, Schritt 2 «Das seid ihr, oder?», und der Weg von Hand, wenn nichts gefunden wird.

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

### onboarding das seid ihr

<a href="1-einstieg/06-onboarding-das-seid-ihr-desktop.jpg"><img src="1-einstieg/06-onboarding-das-seid-ihr-desktop.jpg" width="560" alt="onboarding das seid ihr, desktop"></a> <a href="1-einstieg/06-onboarding-das-seid-ihr-phone.jpg"><img src="1-einstieg/06-onboarding-das-seid-ihr-phone.jpg" width="180" alt="onboarding das seid ihr, phone"></a>

### onboarding verein von hand

<a href="1-einstieg/07-onboarding-verein-von-hand-desktop.jpg"><img src="1-einstieg/07-onboarding-verein-von-hand-desktop.jpg" width="560" alt="onboarding verein von hand, desktop"></a> <a href="1-einstieg/07-onboarding-verein-von-hand-phone.jpg"><img src="1-einstieg/07-onboarding-verein-von-hand-phone.jpg" width="180" alt="onboarding verein von hand, phone"></a>

### onboarding team

<a href="1-einstieg/08-onboarding-team-desktop.jpg"><img src="1-einstieg/08-onboarding-team-desktop.jpg" width="560" alt="onboarding team, desktop"></a> <a href="1-einstieg/08-onboarding-team-phone.jpg"><img src="1-einstieg/08-onboarding-team-phone.jpg" width="180" alt="onboarding team, phone"></a>

### onboarding kader

<a href="1-einstieg/09-onboarding-kader-desktop.jpg"><img src="1-einstieg/09-onboarding-kader-desktop.jpg" width="560" alt="onboarding kader, desktop"></a> <a href="1-einstieg/09-onboarding-kader-phone.jpg"><img src="1-einstieg/09-onboarding-kader-phone.jpg" width="180" alt="onboarding kader, phone"></a>

### onboarding einladen

<a href="1-einstieg/10-onboarding-einladen-desktop.jpg"><img src="1-einstieg/10-onboarding-einladen-desktop.jpg" width="560" alt="onboarding einladen, desktop"></a> <a href="1-einstieg/10-onboarding-einladen-phone.jpg"><img src="1-einstieg/10-onboarding-einladen-phone.jpg" width="180" alt="onboarding einladen, phone"></a>

## Trainer/in

Demo-Verein mit analysierten Testvideos: Spiele (Start), ein Spiel mit den Tabs Spiel, Video und Zahlen, Prüfen, Spieltag, Saison, Szenen, Sammlungen, Training, Team, Einstellungen. Die Werkbank liegt im Tab Video hinter «Mehr».

### spiele

<a href="2-trainer/01-spiele-desktop.jpg"><img src="2-trainer/01-spiele-desktop.jpg" width="560" alt="spiele, desktop"></a> <a href="2-trainer/01-spiele-phone.jpg"><img src="2-trainer/01-spiele-phone.jpg" width="180" alt="spiele, phone"></a>

### video hochladen

<a href="2-trainer/02-video-hochladen-desktop.jpg"><img src="2-trainer/02-video-hochladen-desktop.jpg" width="560" alt="video hochladen, desktop"></a> <a href="2-trainer/02-video-hochladen-phone.jpg"><img src="2-trainer/02-video-hochladen-phone.jpg" width="180" alt="video hochladen, phone"></a>

### neues spiel

<a href="2-trainer/03-neues-spiel-desktop.jpg"><img src="2-trainer/03-neues-spiel-desktop.jpg" width="560" alt="neues spiel, desktop"></a> <a href="2-trainer/03-neues-spiel-phone.jpg"><img src="2-trainer/03-neues-spiel-phone.jpg" width="180" alt="neues spiel, phone"></a>

### spiel vor dem anpfiff

<a href="2-trainer/04-spiel-vor-dem-anpfiff-desktop.jpg"><img src="2-trainer/04-spiel-vor-dem-anpfiff-desktop.jpg" width="560" alt="spiel vor dem anpfiff, desktop"></a> <a href="2-trainer/04-spiel-vor-dem-anpfiff-phone.jpg"><img src="2-trainer/04-spiel-vor-dem-anpfiff-phone.jpg" width="180" alt="spiel vor dem anpfiff, phone"></a>

### spiel video

<a href="2-trainer/05-spiel-video-desktop.jpg"><img src="2-trainer/05-spiel-video-desktop.jpg" width="560" alt="spiel video, desktop"></a> <a href="2-trainer/05-spiel-video-phone.jpg"><img src="2-trainer/05-spiel-video-phone.jpg" width="180" alt="spiel video, phone"></a>

### spiel video werkbank

<a href="2-trainer/06-spiel-video-werkbank-desktop.jpg"><img src="2-trainer/06-spiel-video-werkbank-desktop.jpg" width="560" alt="spiel video werkbank, desktop"></a> <a href="2-trainer/06-spiel-video-werkbank-phone.jpg"><img src="2-trainer/06-spiel-video-werkbank-phone.jpg" width="180" alt="spiel video werkbank, phone"></a>

### spiel spiel

<a href="2-trainer/07-spiel-spiel-desktop.jpg"><img src="2-trainer/07-spiel-spiel-desktop.jpg" width="560" alt="spiel spiel, desktop"></a> <a href="2-trainer/07-spiel-spiel-phone.jpg"><img src="2-trainer/07-spiel-spiel-phone.jpg" width="180" alt="spiel spiel, phone"></a>

### spiel zahlen

<a href="2-trainer/08-spiel-zahlen-desktop.jpg"><img src="2-trainer/08-spiel-zahlen-desktop.jpg" width="560" alt="spiel zahlen, desktop"></a> <a href="2-trainer/08-spiel-zahlen-phone.jpg"><img src="2-trainer/08-spiel-zahlen-phone.jpg" width="180" alt="spiel zahlen, phone"></a>

### spiel pruefen

<a href="2-trainer/09-spiel-pruefen-desktop.jpg"><img src="2-trainer/09-spiel-pruefen-desktop.jpg" width="560" alt="spiel pruefen, desktop"></a> <a href="2-trainer/09-spiel-pruefen-phone.jpg"><img src="2-trainer/09-spiel-pruefen-phone.jpg" width="180" alt="spiel pruefen, phone"></a>

### spiel pruefen person

<a href="2-trainer/10-spiel-pruefen-person-desktop.jpg"><img src="2-trainer/10-spiel-pruefen-person-desktop.jpg" width="560" alt="spiel pruefen person, desktop"></a> <a href="2-trainer/10-spiel-pruefen-person-phone.jpg"><img src="2-trainer/10-spiel-pruefen-person-phone.jpg" width="180" alt="spiel pruefen person, phone"></a>

### spieltag

<a href="2-trainer/11-spieltag-desktop.jpg"><img src="2-trainer/11-spieltag-desktop.jpg" width="560" alt="spieltag, desktop"></a> <a href="2-trainer/11-spieltag-phone.jpg"><img src="2-trainer/11-spieltag-phone.jpg" width="180" alt="spieltag, phone"></a>

### spieltag markieren

<a href="2-trainer/12-spieltag-markieren-desktop.jpg"><img src="2-trainer/12-spieltag-markieren-desktop.jpg" width="560" alt="spieltag markieren, desktop"></a> <a href="2-trainer/12-spieltag-markieren-phone.jpg"><img src="2-trainer/12-spieltag-markieren-phone.jpg" width="180" alt="spieltag markieren, phone"></a>

### spiel scouting

<a href="2-trainer/13-spiel-scouting-desktop.jpg"><img src="2-trainer/13-spiel-scouting-desktop.jpg" width="560" alt="spiel scouting, desktop"></a> <a href="2-trainer/13-spiel-scouting-phone.jpg"><img src="2-trainer/13-spiel-scouting-phone.jpg" width="180" alt="spiel scouting, phone"></a>

### spielbericht hinzufuegen

<a href="2-trainer/14-spielbericht-hinzufuegen-desktop.jpg"><img src="2-trainer/14-spielbericht-hinzufuegen-desktop.jpg" width="560" alt="spielbericht hinzufuegen, desktop"></a> <a href="2-trainer/14-spielbericht-hinzufuegen-phone.jpg"><img src="2-trainer/14-spielbericht-hinzufuegen-phone.jpg" width="180" alt="spielbericht hinzufuegen, phone"></a>

### saison

<a href="2-trainer/15-saison-desktop.jpg"><img src="2-trainer/15-saison-desktop.jpg" width="560" alt="saison, desktop"></a> <a href="2-trainer/15-saison-phone.jpg"><img src="2-trainer/15-saison-phone.jpg" width="180" alt="saison, phone"></a>

### statistik matrix

<a href="2-trainer/16-statistik-matrix-desktop.jpg"><img src="2-trainer/16-statistik-matrix-desktop.jpg" width="560" alt="statistik matrix, desktop"></a> <a href="2-trainer/16-statistik-matrix-phone.jpg"><img src="2-trainer/16-statistik-matrix-phone.jpg" width="180" alt="statistik matrix, phone"></a>

### assistent

<a href="2-trainer/17-assistent-desktop.jpg"><img src="2-trainer/17-assistent-desktop.jpg" width="560" alt="assistent, desktop"></a> <a href="2-trainer/17-assistent-phone.jpg"><img src="2-trainer/17-assistent-phone.jpg" width="180" alt="assistent, phone"></a>

### szenen

<a href="2-trainer/18-szenen-desktop.jpg"><img src="2-trainer/18-szenen-desktop.jpg" width="560" alt="szenen, desktop"></a> <a href="2-trainer/18-szenen-phone.jpg"><img src="2-trainer/18-szenen-phone.jpg" width="180" alt="szenen, phone"></a>

### sammlungen

<a href="2-trainer/19-sammlungen-desktop.jpg"><img src="2-trainer/19-sammlungen-desktop.jpg" width="560" alt="sammlungen, desktop"></a> <a href="2-trainer/19-sammlungen-phone.jpg"><img src="2-trainer/19-sammlungen-phone.jpg" width="180" alt="sammlungen, phone"></a>

### sammlung

<a href="2-trainer/20-sammlung-desktop.jpg"><img src="2-trainer/20-sammlung-desktop.jpg" width="560" alt="sammlung, desktop"></a> <a href="2-trainer/20-sammlung-phone.jpg"><img src="2-trainer/20-sammlung-phone.jpg" width="180" alt="sammlung, phone"></a>

### playlists

<a href="2-trainer/21-playlists-desktop.jpg"><img src="2-trainer/21-playlists-desktop.jpg" width="560" alt="playlists, desktop"></a> <a href="2-trainer/21-playlists-phone.jpg"><img src="2-trainer/21-playlists-phone.jpg" width="180" alt="playlists, phone"></a>

### playlist

<a href="2-trainer/22-playlist-desktop.jpg"><img src="2-trainer/22-playlist-desktop.jpg" width="560" alt="playlist, desktop"></a> <a href="2-trainer/22-playlist-phone.jpg"><img src="2-trainer/22-playlist-phone.jpg" width="180" alt="playlist, phone"></a>

### praesentationen

<a href="2-trainer/23-praesentationen-desktop.jpg"><img src="2-trainer/23-praesentationen-desktop.jpg" width="560" alt="praesentationen, desktop"></a> <a href="2-trainer/23-praesentationen-phone.jpg"><img src="2-trainer/23-praesentationen-phone.jpg" width="180" alt="praesentationen, phone"></a>

### praesentation bearbeiten

<a href="2-trainer/24-praesentation-bearbeiten-desktop.jpg"><img src="2-trainer/24-praesentation-bearbeiten-desktop.jpg" width="560" alt="praesentation bearbeiten, desktop"></a> <a href="2-trainer/24-praesentation-bearbeiten-phone.jpg"><img src="2-trainer/24-praesentation-bearbeiten-phone.jpg" width="180" alt="praesentation bearbeiten, phone"></a>

### training plan

<a href="2-trainer/25-training-plan-desktop.jpg"><img src="2-trainer/25-training-plan-desktop.jpg" width="560" alt="training plan, desktop"></a> <a href="2-trainer/25-training-plan-phone.jpg"><img src="2-trainer/25-training-plan-phone.jpg" width="180" alt="training plan, phone"></a>

### training uebungen

<a href="2-trainer/26-training-uebungen-desktop.jpg"><img src="2-trainer/26-training-uebungen-desktop.jpg" width="560" alt="training uebungen, desktop"></a> <a href="2-trainer/26-training-uebungen-phone.jpg"><img src="2-trainer/26-training-uebungen-phone.jpg" width="180" alt="training uebungen, phone"></a>

### training spielzuege

<a href="2-trainer/27-training-spielzuege-desktop.jpg"><img src="2-trainer/27-training-spielzuege-desktop.jpg" width="560" alt="training spielzuege, desktop"></a> <a href="2-trainer/27-training-spielzuege-phone.jpg"><img src="2-trainer/27-training-spielzuege-phone.jpg" width="180" alt="training spielzuege, phone"></a>

### training aufgaben

<a href="2-trainer/28-training-aufgaben-desktop.jpg"><img src="2-trainer/28-training-aufgaben-desktop.jpg" width="560" alt="training aufgaben, desktop"></a> <a href="2-trainer/28-training-aufgaben-phone.jpg"><img src="2-trainer/28-training-aufgaben-phone.jpg" width="180" alt="training aufgaben, phone"></a>

### team kader

<a href="2-trainer/29-team-kader-desktop.jpg"><img src="2-trainer/29-team-kader-desktop.jpg" width="560" alt="team kader, desktop"></a> <a href="2-trainer/29-team-kader-phone.jpg"><img src="2-trainer/29-team-kader-phone.jpg" width="180" alt="team kader, phone"></a>

### team kader bearbeiten

<a href="2-trainer/30-team-kader-bearbeiten-desktop.jpg"><img src="2-trainer/30-team-kader-bearbeiten-desktop.jpg" width="560" alt="team kader bearbeiten, desktop"></a> <a href="2-trainer/30-team-kader-bearbeiten-phone.jpg"><img src="2-trainer/30-team-kader-bearbeiten-phone.jpg" width="180" alt="team kader bearbeiten, phone"></a>

### team saisonverlauf spielerin

<a href="2-trainer/31-team-saisonverlauf-spielerin-desktop.jpg"><img src="2-trainer/31-team-saisonverlauf-spielerin-desktop.jpg" width="560" alt="team saisonverlauf spielerin, desktop"></a> <a href="2-trainer/31-team-saisonverlauf-spielerin-phone.jpg"><img src="2-trainer/31-team-saisonverlauf-spielerin-phone.jpg" width="180" alt="team saisonverlauf spielerin, phone"></a>

### team termine

<a href="2-trainer/32-team-termine-desktop.jpg"><img src="2-trainer/32-team-termine-desktop.jpg" width="560" alt="team termine, desktop"></a> <a href="2-trainer/32-team-termine-phone.jpg"><img src="2-trainer/32-team-termine-phone.jpg" width="180" alt="team termine, phone"></a>

### team abgleich handball ch

<a href="2-trainer/33-team-abgleich-handball-ch-desktop.jpg"><img src="2-trainer/33-team-abgleich-handball-ch-desktop.jpg" width="560" alt="team abgleich handball ch, desktop"></a> <a href="2-trainer/33-team-abgleich-handball-ch-phone.jpg"><img src="2-trainer/33-team-abgleich-handball-ch-phone.jpg" width="180" alt="team abgleich handball ch, phone"></a>

### team beitrittsanfragen

<a href="2-trainer/34-team-beitrittsanfragen-desktop.jpg"><img src="2-trainer/34-team-beitrittsanfragen-desktop.jpg" width="560" alt="team beitrittsanfragen, desktop"></a> <a href="2-trainer/34-team-beitrittsanfragen-phone.jpg"><img src="2-trainer/34-team-beitrittsanfragen-phone.jpg" width="180" alt="team beitrittsanfragen, phone"></a>

### ich profil

<a href="2-trainer/35-ich-profil-desktop.jpg"><img src="2-trainer/35-ich-profil-desktop.jpg" width="560" alt="ich profil, desktop"></a> <a href="2-trainer/35-ich-profil-phone.jpg"><img src="2-trainer/35-ich-profil-phone.jpg" width="180" alt="ich profil, phone"></a>

### ich sicherheit

<a href="2-trainer/36-ich-sicherheit-desktop.jpg"><img src="2-trainer/36-ich-sicherheit-desktop.jpg" width="560" alt="ich sicherheit, desktop"></a> <a href="2-trainer/36-ich-sicherheit-phone.jpg"><img src="2-trainer/36-ich-sicherheit-phone.jpg" width="180" alt="ich sicherheit, phone"></a>

### ich daten

<a href="2-trainer/37-ich-daten-desktop.jpg"><img src="2-trainer/37-ich-daten-desktop.jpg" width="560" alt="ich daten, desktop"></a> <a href="2-trainer/37-ich-daten-phone.jpg"><img src="2-trainer/37-ich-daten-phone.jpg" width="180" alt="ich daten, phone"></a>

### verein

<a href="2-trainer/38-verein-desktop.jpg"><img src="2-trainer/38-verein-desktop.jpg" width="560" alt="verein, desktop"></a> <a href="2-trainer/38-verein-phone.jpg"><img src="2-trainer/38-verein-phone.jpg" width="180" alt="verein, phone"></a>

### verein teams

<a href="2-trainer/39-verein-teams-desktop.jpg"><img src="2-trainer/39-verein-teams-desktop.jpg" width="560" alt="verein teams, desktop"></a> <a href="2-trainer/39-verein-teams-phone.jpg"><img src="2-trainer/39-verein-teams-phone.jpg" width="180" alt="verein teams, phone"></a>

### verein abo

<a href="2-trainer/40-verein-abo-desktop.jpg"><img src="2-trainer/40-verein-abo-desktop.jpg" width="560" alt="verein abo, desktop"></a> <a href="2-trainer/40-verein-abo-phone.jpg"><img src="2-trainer/40-verein-abo-phone.jpg" width="180" alt="verein abo, phone"></a>

### mitteilungen

<a href="2-trainer/41-mitteilungen-desktop.jpg"><img src="2-trainer/41-mitteilungen-desktop.jpg" width="560" alt="mitteilungen, desktop"></a> <a href="2-trainer/41-mitteilungen-phone.jpg"><img src="2-trainer/41-mitteilungen-phone.jpg" width="180" alt="mitteilungen, phone"></a>

## Spieler/in

Ein Spielerkonto, mit dem Kadereintrag verknüpft.

### uebersicht

<a href="3-spielerin/01-uebersicht-desktop.jpg"><img src="3-spielerin/01-uebersicht-desktop.jpg" width="560" alt="uebersicht, desktop"></a> <a href="3-spielerin/01-uebersicht-phone.jpg"><img src="3-spielerin/01-uebersicht-phone.jpg" width="180" alt="uebersicht, phone"></a>

### meine szenen

<a href="3-spielerin/02-meine-szenen-desktop.jpg"><img src="3-spielerin/02-meine-szenen-desktop.jpg" width="560" alt="meine szenen, desktop"></a> <a href="3-spielerin/02-meine-szenen-phone.jpg"><img src="3-spielerin/02-meine-szenen-phone.jpg" width="180" alt="meine szenen, phone"></a>

### szenen eines spiels

<a href="3-spielerin/03-szenen-eines-spiels-desktop.jpg"><img src="3-spielerin/03-szenen-eines-spiels-desktop.jpg" width="560" alt="szenen eines spiels, desktop"></a> <a href="3-spielerin/03-szenen-eines-spiels-phone.jpg"><img src="3-spielerin/03-szenen-eines-spiels-phone.jpg" width="180" alt="szenen eines spiels, phone"></a>

### termine

<a href="3-spielerin/04-termine-desktop.jpg"><img src="3-spielerin/04-termine-desktop.jpg" width="560" alt="termine, desktop"></a> <a href="3-spielerin/04-termine-phone.jpg"><img src="3-spielerin/04-termine-phone.jpg" width="180" alt="termine, phone"></a>

### team

<a href="3-spielerin/05-team-desktop.jpg"><img src="3-spielerin/05-team-desktop.jpg" width="560" alt="team, desktop"></a> <a href="3-spielerin/05-team-phone.jpg"><img src="3-spielerin/05-team-phone.jpg" width="180" alt="team, phone"></a>

### aufgaben

<a href="3-spielerin/06-aufgaben-desktop.jpg"><img src="3-spielerin/06-aufgaben-desktop.jpg" width="560" alt="aufgaben, desktop"></a> <a href="3-spielerin/06-aufgaben-phone.jpg"><img src="3-spielerin/06-aufgaben-phone.jpg" width="180" alt="aufgaben, phone"></a>

### spiel

<a href="3-spielerin/07-spiel-desktop.jpg"><img src="3-spielerin/07-spiel-desktop.jpg" width="560" alt="spiel, desktop"></a> <a href="3-spielerin/07-spiel-phone.jpg"><img src="3-spielerin/07-spiel-phone.jpg" width="180" alt="spiel, phone"></a>

### mein saisonverlauf

<a href="3-spielerin/08-mein-saisonverlauf-desktop.jpg"><img src="3-spielerin/08-mein-saisonverlauf-desktop.jpg" width="560" alt="mein saisonverlauf, desktop"></a> <a href="3-spielerin/08-mein-saisonverlauf-phone.jpg"><img src="3-spielerin/08-mein-saisonverlauf-phone.jpg" width="180" alt="mein saisonverlauf, phone"></a>

### ich

<a href="3-spielerin/09-ich-desktop.jpg"><img src="3-spielerin/09-ich-desktop.jpg" width="560" alt="ich, desktop"></a> <a href="3-spielerin/09-ich-phone.jpg"><img src="3-spielerin/09-ich-phone.jpg" width="180" alt="ich, phone"></a>

### einwilligungen

<a href="3-spielerin/10-einwilligungen-desktop.jpg"><img src="3-spielerin/10-einwilligungen-desktop.jpg" width="560" alt="einwilligungen, desktop"></a> <a href="3-spielerin/10-einwilligungen-phone.jpg"><img src="3-spielerin/10-einwilligungen-phone.jpg" width="180" alt="einwilligungen, phone"></a>

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
