# Für Lukas

Was ich ohne dich nicht entscheiden wollte oder konnte.

1. **Pull Request statt `main`.** Das Blueprint wollte einen Branch und einen PR; ich habe nichts
   nach `main` gemergt. Schau dir den PR an und merge ihn, wenn dir die Richtung gefällt.
2. **Die Referenzbilder habe ich nicht übernommen**, wie du geschrieben hast. Übernommen ist die
   Idee (Bühne in Vereinsfarbe, Spielfeld als Motiv, Stimme aus den Daten, eigene Icons, Momente,
   Matchkarte). Schrift und Form sind eine eigene, ruhigere Lösung (`DECISIONS.md`).
3. **Richtwerte für die gelbe Markierung** in der Saison: Paraden 30 %, Würfe 55 %, 12 Ballverluste
   pro Spiel. Das sind übliche Werte im Erwachsenenhandball, kein Ligaschnitt, und die Seite sagt
   das. Wenn du andere Werte willst (z. B. pro Liga), ist das eine Zeile in `lib/voice.ts`.
4. **Trainernotizen in Handschrift** sind vorbereitet (Schrift geladen, Klasse `font-hand`), aber
   noch nicht eingesetzt: Kommentare können auch von Spielern stammen, und die Regel "nur echte
   Trainernotizen, wenn sie zum Moment passen" braucht eine klare Rolle am Kommentar. Vorschlag:
   Kommentare von Trainerrollen im Video-Panel in Handschrift.
5. **Standbilder in der Bühne** habe ich bewusst weggelassen: Dafür muss pro Spieler die
   Einwilligung "Bild" geprüft werden, und bei Nachwuchsteams gar nicht. Die Fläche bleibt
   Vereinsfarbe. Wenn du das willst, braucht es eine kurze Klärung zu Einwilligung und Rechten.
6. **Marketing-Site und Expo-App** tragen noch den Look von ADR 023. Wenn dir die neue Identität
   gefällt, ziehe ich sie dort nach (Schrift, Farben, Bühne).
7. **Usability-Test (Q-UX-1)** bleibt offen: 20 Minuten mit einem Trainer und einem Spieler am Handy.
8. **Rote Vereinsfarbe als Akzent.** Der Akzent (Hauptknöpfe, Links, Fokus) ist die Vereinsfarbe.
   Für einen roten Verein wie den Demo-Verein lesen sich "Speichern", "Bericht erstellen" oder
   "Rechnung anfordern" wie Fehler, denn Rot heisst in der App sonst Gegentor und Fehler.
   Möglichkeiten:
   - **A (mein Vorschlag): Hauptknöpfe in Tinte, Vereinsfarbe nur auf der Bühne.** Knöpfe schwarz
     (im Dunkelmodus weiss), Links unterstrichen in Tinte; die Vereinsfarbe bleibt oben in der Bühne,
     im Logo und in den Rückennummern. Rot und Fehler kollidieren nie mehr, für jeden Verein gleich.
   - **B: Akzent nur, wenn die Vereinsfarbe nicht rot ist.** Rote Vereine bekommen automatisch
     Tinte. Ein Verein mit Blau behält blaue Knöpfe. Nachteil: zwei Verhalten, schwer zu erklären.
   - **C: so lassen** und Fehler zusätzlich mit Symbol und Wort kennzeichnen (das tun sie schon).
   Bei A ist es eine Änderung an den Tokens in `globals.css` und am Button; ich setze es um, wenn du
   zustimmst.
