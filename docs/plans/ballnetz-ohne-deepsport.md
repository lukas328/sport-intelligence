# Ballnetz ohne DeepSport: Plan über hr1 hinaus

Stand 26.11.2026, Analyse-Sitzung. **Plan, keine Umsetzung vor dem OK der Hauptsitzung.**

## Ausgangslage

- hr-nods: Ballnetz ohne nicht-kommerzielle Daten, im Produkt erlaubt (`infra/model-licences.json`).
  Auf Ball-Test 2 (eingefrorene LLM-Labels, 85 Bälle, 42 neue Hallen) findet es 68,2 % als
  Top-1 im 12-px-Radius (CI 57,1 bis 79,8). hr1 kommt auf 72,9 % (CI 64,0 bis 82,1), ist aber mit
  DeepSport (CC BY-NC-SA) trainiert, also nur Test.
- Paarweise trifft nur hr1 9 Bälle und nur hr-nods 5. Bei 85 Bällen ist ein Unterschied unter etwa
  10 Punkten nicht auflösbar (`ml/ball/LINEAGE.md` §3). Ein «über hr1» ist mit dem heutigen Test
  darum gar nicht messbar.
- Nicht erlaubt: DeepSport, EIGD, SportsMOT, WASB-Gewichte, DINOv3 und jede Destillation aus hr1
  oder hrp1. Dazu gehört auch, Kandidaten dieser Netze als Label-Hilfe zu zeigen (siehe Schritt 2).
- Was heute im Training steckt:
  - Batch von 252 Kacheln (`train_hr_nods_push.py`).
  - Die besten Labels bekommen nur 12 Positive pro Batch (5 %): menschlich bestätigte LLM-Punkte
    D13 (5767 Punkte, 150 Clips, 57 Spiele) und die Peaks des Owners D11.
  - Die OWLv2-Pseudo-Labels (ungeprüft) bekommen 36, die selbst geminten Tracklets 24.
  - hr-nods hat den DeepSport-Anteil der kleinen Gruppe D2 bis D4 gegeben (130 Owner-Frames,
    Pfade, Zufallsnegative), nicht den menschlichen Labels.
- Die Trainings-Clips decken nur 57 der 226 Spiele der Bibliothek ab.
- Beide hr-Netze lernten am Budget-Ende noch. Weiter trainieren mit halber Lernrate brachte aber
  nichts (hr2, hrp2).
- Fehlerbilder (ältere Netze): 41 % der falschen Peaks liegen auf Händen. 45 % der echten Bälle
  liegen innerhalb von 15 px eines Handgelenks. Für hr-nods fehlt eine Fehleranalyse nach
  Kategorien.

## Schritte

Reihenfolge nach Nutzen pro Aufwand. Jeder Schritt hat eine vorab festgelegte Entscheidregel. Gemessen
wird nur auf dem erweiterten Ball-Test (Schritt 0), nie auf dem Wurf-Endtest.

### 0. Messbar machen (Voraussetzung)

- **Was:** Ball-Test 2 von 85 auf etwa 250 Bälle erweitern.
  - Neue Frames aus denselben 42 Testspielen, ausserhalb der bestehenden Test-Frames, von Gold v1
    und vom Wurf-Endtest.
  - Zwei unabhängige LLM-Durchgänge ohne Detektor-Ringe, dritter Blick bei Uneinigkeit, eingefroren.
  - Dazu pro Ball eine Kategorie: in der Hand, Bewegungsunschärfe, klein oder fern, verdeckt, frei.
  - Danach eine Fehleranalyse hr-nods gegen hr1 pro Kategorie, nur Messung.
- **Warum:** Bei 250 Bällen wird ein Unterschied von etwa 6 Punkten auflösbar. Die Kategorien sagen,
  welcher der folgenden Schritte zieht.
- **Aufwand:** etwa ein Tag LLM-Labeling (rund 900 Frames, zwei Durchgänge), dann die Auswertung.
  GPU: keine (Netze auf CPU über 900 Frames).
- **Gewinn:** kein Punkt, aber erst damit ist jede weitere Aussage belastbar.

### 1. Batch-Mischung neu gewichten (billig)

- **Was:** Die menschlich bestätigten Labels (D13, D11, dazu die harten Negative D14) bekommen
  den Platz, den DeepSport hatte: etwa 40 statt 12 Positive pro Batch, aus OWLv2 und Tracklets
  entsprechend weniger. Sonst alles wie hr-nods (Code, Budget, Augmentierungen).
- **Ablation dazu:** derselbe Lauf ohne TeamTrack-Ball-Labels. Die Rechtslage der TeamTrack-Bälle
  ist offen (OPEN_QUESTIONS 4c). Ein Netz, das ohne sie gleich gut ist, macht die Frage
  gegenstandslos.
- **Aufwand:** zwei Kaggle-Läufe T4 je 9,5 h, gratis. Die Pipeline ist da, nur
  `train_hr_nods_push.py` wird angepasst.
