# Befunde, vierte Runde: UI/UX-Runde Lukas (18.11.2026, morgens)

Stand: Website nach #84 (Runde 3), App nach #86 und Deploy vom 18.11. Lukas sammelt, umgesetzt
wird erst auf sein Zeichen. Prio P1 (vor dem nächsten Test), P2 (bald), P3 (später).

## Website

| # | Befund | Wo | Prio | Einschätzung und Massnahme | Stand |
|---|---|---|---|---|---|
| U30 | «Frag deine Spiele» ist gut und modern. Aber: Das ist noch Statistik, nicht Einsicht. Die Seite soll zeigen, dass wir handlungsbasiert arbeiten: nicht nur «hier sind die Szenen, das ist dazu gemappt», sondern Einsichten fürs nächste Training. Kein Fitness-Tracker, der nur die Herzfrequenz anzeigt. Vielleicht als weitere Kachel. | Startseite, nach «Frag deine Spiele» | P1 | stimmt. Heute steht der Weg von der Zahl zur Handlung nur verstreut auf der Seite: drei Dinge (Abend), Trainingstipps mit Übung (ein Satz im Teamchat-Teil). Massnahme: eine eigene Kachel «Was heisst das fürs Training?» als Schleife in vier Schritten am Beispiel der Demo-Geschichte: (1) Muster: 11 von 29 über aussen rechts; (2) woran es liegt: die Szenen dazu, die Positionen von oben zeigen, wo die Abwehr steht; (3) was ihr übt: Trainingstipp mit Übung aus der Bibliothek (gibt es in der App: `services/training_tips.py`, Übungen aus `services/drills`); (4) hat es geholfen: der Saisonbalken pro Spiel zeigt, ob das Thema bleibt oder weg ist. Ehrlichkeit (W32): Schritte 1, 3 und 4 kann die App heute; bei Schritt 2 zeigt sie Szenen und Positionen, die Ursache benennt heute der Trainer selbst. Bewegungs-Einsichten («so laufen eure Leute», automatisch erkannt) kommen erst, wenn die Analyse sie liefert. Bis dahin auf der Website nichts versprechen, was die App nicht kann. | offen |
| U31 | «So sieht es in der App aus» (So funktioniert es): Idee gut, aber auf breiten Bildschirmen noch viel weisser Raum. Die Leiste rechts mit 1 bis 4 muss mehr hervorkommen, braucht eine gute Animation; statt einfacher Kästchen 1 2 3 4 das Handball-Thema aufnehmen. | So funktioniert es, App-Tour, ab etwa 1600 px (Bild bei 1885 px) | P1 | stimmt. Beobachtet: links steht der Text nur in einer schmalen Spalte (rund 240 px) mit grossem Abstand zum Bild; unter und neben dem Bild bleibt viel leer; die Zahlenleiste rechts ist klein und grau und wirkt wie ein Anhang. Zudem laufen Text und Bild auseinander: rechts ist Schritt 2 aktiv, links steht Schritt 3 blass im Blick, Schritt 2 ist schon weggescrollt. Massnahme: (1) Bühne über die volle Breite: Text näher ans Bild und breiter, das Bild grösser; (2) die Leiste als Handball-Element, z. B. ein Spielzug auf dem halben Feld: vier Spieler-Punkte, ein Pass läuft beim Scrollen von Punkt zu Punkt, der aktive Schritt ist der ballführende Spieler (ruhig, mit reduzierter Bewegung ohne Animation); (3) Text und Bild über denselben Auslöser umschalten, damit immer der Text zum Bild aktiv ist. | offen |

## Erledigt aus Runde 3 (Antworten Lukas, 18.11.)

- Torhüter im Gratis-Plan angehakt: bleibt so, Torhüter wird ein Standard-Feature.
- Stripe und der frühere Torhüter-Zuschlag: Auf Staging ist Stripe nicht eingerichtet (`checkout_available` false), niemand konnte den Zuschlag über Stripe buchen. Nichts zu tun.
- Lizenz Wiedererkennungsmodell (MSMT17): zur Kenntnis genommen, vor dem Verkauf klären.
- Testspuren im Konto TV Thalwil: dürfen entfernt werden.
