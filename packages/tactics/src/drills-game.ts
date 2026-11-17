/** Drills for transition, fast break, defence and powerplay (own texts, see drills.ts). */
import { L, dribble, keeper, me, op, pass, run, shot, sketch } from "./drill-kit";
import type { Drill } from "./drill-types";
import { lineSpot } from "./geometry";
import { attack, defence } from "./templates";

const RM = lineSpot(11, 0);
const RL = lineSpot(10.8, 0.36);
const RR = lineSpot(10.8, -0.36);
const line = (s: number, d = 6.8) => lineSpot(d, s);

export const GAME_DRILLS: Drill[] = [
  {
    id: "transition_back",
    focus: ["transition_defence"],
    minutes: 15,
    players: "10-14",
    level: "advanced",
    name: L("Schnelles Rückzugsverhalten", "Repli défensif rapide", "Fast transition back"),
    setup: L(
      "Angriff 6 gegen 6, nach Abschluss oder Ballverlust sofort Gegenstoss des Gegners; Rückzug im Sprint.",
      "Attaque 6 contre 6, après tir ou perte de balle contre-attaque immédiate ; repli en sprint.",
      "Attack 6 against 6, after a shot or turnover the opponent counters at once; sprint back.",
    ),
    procedure: L(
      "Das Angriffsteam spielt bis zum Abschluss. Mit dem Wurf oder Ballverlust startet der Gegner über das ganze Feld, das Angriffsteam sprintet zurück und stellt die Abwehr.",
      "L'équipe en attaque joue jusqu'au tir. Au tir ou à la perte, l'adversaire part sur tout le terrain, l'équipe revient en sprint et organise la défense.",
      "The attacking team plays until the shot. With the shot or turnover the opponent goes over the full court, the attacking team sprints back and sets the defence.",
    ),
    coaching: L(
      "Der Spieler nach dem Ballverlust stört den ersten Pass, alle anderen zuerst zum eigenen 9 m.",
      "Le joueur qui perd le ballon gêne la première passe, les autres reviennent d'abord aux 9 m.",
      "The player who lost the ball disrupts the first pass, everybody else back to their own 9 m first.",
    ),
    variants: L(
      "Gegner startet mit einem Spieler mehr; Rückzug mit Blick zum Ball (rückwärts laufen verboten); Punkte für verhinderte Gegenstösse.",
      "L'adversaire part avec un joueur de plus ; repli en regardant le ballon ; points pour chaque contre empêché.",
      "The opponent starts with one player more; run back watching the ball; points for every fast break stopped.",
    ),
    sketch: sketch(() => ({
      court: "full",
      tokens: [keeper("own", true), me("1", [30.5, 15]), me("2", [29.2, 10]), me("3", [30.5, 5]), op("1", [33.5, 16.5]), op("2", [31.6, 7.6])],
      arrows: [run([30.5, 15], [11, 13.4]), run([29.2, 10], [10.6, 9.6]), run([30.5, 5], [12, 6]), pass([31.6, 7.6], [15, 16.6]), run([33.5, 16.5], [15, 16.6])],
      ball: [31.6, 7.6],
    })),
  },
  {
    id: "transition_3v2_back",
    focus: ["transition_defence"],
    minutes: 12,
    players: "6-12",
    level: "basic",
    name: L("Rückzug 3 gegen 2 nach Ballverlust", "Repli à 2 contre 3 après la perte", "Getting back 2 against 3 after a turnover"),
    setup: L(
      "Ganzes Feld. Drei Angreifer an der Mittellinie mit Ball, zwei Verteidiger einen Schritt weiter vorne, Torhüter.",
      "Terrain entier. Trois attaquants à la ligne médiane avec ballon, deux défenseurs un pas plus loin, gardien.",
      "Full court. Three attackers at the centre line with the ball, two defenders a step further up, goalkeeper.",
    ),
    procedure: L(
      "Auf Pfiff greifen die drei an, die zwei sprinten zurück und verteidigen in Unterzahl bis zum Abschluss.",
      "Au coup de sifflet, les trois attaquent, les deux reviennent en sprint et défendent en infériorité jusqu'au tir.",
      "On the whistle the three attack, the two sprint back and defend outnumbered until the shot.",
    ),
    coaching: L(
      "Zuerst die Mitte und den Ball sichern, Zeit gewinnen, bis Hilfe kommt; nicht zu früh herausgehen.",
      "D'abord protéger l'axe et le ballon, gagner du temps jusqu'au retour des autres ; ne pas sortir trop tôt.",
      "Protect the middle and the ball first, win time until help arrives; do not step out too early.",
    ),
    variants: L(
      "Dritter Verteidiger startet zwei Sekunden später; Angreifer müssen in acht Sekunden abschliessen.",
      "Un troisième défenseur part deux secondes plus tard ; les attaquants doivent finir en huit secondes.",
      "A third defender starts two seconds later; attackers must finish within eight seconds.",
    ),
    sketch: sketch(() => ({
      court: "full",
      tokens: [keeper("own", true), me("1", [23.4, 13]), me("2", [24.6, 7]), op("1", [20.6, 16.4]), op("2", [20.2, 10]), op("3", [20.6, 3.6])],
      arrows: [run([23.4, 13], [8.4, 12]), run([24.6, 7], [8.8, 7.8]), dribble([20.2, 10], [11.6, 10]), run([20.6, 16.4], [12.6, 16.2]), run([20.6, 3.6], [12.6, 3.8])],
      ball: [20.2, 10],
    })),
  },
  {
    id: "transition_waves_game",
    focus: ["transition_defence", "fast_break"],
    minutes: 15,
    players: "8-14",
    level: "advanced",
    name: L("Wellenspiel: Angriff, Ballverlust, Rückzug", "Jeu de vagues : attaque, perte, repli", "Waves game: attack, turnover, back"),
    setup: L(
      "Ganzes Feld, 3 gegen 3, zwei Torhüter, weitere Dreiergruppen an den Seitenlinien.",
      "Terrain entier, 3 contre 3, deux gardiens, d'autres trios le long des touches.",
      "Full court, 3 on 3, two goalkeepers, more groups of three at the side lines.",
    ),
    procedure: L(
      "Team A greift an. Nach dem Abschluss wirft der Torhüter sofort ab, Team B kontert, Team A läuft zurück. Danach kommt Team C gegen B.",
      "L'équipe A attaque. Après le tir, le gardien relance tout de suite, l'équipe B contre, A revient. Puis l'équipe C affronte B.",
      "Team A attacks. After the shot the goalkeeper throws out at once, team B counters, team A runs back. Then team C plays against B.",
    ),
    coaching: L(
      "Umschalten im Kopf vor dem Wurf: wer wirft, wer sichert. Rückzug auf dem kürzesten Weg zum eigenen Tor.",
      "Penser la transition avant le tir : qui tire, qui assure. Repli par le chemin le plus court.",
      "Switch in the head before the shot: who shoots, who covers. Run back on the shortest way to the own goal.",
    ),
    variants: L(
      "4 gegen 4; Tor im Gegenstoss zählt doppelt; Trainer bestimmt mit Zuruf, wer zurückläuft.",
      "4 contre 4 ; un but en contre compte double ; l'entraîneur désigne qui revient.",
      "4 on 4; a fast break goal counts double; the coach calls who runs back.",
    ),
    sketch: sketch(() => ({
      court: "full",
      tokens: [keeper("own", true), me("1", [30, 14]), me("2", [29.2, 10]), me("3", [30, 6]), op("1", [33.5, 16.5]), op("2", [32.8, 10]), op("3", [33.5, 3.5]), keeper("opp")],
      arrows: [shot([29.2, 10]), run([30, 14], [11, 13]), run([30, 6], [11, 7]), pass([39.3, 10], [15, 16.4]), run([33.5, 16.5], [15, 16.4])],
      ball: [29.2, 10],
    })),
  },
  {
    id: "fast_break_waves",
    focus: ["fast_break"],
    minutes: 15,
    players: "8-14",
    level: "basic",
    name: L("Gegenstoss in drei Wellen", "Contre-attaque en trois vagues", "Fast break in three waves"),
    setup: L(
      "Nach Parade langer Pass auf die Flügel (1. Welle), Rückraum folgt (2. Welle), Kreis zuletzt.",
      "Après un arrêt longue passe aux ailiers (1re vague), la base arrière suit (2e vague), le pivot en dernier.",
      "After a save a long pass to the wings (first wave), back court follows (second wave), pivot last.",
    ),
    procedure: L(
      "Der Torhüter pariert und spielt lang auf einen Flügel. Ist der zu, kommt der Ball über die Rückraumspieler der 2. Welle, der Kreisläufer läuft in die Mitte nach.",
      "Le gardien arrête et joue long sur une aile. Si elle est fermée, le ballon passe par les arrières de la 2e vague, le pivot suit dans l'axe.",
      "The goalkeeper saves and plays long to a wing. If that is closed, the ball goes through the back court players of the second wave, the pivot follows in the middle.",
    ),
    coaching: L(
      "Flügel starten beim Wurf des Gegners, Torhüter schaut zuerst lang.",
      "Les ailiers partent au tir adverse, le gardien regarde d'abord loin.",
      "Wings start when the opponent shoots, goalkeeper looks long first.",
    ),
    variants: L(
      "Mit zwei zurücklaufenden Verteidigern; Abschluss spätestens nach zehn Sekunden; Start nach Gegentor (Schnelle Mitte).",
      "Avec deux défenseurs qui reviennent ; finir en dix secondes ; départ après un but encaissé (engagement rapide).",
      "With two defenders running back; finish within ten seconds; start after a goal against (quick throw-off).",
    ),
    sketch: sketch(() => ({
      court: "full",
      tokens: [keeper("own", true), me("LA", [7, 18.5]), me("RA", [7, 1.5]), me("RL", [9, 13]), me("RR", [9, 7]), me("KM", [8, 10])],
      arrows: [run([7, 18.5], [30, 17.6]), run([7, 1.5], [30, 2.4]), run([9, 13], [24, 13]), run([9, 7], [24, 7]), run([8, 10], [20, 10]), pass([0.7, 10], [30, 17.6])],
      ball: [0.7, 10],
    })),
  },
  {
    id: "fast_break_2v1",
    focus: ["fast_break"],
    minutes: 12,
    players: "6-12",
    level: "basic",
    name: L("Gegenstoss 2 gegen 1", "Contre-attaque à 2 contre 1", "Fast break 2 on 1"),
    setup: L(
      "Zwei Angreifer an der Mittellinie, ein Verteidiger auf 9 m, Torhüter.",
      "Deux attaquants à la ligne médiane, un défenseur à 9 m, gardien.",
      "Two attackers at the centre line, one defender at 9 m, goalkeeper.",
    ),
    procedure: L(
      "Der Ballführer läuft auf den Verteidiger zu und bindet ihn, der Mitspieler hält Abstand. Pass im richtigen Moment, Abschluss ohne Prellen.",
      "Le porteur fonce sur le défenseur pour le fixer, le partenaire garde la distance. Passe au bon moment, finition sans dribble.",
      "The ball carrier runs at the defender to tie him, the team-mate keeps his distance. Pass at the right moment, finish without bouncing.",
    ),
    coaching: L(
      "Breite halten (mindestens 4 m), auf den Verteidiger zulaufen, nicht am Verteidiger vorbei passen, wenn er schon entschieden hat.",
      "Garder la largeur (au moins 4 m), aller vers le défenseur, ne pas passer s'il a déjà choisi.",
      "Keep the width (at least 4 m), run at the defender, do not pass once he has already decided.",
    ),
    variants: L(
      "3 gegen 2; Verteidiger startet hinter den Angreifern; Torhüter spielt den ersten Pass.",
      "3 contre 2 ; le défenseur part derrière les attaquants ; le gardien fait la première passe.",
      "3 on 2; the defender starts behind the attackers; the goalkeeper plays the first pass.",
    ),
    sketch: sketch(() => {
      const end = [28.4, 12.4] as const;
      const free = [31.4, 6.6] as const;
      return {
        tokens: [keeper("opp"), me("1", [21.2, 13]), me("2", [21.2, 7]), op("1", lineSpot(9, 0))],
        arrows: [dribble([21.2, 13], end), run([21.2, 7], free), pass(end, free), shot(free, false)],
        ball: [21.2, 13],
      };
    }),
  },
  {
    id: "fast_break_quick_throwoff",
    focus: ["fast_break"],
    minutes: 12,
    players: "8-14",
    level: "advanced",
    name: L("Schnelle Mitte", "Engagement rapide", "Quick throw-off"),
    setup: L(
      "Ganzes Feld. Nach einem Gegentor holt der Torhüter den Ball, ein Spieler steht am Mittelpunkt.",
      "Terrain entier. Après un but encaissé, le gardien récupère le ballon, un joueur se place au centre.",
      "Full court. After a goal against the goalkeeper gets the ball, one player stands at the centre spot.",
    ),
    procedure: L(
      "Der Torhüter spielt sofort zum Spieler am Mittelpunkt, der mit einem Fuss auf der Mittellinie anwirft. Die Flügel und der Rückraum laufen schon an und greifen die noch ungeordnete Abwehr an.",
      "Le gardien passe tout de suite au joueur au centre, qui engage un pied sur la ligne. Ailiers et arrières sont déjà lancés et attaquent la défense pas encore en place.",
      "The goalkeeper passes at once to the player at the centre spot, who throws off with one foot on the centre line. Wings and back court are already running and attack the defence that is not set yet.",
    ),
    coaching: L(
      "Regel: beim Anwurf alle Mitspieler in der eigenen Hälfte. Wer die Mitte macht, ist vorher klar.",
      "Règle : à l'engagement tous les partenaires dans leur moitié. Celui qui engage est désigné à l'avance.",
      "Rule: at the throw-off all team-mates in their own half. Who takes the throw-off is clear beforehand.",
    ),
    variants: L(
      "Gegner läuft mit drei Spielern zurück; Abschluss in acht Sekunden; Mitte auch nach Ballgewinn im Feld.",
      "L'adversaire revient avec trois joueurs ; finir en huit secondes ; engagement rapide aussi après une récupération.",
      "The opponent runs back with three players; finish within eight seconds; quick restart also after winning the ball.",
    ),
    sketch: sketch(() => ({
      court: "full",
      tokens: [keeper("own", true), me("1", [19.4, 10]), me("2", [17, 14.6]), me("3", [17, 5.4]), op("1", [25, 12.8]), op("2", [26, 7]), keeper("opp")],
      arrows: [pass([0.7, 10], [19.4, 10]), run([17, 14.6], [29, 14.6]), run([17, 5.4], [30, 5.4]), pass([19.4, 10], [29, 14.6]), run([25, 12.8], [32, 12.6])],
      ball: [0.7, 10],
    })),
  },
  {
    id: "fast_break_3v2",
    focus: ["fast_break", "passing"],
    minutes: 15,
    players: "6-12",
    level: "basic",
    name: L("Zweite Welle 3 gegen 2", "Deuxième vague à 3 contre 2", "Second wave 3 on 2"),
    setup: L(
      "Drei Rückraumspieler kommen von der Mittellinie gegen zwei Verteidiger auf 8 bis 9 m, Torhüter.",
      "Trois arrières arrivent de la ligne médiane contre deux défenseurs à 8 ou 9 m, gardien.",
      "Three back court players come from the centre line against two defenders at 8 to 9 m, goalkeeper.",
    ),
    procedure: L(
      "Die drei passen sich im Lauf den Ball zu und stossen auf die Lücken. Ziel: in maximal drei Pässen einen freien Wurf herausspielen.",
      "Les trois se passent le ballon en course et attaquent les intervalles. Objectif : un tir libre en trois passes au plus.",
      "The three pass to each other on the run and drive at the gaps. Aim: a free shot within three passes at most.",
    ),
    coaching: L(
      "Tempo halten, Pässe nach vorne in den Lauf, der Ballführer bindet immer einen Verteidiger.",
      "Garder le rythme, passes vers l'avant dans la course, le porteur fixe toujours un défenseur.",
      "Keep the speed, passes forward into the run, the ball carrier always ties a defender.",
    ),
    variants: L(
      "Mit Kreisläufer der nachkommt (4 gegen 3); Verteidiger dürfen offensiv herausgehen; Start nach Pass des Torhüters.",
      "Avec un pivot qui arrive (4 contre 3) ; les défenseurs peuvent sortir ; départ sur passe du gardien.",
      "With a pivot arriving (4 on 3); defenders may step out; start after a pass from the goalkeeper.",
    ),
    sketch: sketch(() => {
      const rl = [28.4, 14.6] as const;
      const rm = [28, 10] as const;
      return {
        tokens: [keeper("opp"), me("RL", [22, 15]), me("RM", [21, 10]), me("RR", [22, 5]), op("1", lineSpot(8.6, 0.2)), op("2", lineSpot(8.6, -0.2))],
        arrows: [run([22, 15], rl), dribble([21, 10], rm), run([22, 5], [28.6, 5.4]), pass(rm, rl)],
        ball: [21, 10],
      };
    }),
  },
  {
    id: "defence_6_0_shift",
    focus: ["defence"],
    minutes: 15,
    players: "12",
    level: "basic",
    name: L("6:0 Verschieben und Helfen", "6-0 coulisser et aider", "6-0 shifting and help"),
    setup: L(
      "Angriff spielt den Ball schnell um den Kreis, Abwehr verschiebt ballorientiert und hilft zur Mitte.",
      "L'attaque fait circuler vite, la défense coulisse côté ballon et aide vers le centre.",
      "The attack passes quickly around, the defence shifts to the ball and helps to the centre.",
    ),
    procedure: L(
      "Erst ohne Torwurf: der Verteidiger am Ball tritt heraus, die Nachbarn sichern nach innen. Danach darf der Angriff nach fünf Pässen werfen.",
      "D'abord sans tir : le défenseur face au ballon sort, ses voisins couvrent vers l'intérieur. Ensuite l'attaque peut tirer après cinq passes.",
      "First without shots: the defender at the ball steps out, his neighbours cover inside. Then the attack may shoot after five passes.",
    ),
    coaching: L(
      "Kommunikation, Arme oben, Nebenmann sichert ab.",
      "Communication, bras levés, le voisin couvre.",
      "Talk, arms up, the neighbour covers.",
    ),
    variants: L(
      "Mit Kreisläufer, der wandert; Angriff mit Kreuzen; Abwehr spielt aktiv mit Ballgewinn als Punkt.",
      "Avec un pivot qui se déplace ; attaque avec croisés ; défense active, une interception vaut un point.",
      "With a pivot who moves; attack with crosses; active defence, winning the ball scores a point.",
    ),
    sketch: sketch(() => {
      const tokens = [...defence("6-0"), ...attack("opp")];
      return {
        tokens,
        arrows: [pass(RM, RL), run(line(0.49), lineSpot(8.4, 0.42)), run(line(0.16), lineSpot(6.8, 0.3)), run(line(-0.16), lineSpot(6.8, 0.04))],
        ball: RM,
      };
    }),
  },
  {
    id: "defence_1v1_footwork",
    focus: ["defence"],
    minutes: 10,
    players: "2-14",
    level: "basic",
    name: L("Abwehr 1 gegen 1: Beinarbeit", "Défense 1 contre 1 : travail des appuis", "Defence 1 on 1: footwork"),
    setup: L(
      "Paare in einer 4 m breiten Gasse zwischen Hütchen, ein Angreifer mit Ball, ein Verteidiger.",
      "Par paires dans un couloir de 4 m entre plots, un attaquant avec ballon, un défenseur.",
      "Pairs in a 4 m wide lane between cones, one attacker with the ball, one defender.",
    ),
    procedure: L(
      "Der Angreifer versucht mit Prellen und Täuschungen durch die Gasse zu kommen, der Verteidiger stellt ihn mit Seitschritten und drängt ihn zur Seite ab. Nach drei Versuchen tauschen.",
      "L'attaquant tente de passer le couloir en dribblant et feintant, le défenseur le contient en pas chassés et l'oriente vers le côté. Changer après trois essais.",
      "The attacker tries to get through the lane with bounces and feints, the defender stops him with side steps and forces him to the side. Swap after three tries.",
    ),
    coaching: L(
      "Tief und breit stehen, Seitschritte statt Überkreuzen, Arm auf der Wurfarmseite, Körper vor den Angreifer.",
      "Rester bas et large, pas chassés sans croiser, bras du côté du bras de tir, corps devant l'attaquant.",
      "Stand low and wide, side steps instead of crossing the feet, arm on the throwing-arm side, body in front of the attacker.",
    ),
    variants: L(
      "Angreifer ohne Ball (nur Beinarbeit); Gasse breiter; mit Torwurf, wenn der Angreifer durch ist.",
      "Attaquant sans ballon (seulement les appuis) ; couloir plus large ; avec tir si l'attaquant passe.",
      "Attacker without the ball (footwork only); a wider lane; with a shot when the attacker gets through.",
    ),
    sketch: sketch(() => ({
      tokens: [keeper(), me("1", lineSpot(8.4, 0)), op("1", lineSpot(11.4, 0))],
      arrows: [run(lineSpot(8.4, 0), [31.4, 11.8]), dribble(lineSpot(11.4, 0), [29.8, 11.6], [30.6, 12.6])],
      ball: lineSpot(11.4, 0),
      cones: [lineSpot(9.5, 0.2), lineSpot(9.5, -0.2), lineSpot(12, 0.17), lineSpot(12, -0.17)],
    })),
  },
  {
    id: "defence_step_out",
    focus: ["defence"],
    minutes: 12,
    players: "6-12",
    level: "basic",
    name: L("Heraustreten und Zurücksinken", "Sortir et reculer", "Step out and drop back"),
    setup: L(
      "Drei Verteidiger an der 6-m-Linie gegen drei Rückraumspieler, die sich den Ball zupassen.",
      "Trois défenseurs sur les 6 m contre trois arrières qui se font des passes.",
      "Three defenders at the 6 m line against three back court players passing the ball.",
    ),
    procedure: L(
      "Der Verteidiger gegenüber dem Ball tritt bis 9 m heraus und stört, sobald der Ball weg ist, sinkt er zurück. Der nächste Verteidiger tritt zum neuen Ballführer heraus.",
      "Le défenseur face au ballon sort jusqu'à 9 m et gêne ; dès que le ballon part, il recule. Le suivant sort sur le nouveau porteur.",
      "The defender facing the ball steps out to 9 m and disturbs; as soon as the ball has gone he drops back. The next defender steps out to the new ball carrier.",
    ),
    coaching: L(
      "Heraustreten mit dem Pass, nicht danach; schräg zurück zur Mitte sinken; Arme oben gegen den Pass.",
      "Sortir sur la passe, pas après ; reculer en biais vers le centre ; bras levés contre la passe.",
      "Step out with the pass, not after it; drop back diagonally to the centre; arms up against the pass.",
    ),
    variants: L(
      "Angreifer dürfen nach fünf Pässen werfen; mit Kreisläufer; vier gegen vier über die ganze Breite.",
      "Les attaquants peuvent tirer après cinq passes ; avec pivot ; quatre contre quatre sur toute la largeur.",
      "Attackers may shoot after five passes; with a pivot; four on four across the full width.",
    ),
    sketch: sketch(() => ({
      tokens: [keeper(), me("1", line(0.36)), me("2", line(0)), me("3", line(-0.36)), op("RL", RL), op("RM", lineSpot(11.6, 0)), op("RR", RR)],
      arrows: [run(line(0), lineSpot(9.4, 0)), pass(lineSpot(11.6, 0), RL), run(line(0.36), lineSpot(8.8, 0.34))],
      ball: lineSpot(11.6, 0),
    })),
  },
  {
    id: "defence_pivot_handover",
    focus: ["defence", "pivot"],
    minutes: 12,
    players: "6-10",
    level: "advanced",
    name: L("Kreisläufer übergeben und übernehmen", "Transmettre et reprendre le pivot", "Hand over and take over the pivot"),
    setup: L(
      "Zwei Innenverteidiger gegen einen Kreisläufer, zwei Rückraumspieler spielen ihn an, Torhüter.",
      "Deux défenseurs centraux contre un pivot, deux arrières cherchent à le servir, gardien.",
      "Two central defenders against a pivot, two back court players try to find him, goalkeeper.",
    ),
    procedure: L(
      "Der Kreisläufer wandert entlang der 6-m-Linie. Der Verteidiger, in dessen Raum er ist, übernimmt ihn, der andere gibt ihn mit einem Zuruf ab und sichert vorne.",
      "Le pivot se déplace le long des 6 m. Le défenseur dont il entre dans la zone le reprend, l'autre le transmet à la voix et couvre devant.",
      "The pivot moves along the 6 m line. The defender whose space he enters takes him over, the other hands him over with a call and covers in front.",
    ),
    coaching: L(
      "Laut übergeben («hab ihn»), Kreisläufer nie in den Rücken lassen, Körperkontakt halten.",
      "Transmettre à voix haute (« je l'ai »), ne jamais laisser le pivot dans le dos, garder le contact.",
      "Hand over loudly ('got him'), never let the pivot get behind you, keep body contact.",
    ),
    variants: L(
      "Mit Sperre des Kreisläufers für einen Rückraumspieler; drei Verteidiger; Angriff darf werfen.",
      "Avec écran du pivot pour un arrière ; trois défenseurs ; l'attaque peut tirer.",
      "With the pivot screening for a back court player; three defenders; the attack may shoot.",
    ),
    sketch: sketch(() => ({
      tokens: [keeper(), me("1", line(0.25)), me("2", line(-0.25)), op("KM", [33.7, 10.6]), op("RM", RM), op("RL", RL)],
      arrows: [run([33.7, 10.6], [33.7, 8.4]), pass(RL, RM)],
      ball: RL,
    })),
  },
  {
    id: "defence_block",
    focus: ["defence", "goalkeeping"],
    minutes: 10,
    players: "3-8",
    level: "basic",
    name: L("Block gegen den Rückraumwurf", "Contre sur le tir de loin", "Blocking the back court shot"),
    setup: L(
      "Ein Werfer auf 10 m, ein Blockspieler auf 8 m, Torhüter. Block und Torhüter sprechen ab, wer welche Ecke nimmt.",
      "Un tireur à 10 m, un contreur à 8 m, gardien. Contreur et gardien se partagent les coins.",
      "A shooter at 10 m, a blocker at 8 m, goalkeeper. Blocker and goalkeeper agree who takes which corner.",
    ),
    procedure: L(
      "Der Werfer bekommt den Ball und wirft. Der Blockspieler springt mit beiden Armen auf der Wurfarmseite, der Torhüter deckt die andere Ecke.",
      "Le tireur reçoit et tire. Le contreur saute bras tendus du côté du bras de tir, le gardien couvre l'autre coin.",
      "The shooter gets the ball and shoots. The blocker jumps with both arms on the throwing-arm side, the goalkeeper covers the other corner.",
    ),
    coaching: L(
      "Spät springen (erst mit dem Wurfarm), Arme eng und hoch, Augen offen.",
      "Sauter tard (avec le bras de tir), bras serrés et hauts, yeux ouverts.",
      "Jump late (with the throwing arm), arms close together and high, eyes open.",
    ),
    variants: L(
      "Werfer darf auch durchbrechen; zwei Werfer im Wechsel; Block ohne Sprung gegen Schlagwurf.",
      "Le tireur peut aussi déborder ; deux tireurs en alternance ; contre sans saut contre un tir à l'appui.",
      "The shooter may also break through; two shooters in turn; a block without jumping against a set shot.",
    ),
    sketch: sketch(() => ({
      tokens: [keeper(), me("1", lineSpot(7.8, 0)), op("1", [28.8, 10]), op("2", RL)],
      arrows: [pass(RL, [28.8, 10]), run(lineSpot(7.8, 0), [31.4, 10]), shot([28.8, 10])],
      ball: RL,
    })),
  },
  {
    id: "defence_5_1_advanced",
    focus: ["defence"],
    minutes: 15,
    players: "12",
    level: "advanced",
    name: L("5:1: der Vorgezogene stört", "5-1 : l'avancé gêne", "5-1: the advanced defender disrupts"),
    setup: L(
      "Abwehr 5:1 gegen einen Angriff 3:3, Torhüter.",
      "Défense 5-1 contre une attaque 3-3, gardien.",
      "A 5-1 defence against a 3-3 attack, goalkeeper.",
    ),
    procedure: L(
      "Der vorgezogene Verteidiger 6 stört RM und den Pass in die Mitte, die fünf an der Linie verschieben mit. Wechselt der Ball auf die Seite, bleibt 6 zwischen Ball und Mitte.",
      "L'avancé 6 gêne le DC et la passe dans l'axe, les cinq sur la ligne coulissent. Quand le ballon change de côté, 6 reste entre ballon et centre.",
      "The advanced defender 6 disrupts the centre back and the pass into the middle, the five on the line shift along. When the ball goes to the side, 6 stays between ball and centre.",
    ),
    coaching: L(
      "Der Vorgezogene arbeitet mit den Beinen, nicht mit den Händen; die Halbverteidiger sichern seinen Rücken.",
      "L'avancé travaille avec les jambes, pas les mains ; les demis couvrent son dos.",
      "The advanced defender works with the legs, not the hands; the half defenders cover his back.",
    ),
    variants: L(
      "Mit Kreuzen RM und RL; Vorgezogener darf den Pass abfangen und Gegenstoss laufen; 5:1 gegen 2 Kreisläufer.",
      "Avec croisé DC et arrière gauche ; l'avancé peut intercepter et partir en contre ; 5-1 contre deux pivots.",
      "With a cross of centre back and left back; the advanced defender may intercept and run the fast break; 5-1 against two pivots.",
    ),
    sketch: sketch(() => {
      const tokens = [...defence("5-1"), ...attack("opp", "5-1")];
      const rm = lineSpot(11.9, 0);
      return { tokens, arrows: [pass(rm, RL), run(lineSpot(9.8, 0), [30.6, 12.8]), run(line(0.4), lineSpot(8, 0.4))], ball: rm };
    }),
  },
  {
    id: "powerplay_7v6",
    focus: ["powerplay"],
    minutes: 12,
    players: "12",
    level: "advanced",
    name: L("Überzahl 6 gegen 5", "Supériorité 6 contre 5", "Powerplay 6 against 5"),
    setup: L(
      "Angriff in Überzahl mit zwei Kreisläufern, Ziel: freier Wurf aus der Nahdistanz innert 30 Sekunden.",
      "Attaque en supériorité avec deux pivots, objectif : tir libre de près en 30 secondes.",
      "Attack in powerplay with two pivots, aim: a free close-range shot within 30 seconds.",
    ),
    procedure: L(
      "Vier Spieler aussen, zwei am Kreis gegen eine 5:0-Abwehr. Der Ball läuft schnell, bis ein Verteidiger zwei Angreifer decken muss; dort wird abgeschlossen.",
      "Quatre joueurs à l'extérieur, deux pivots contre une défense 5-0. Le ballon circule vite jusqu'à ce qu'un défenseur doive couvrir deux attaquants ; on finit là.",
      "Four players outside, two at the line against a 5-0 defence. The ball moves fast until one defender has to cover two attackers; that is where the shot comes.",
    ),
    coaching: L(
      "Ball schnell bewegen, Überzahl auf einer Seite schaffen, Geduld bis zur klaren Chance.",
      "Faire circuler vite, créer le surnombre d'un côté, patience jusqu'à l'occasion nette.",
      "Move the ball fast, create the extra player on one side, be patient until the clear chance.",
    ),
    variants: L(
      "Gegen 4:1; Abschluss nur vom Kreis oder Flügel; Zeit auf 20 Sekunden kürzen.",
      "Contre 4-1 ; finir seulement au pivot ou à l'aile ; réduire le temps à 20 secondes.",
      "Against 4-1; finish only from the line or the wing; cut the time to 20 seconds.",
    ),
    sketch: sketch(() => {
      const k1 = lineSpot(6.3, 0.18);
      return {
        tokens: [keeper("opp"), me("LA", [36.2, 19.2]), me("RL", RL), me("RR", RR), me("RA", [36.2, 0.8]), me("KM", k1), me("K2", lineSpot(6.3, -0.18)), ...[0.75, 0.37, 0, -0.37, -0.75].map((s, i) => op(String(i + 1), line(s)))],
        arrows: [pass(RL, RR), pass(RR, k1)],
        ball: RL,
      };
    }),
  },
  {
    id: "powerplay_shorthanded",
    focus: ["powerplay", "defence"],
    minutes: 12,
    players: "12",
    level: "advanced",
    name: L("Unterzahl 5 gegen 6 verteidigen", "Défendre à 5 contre 6", "Defending 5 against 6"),
    setup: L(
      "Fünf Verteidiger und Torhüter gegen einen vollständigen Angriff, zwei Minuten auf der Uhr.",
      "Cinq défenseurs et le gardien contre une attaque complète, deux minutes au chrono.",
      "Five defenders and the goalkeeper against a complete attack, two minutes on the clock.",
    ),
    procedure: L(
      "Die Abwehr steht eng 5:0 und verschiebt kurz. Weit gestellte Flügel werden bewusst offen gelassen, die Mitte bleibt zu. Ziel: zwei Minuten mit höchstens einem Gegentor.",
      "La défense joue serrée en 5-0 et coulisse court. Les ailiers très écartés sont laissés libres exprès, l'axe reste fermé. Objectif : deux minutes avec un but au plus.",
      "The defence stands tight in a 5-0 and shifts short. Wings who stand wide are left open on purpose, the middle stays closed. Aim: two minutes with at most one goal against.",
    ),
    coaching: L(
      "Mitte zu, Würfe aus spitzem Winkel zulassen; der Torhüter weiss, welcher Flügel offen ist.",
      "Fermer l'axe, accepter les tirs dans l'angle fermé ; le gardien sait quelle aile est ouverte.",
      "Close the middle, allow shots from narrow angles; the goalkeeper knows which wing is open.",
    ),
    variants: L(
      "Angriff mit zwei Kreisläufern; 4 gegen 6 für 30 Sekunden; nach Ballgewinn sofort Gegenstoss.",
      "Attaque avec deux pivots ; 4 contre 6 pendant 30 secondes ; contre immédiat après récupération.",
      "Attack with two pivots; 4 against 6 for 30 seconds; a fast break straight after winning the ball.",
    ),
    sketch: sketch(() => ({
      tokens: [keeper(), ...[0.75, 0.37, 0, -0.37, -0.75].map((s, i) => me(String(i + 1), line(s))), op("LA", [36.2, 19.2]), op("RL", RL), op("RM", RM), op("RR", RR), op("RA", [36.2, 0.8]), op("KM", lineSpot(6.3, 0.18))],
      arrows: [pass(RM, RL), run(line(0.37), lineSpot(8.4, 0.38)), run(line(0), lineSpot(6.8, 0.14))],
      ball: RM,
    })),
  },
  {
    id: "powerplay_empty_goal",
    focus: ["powerplay"],
    minutes: 15,
    players: "14",
    level: "advanced",
    name: L("7 gegen 6 mit leerem Tor", "7 contre 6 avec le but vide", "7 against 6 with an empty goal"),
    setup: L(
      "Der Torhüter geht für einen siebten Feldspieler raus: zwei Kreisläufer, fünf aussen, gegen eine 6:0-Abwehr.",
      "Le gardien sort pour un septième joueur de champ : deux pivots, cinq à l'extérieur, contre une défense 6-0.",
      "The goalkeeper comes off for a seventh court player: two pivots, five outside, against a 6-0 defence.",
    ),
    procedure: L(
      "Der Angriff spielt geduldig, bis der Wurf frei ist. Nach Ballverlust oder Fehlwurf sofort zurück, der Torhüter kommt wieder herein; die Abwehr versucht den Wurf aufs leere Tor.",
      "L'attaque joue patiemment jusqu'au tir libre. Après une perte ou un tir manqué, retour immédiat, le gardien revient ; la défense tente le tir dans le but vide.",
      "The attack plays patiently until the shot is free. After a turnover or a miss everybody goes back at once and the goalkeeper comes back in; the defence tries the shot at the empty goal.",
    ),
    coaching: L(
      "Sichere Pässe vor Risiko, klare Wechselregel für den Torhüter, der siebte Spieler trägt ein Leibchen.",
      "Passes sûres avant le risque, règle de changement claire pour le gardien, le septième porte une chasuble.",
      "Safe passes before risk, a clear substitution rule for the goalkeeper, the seventh player wears a bib.",
    ),
    variants: L(
      "Gegen 5:1; Ballverlust zählt als Gegentor; nur 40 Sekunden Angriffszeit.",
      "Contre 5-1 ; une perte compte comme un but encaissé ; seulement 40 secondes d'attaque.",
      "Against 5-1; a turnover counts as a goal against; only 40 seconds of attack.",
    ),
    sketch: sketch(() => ({
      tokens: [
        me("LA", [36.2, 19.2]),
        me("RL", RL),
        me("RM", RM),
        me("RR", RR),
        me("RA", [36.2, 0.8]),
        me("KM", lineSpot(6.3, 0)),
        me("K2", lineSpot(6.3, 0.66)),
        ...defence("6-0", "opp"),
      ],
      arrows: [pass(RM, RL), pass(RL, lineSpot(6.3, 0.66))],
      ball: RM,
    })),
  },
];