- **Erwarteter Gewinn:** +2 bis +4 Punkte. Geschätzt, nicht belegt: die Labels mit dem besten
  Signal sind heute stark untergewichtet.
- **Regel:** weiter, wenn mindestens gleich gut wie hr-nods auf dem erweiterten Test.

### 2. Mehr lizenzfreie Labels aus der Bibliothek (grösster Hebel)

- **Was:** 4000 bis 6000 neue LLM-Ballpunkte aus etwa 80 Spielen, die noch in keinem Training
  stecken.
  - Bestehende Pipeline in `ml/gold/`: Übersicht, Schlüsselbild-Durchgang, dichter Durchgang für
    schnelle Stellen. Der Pilot lag bei 98 % der sicheren Punkte innerhalb von 12 px.
  - Zwei Durchgänge. Ein Punkt zählt, wenn beide innerhalb von 30 px liegen.
  - Auswahl gezielt auf schwere Szenen: Würfe, Ball in der Hand, harte Pässe, hohe Bälle vor
    der Wand. Die Frames kommen aus der Kaggle-observe-Bibliothek (Segmente mit Bewegung und
    Personen).
- **Wichtig, Lizenz und Bias:**
  - Die observe-Ausgaben der Bibliothek enthalten Ballkandidaten von hrp1 (DeepSport). Diese
    Kandidaten werden NICHT als Ringe oder Vorschläge gezeigt, sonst ist es eine indirekte
    Destillation.
  - Ringe nur aus OWLv2 (Apache-2.0) oder hr-nods, oder gar keine. Ohne Ringe vermeidet man auch
    den bekannten Bias (in Gold wurden zu 66 bis 80 % Detektor-Kandidaten gewählt). Darum die
    Hälfte der Clips ohne Ringe.
- **Ausschlüsse:**
  - die 42 Ball-Testspiele und alle Spiele derselben Heimhalle;
  - die Hallen von Ball-Testset 1 (Horgen, Leimental, Uznach, Eisenach, Wetzlar, Cottbus);
  - die Wurf-Endtest-Spiele samt Hallen;
  - `ml/data/not_handball.json`.
  - Vereinsdaten nur nach Lukas' Entscheid zu Q-DATA-4.
- **Aufwand:** Labeling durch Subagenten. Eine Durchsatzzahl gibt es noch nicht. Der Pilot misst
  sie auf 2 Spielen, danach Hochrechnung und Freigabe. Grob geschätzt 3 bis 5 Tage, verteilt;
  das 5-h-Nutzungslimit begrenzt, es braucht Pausen. Eine Stichprobe (etwa 300 Punkte) prüft ein
  dritter Blick. GPU: ein Kaggle-Lauf, gratis.
- **Erwarteter Gewinn:** +4 bis +8 Punkte. Begründung: Der Stand der Technik nennt 3000 bis 5000
  geprüfte Frames aus 30 bis 50 Hallen als Grösse, ab der ein Ballnetz in neuen Hallen trägt
  (`ball-stand-der-technik.md`). Heute sind es 57 Spiele mit LLM-Punkten.
- **Regel:** ins Training, wenn die Doppel-Übereinstimmung auf dem Pilot mindestens 90 % innerhalb
  von 12 px beträgt. Sonst zuerst die Prompts verbessern.

### 3. Harte Beispiele gezielt

- **Was:**
  - Positive mit Ball in der Hand und unscharfem Ball. Konvention: Mitte der Unschärfe, wie bei
    BlurBall.
  - Harte Negative auf Händen, Köpfen und Bank-Objekten, aus den falschen Peaks von hr-nods selbst.
  - Verdeckungs-Augmentierung (Teile des Balls abdecken).
- **Aufwand:** klein, wenn Schritt 2 läuft (dieselbe Pipeline, andere Auswahl). Kein eigener
  GPU-Lauf, fliesst in den Lauf von Schritt 2.
- **Erwarteter Gewinn:** +1 bis +3 Punkte, vor allem weniger Fehlalarme auf Händen. Die
  Kategorien aus Schritt 0 sagen, ob es sich lohnt.

### 4. Ensemble aus zwei lizenzfreien Netzen

- **Was:** zwei BallHR-Netze aus zwei Folds über die Trainings-Clips, beide von Grund auf trainiert.
  Die Fold-Netze sind ohnehin geplant: sie liefern saubere Kandidaten für das Tracker-Rescoring.
  - Auf Gold v1 brachte hr1 + hrp1 73,8 % gegen 63,2 % und 65,7 % einzeln. Das ist der grösste
    gemessene Sprung in der ganzen Linie.
  - hrp (timm hrnet_w18, ImageNet-Start) ist nur zulässig, wenn die Lizenz der ImageNet-Gewichte
    geklärt ist (heute «ungeprüft»). Darum zuerst zwei Scratch-Netze.
- **Aufwand:** zwei Kaggle-Läufe, gratis.
- **Kosten im Produkt:** doppelte Ball-Inferenz auf CPU. Der Anteil des Ballnetzes an der
  Laufzeit ist hier nicht nachgemessen. Mit der Hauptsitzung zu entscheiden; GPU-Tag oder nur auf
  Wurffenstern.
- **Erwarteter Gewinn:** +3 bis +6 Punkte über dem besten Einzelnetz. Das ist auf hr1 + hrp1
  gemessen; für Scratch-Folds ist es eine Annahme.

### 5. Höhere Ausgabeauflösung (Modal, einmal)

- **Was:** Ausgabe mit Stride 2 statt 4 (feinere Peaks für kleine, ferne Bälle). Inferenz mit
  1280 px statt 960 px im Produkt prüfen; das ist nur Messung, ohne neues Training.
- **Aufwand:** ein Lauf. Pro Schritt etwa 1,5- bis 2-mal teurer, auf einer T4 in 9,5 h also zu
  wenig Schritte. Darum Modal mit A10G (etwa 1,1 USD/h, 12 h ≈ 13 USD), innerhalb der 20 USD.
- **Erwarteter Gewinn:** +1 bis +3 Punkte, nur bei kleinen Bällen. Unsicher; nur, wenn Schritt 0
  zeigt, dass kleine oder ferne Bälle ein grosser Fehleranteil sind.

### 6. Mehr Zeitkontext (später)

- **Was:** 5 statt 3 Frames, ein Bewegungskanal nach der Kamera-Registrierung, ein
  Sichtbarkeits-Kopf (TOTNet-Ideen).
- **Warum später:** grösserer Umbau mit neuer Exportkette und Produktanpassung. Lohnt erst, wenn
  der Test 2 bis 3 Punkte auflösen kann und die Schritte 1 bis 4 ausgeschöpft sind.
- **Erwarteter Gewinn:** offen. Die Literatur zeigt Gewinne vor allem bei Verdeckung.

## Zusammenfassung Aufwand und Kosten

| Schritt | Arbeit | GPU | Kosten | erwartet |
|---|---|---|---|---|
| 0 Test erweitern | ~1 Tag LLM-Labels | keine | 0 | Messbarkeit |
| 1 Mischung neu | Skript anpassen | 2 × T4 9,5 h Kaggle | 0 | +2 bis +4 |
| 2 neue Labels | 3 bis 5 Tage LLM-Labels | 1 × T4 Kaggle | 0 | +4 bis +8 |
| 3 harte Beispiele | klein (mit 2) | in 2 | 0 | +1 bis +3 |
| 4 Ensemble 2 Folds | 2 Läufe | 2 × T4 Kaggle | 0 (Produkt: CPU ×2) | +3 bis +6 |
| 5 Stride 2 | 1 Lauf | Modal A10G ~12 h | ~13 USD | +1 bis +3 |
| 6 5 Frames | grösserer Umbau | später | | offen |

Die Gewinne sind Schätzungen und addieren sich nicht einfach. Ziel: ein lizenzfreies Netz (oder
Ensemble) über hr1 auf dem erweiterten Ball-Test, CI der Differenz zu hr-nods über 0. Realistisch
erscheint das mit den Schritten 0 bis 4.

Kaggle: nur ein eigener Analyse-Kernel gleichzeitig, mit Präfix `handball-ml-`. Die
observe-Warteschlange (5 CPU-Plätze) bleibt unberührt; Training nutzt das GPU-Kontingent.

## Lizenzen

- **Gewichte:** BallHR von Grund auf, eigener Code, also eigen. Kein Start aus WASB- oder
  DeepSport-Gewichten. hrp-Varianten erst nach Klärung der timm-ImageNet-Gewichte.
- **Daten:**
  - eigene Labels (Owner, LLM mit Owner-Prüfung);
  - OWLv2-Pseudo-Labels (Lehrer Apache-2.0);
  - TeamTrack (MIT; die Ball-Labels sind rechtlich offen, darum die Ablation in Schritt 1).
- **LLM-Labels:** Ausgaben gehören dem Nutzer (kommerzielle Bedingungen von Anthropic). Als
  LLM-Labels gekennzeichnet, mit Hash eingefroren.
- **Videos der Bibliothek:** öffentliche Übertragungen, schon in D7 bis D13 genutzt. Eine
  Rechtsfrage für Lukas bleibt, ob Training auf fremden Übertragungen für ein kommerzielles Produkt
  zulässig ist; sie betrifft auch hr-nods.
- **`infra/model-licences.json`:** Einträge kommen mit jeder neuen Gewichtsdatei (Rolle, Daten,
  Lizenz, Status, Quelle). Neue Schlüssel bekommen in diesem Plan noch keinen Eintrag, weil es
  noch keine Dateien gibt.

## Was die Hauptsitzung entscheiden soll

1. Schritt 0 und 1 sofort, gratis und klein?
2. Schritt 2 mit Pilot auf 2 Spielen, dann Freigabe des grossen Labelings?
3. Ensemble im Produkt: ist doppelte Ball-Inferenz auf CPU tragbar, oder nur auf Wurffenstern?
4. Modal-Lauf für Stride 2 (etwa 13 USD) erst nach Schritt 0?
