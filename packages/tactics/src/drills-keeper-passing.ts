/** Drills for the goalkeeper and for passing (own texts, see drills.ts). */
import { L, keeper, me, op, pass, run, shot, shotLeft, sketch } from "./drill-kit";
import type { Drill } from "./drills";
import { lineSpot } from "./geometry";

const RM = lineSpot(11, 0);
const RL = lineSpot(10.8, 0.36);
const RR = lineSpot(10.8, -0.36);

export const KEEPER_PASSING_DRILLS: Drill[] = [
  {
    id: "keeper_reaction",
    focus: ["goalkeeping"],
    minutes: 15,
    players: "1-6",
    level: "basic",
    name: L("Torhüter: Reaktion und Stellung", "Gardien : réaction et placement", "Goalkeeper: reaction and position"),
    setup: L(
      "Würfe aus wechselnden Positionen in schneller Folge, Fokus auf die Zone mit den meisten Gegentoren.",
      "Tirs de positions variées en succession rapide, priorité à la zone la plus touchée.",
      "Shots from changing positions in quick succession, focus on the zone with most goals against.",
    ),
    procedure: L(
      "Drei Werfer mit je fünf Bällen auf RL, RM und RR. Sie werfen nacheinander, der Torhüter stellt sich nach jedem Wurf neu zum nächsten Werfer.",
      "Trois tireurs avec cinq ballons chacun aux postes arrière. Ils tirent l'un après l'autre, le gardien se replace face au suivant.",
      "Three shooters with five balls each at LB, CB and RB. They shoot one after the other, the goalkeeper resets towards the next shooter.",
    ),
    coaching: L(
      "Grundstellung auf der Winkelhalbierenden, Arme und Beine gleichzeitig, schnell zurück in die Mitte.",
      "Position de base sur la bissectrice, bras et jambes ensemble, retour rapide au centre.",
      "Base position on the bisector, arms and legs together, quickly back to the centre.",
    ),
    variants: L(
      "Würfe nur in die Zone mit den meisten Gegentoren; Werfer täuschen an; Reihenfolge der Werfer zufällig.",
      "Tirs seulement dans la zone la plus touchée ; les tireurs feintent ; ordre des tireurs au hasard.",
      "Shots only into the zone with most goals against; shooters feint; random order of shooters.",
    ),
    sketch: sketch(() => ({
      tokens: [keeper(), me("1", RL), me("2", RM), me("3", RR)],
      arrows: [shot(RL, false), shot(RR, true)],
      ball: RL,
    })),
  },
  {
    id: "keeper_wings",
    focus: ["goalkeeping", "wings"],
    minutes: 12,
    players: "3-8",
    level: "advanced",
    name: L("Torhüter gegen Flügelwürfe", "Gardien contre tirs à l'aile", "Goalkeeper against wing shots"),
    setup: L(
      "Flügelspieler werfen aus spitzem Winkel, Torhüter übt das Abdecken der kurzen Ecke und das Nachrücken.",
      "Les ailiers tirent avec un angle fermé, le gardien travaille le premier poteau et la sortie.",
      "Wings shoot from a narrow angle, the goalkeeper practises covering the near post and stepping out.",
    ),
    procedure: L(
      "RM spielt abwechselnd auf LA und RA, der Flügel schliesst nach drei Schritten ab. Der Torhüter geht mit dem Pass an den kurzen Pfosten.",
      "Le DC sert à tour de rôle l'ailier gauche et droit, qui finit après trois appuis. Le gardien va au premier poteau sur la passe.",
      "The centre back serves the left and right wing in turn, the wing finishes after three steps. The goalkeeper moves to the near post with the pass.",
    ),
    coaching: L(
      "Kurzen Pfosten zu, Schritt dem Werfer entgegen, spät reagieren.",
      "Fermer le premier poteau, avancer vers le tireur, réagir tard.",
      "Close the near post, step towards the shooter, react late.",
    ),
    variants: L(
      "Flügel dürfen Heber und Dreher werfen; Pass aus dem Gegenstoss; zwei Torhüter im Wechsel.",
      "Les ailiers peuvent lober et roucouler ; passe en contre-attaque ; deux gardiens en alternance.",
      "Wings may lob and spin; the pass comes from a fast break; two goalkeepers in turn.",
    ),
    sketch: sketch(() => {
      const end = [36.4, 16.9] as const;
      return {
        tokens: [keeper(), me("LA", [34.4, 19]), me("RA", [34.4, 1]), me("RM", RM)],
        arrows: [run([34.4, 19], end), pass(RM, end), shot(end)],
        ball: RM,
      };
    }),
  },
  {
    id: "keeper_angle_back",
    focus: ["goalkeeping"],
    minutes: 12,
    players: "2-6",
    level: "basic",
    name: L("Torhüter: Winkel gegen Rückraumwürfe", "Gardien : angle contre les tirs de loin", "Goalkeeper: angle against back court shots"),
    setup: L(
      "Drei Werfer auf 10 m (links, Mitte, rechts), Hütchen auf der 6-m-Linie zeigen die Winkel.",
      "Trois tireurs à 10 m (gauche, centre, droite), des plots sur les 6 m montrent les angles.",
      "Three shooters at 10 m (left, centre, right), cones on the 6 m line show the angles.",
    ),
    procedure: L(
      "Der Trainer zeigt auf einen Werfer, der Torhüter stellt sich in dessen Winkel, erst dann wird geworfen. Nach jedem Wurf zur Mitte zurück.",
      "L'entraîneur désigne un tireur, le gardien se place dans son angle, puis le tir part. Après chaque tir, retour au centre.",
      "The coach points to a shooter, the goalkeeper moves into his angle, only then the shot comes. Back to the centre after each shot.",
    ),
    coaching: L(
      "Kleine schnelle Schritte auf dem Halbkreis vor dem Tor, Schultern zum Werfer, nicht zu weit heraus.",
      "Petits pas rapides sur l'arc devant le but, épaules face au tireur, ne pas trop sortir.",
      "Small quick steps on the arc in front of the goal, shoulders to the shooter, do not come out too far.",
    ),
    variants: L(
      "Pass zwischen den Werfern vor dem Wurf; Würfe mit Block; Torhüter wirft nach der Parade sofort ab.",
      "Passes entre les tireurs avant le tir ; tirs avec contre ; relance immédiate après l'arrêt.",
      "Passes between the shooters before the shot; shots with a block; quick throw-out after the save.",
    ),
    sketch: sketch(() => ({
      tokens: [keeper(), me("1", lineSpot(10, 0.36)), me("2", lineSpot(10, 0)), me("3", lineSpot(10, -0.36))],
      arrows: [run([39.3, 10], [38.6, 11.3]), shot(lineSpot(10, 0.36), true)],
      ball: lineSpot(10, 0.36),
      cones: [lineSpot(6, 0.4), lineSpot(6, 0), lineSpot(6, -0.4)],
    })),
  },
  {
    id: "keeper_seven_m",
    focus: ["goalkeeping", "seven_m"],
    minutes: 10,
    players: "2-8",
    level: "advanced",
    name: L("Torhüter gegen 7 m: Werfer lesen", "Gardien contre le 7 m : lire le tireur", "Goalkeeper against penalties: read the shooter"),
    setup: L(
      "Werfer nacheinander an der 7-m-Linie, Torhüter im Tor, ein Mitspieler notiert Ecke und Ergebnis.",
      "Tireurs l'un après l'autre aux 7 m, gardien dans le but, un partenaire note le coin et le résultat.",
      "Shooters one after the other at the 7 m line, goalkeeper in goal, a team-mate notes corner and result.",
    ),
    procedure: L(
      "Der Torhüter steht etwa auf der 4-m-Linie (Torhütergrenzlinie) oder auf der Torlinie und probiert beides. Er wartet, bis der Wurfarm nach vorne kommt, und reagiert dann.",
      "Le gardien se place vers la ligne des 4 m ou sur sa ligne et essaie les deux. Il attend que le bras du tireur avance, puis réagit.",
      "The goalkeeper stands near the 4 m line (goalkeeper restraining line) or on the goal line and tries both. He waits until the throwing arm comes forward, then reacts.",
    ),
    coaching: L(
      "Ruhig stehen, Gewicht auf den Fussballen, nicht vor dem Wurf in eine Ecke springen; nach jedem Wurf kurz auswerten.",
      "Rester calme, poids sur l'avant des pieds, ne pas plonger avant le tir ; analyser brièvement après chaque tir.",
      "Stand still, weight on the balls of the feet, do not dive before the shot; review briefly after each shot.",
    ),
    variants: L(
      "Torhüter bewegt sich vor dem Wurf seitlich; Werfer müssen eine Täuschung einbauen; Wettkampf mit dem zweiten Torhüter.",
      "Le gardien bouge latéralement avant le tir ; les tireurs doivent feinter ; concours avec le second gardien.",
      "The goalkeeper moves sideways before the shot; shooters must include a feint; competition with the second goalkeeper.",
    ),
    sketch: sketch(() => ({
      tokens: [keeper(), me("1", [32.4, 10]), me("2", [29.6, 12.8]), me("3", [29.6, 7.2])],
      arrows: [run([39.3, 10], [37.2, 10]), shot([32.4, 10], false)],
      ball: [32.4, 10],
    })),
  },
  {
    id: "keeper_outlet",
    focus: ["goalkeeping", "fast_break"],
    minutes: 12,
    players: "4-12",
    level: "basic",
    name: L("Torhüter: schneller Abwurf zum Gegenstoss", "Gardien : relance rapide pour la contre-attaque", "Goalkeeper: quick outlet for the fast break"),
    setup: L(
      "Ganzes Feld. Ein Werfer am eigenen Tor, Flügelspieler an der Seitenlinie bei 8 m, Torhüter im Tor.",
      "Terrain entier. Un tireur devant notre but, des ailiers le long de la touche à 8 m, gardien dans le but.",
      "Full court. A shooter at our goal, wings at the side line at 8 m, goalkeeper in goal.",
    ),
    procedure: L(
      "Nach dem Wurf (Parade oder Ball vom Trainer) starten die Flügel. Der Torhüter spielt den langen Ball in den Lauf vor die Mittellinie.",
      "Après le tir (arrêt ou ballon de l'entraîneur), les ailiers partent. Le gardien joue long dans la course devant la ligne médiane.",
      "After the shot (save or a ball from the coach), the wings start. The goalkeeper plays the long ball into the run ahead of the centre line.",
    ),
    coaching: L(
      "Torhüter: zuerst lang schauen, Pass flach und vor den Läufer. Flügel: Start mit dem Wurf, nicht mit der Parade.",
      "Gardien : regarder loin d'abord, passe tendue devant le coureur. Ailiers : partir au tir, pas à l'arrêt.",
      "Goalkeeper: look long first, pass flat and ahead of the runner. Wings: start with the shot, not with the save.",
    ),
    variants: L(
      "Ein Verteidiger stört den Abwurf; Abschluss gegen den zweiten Torhüter; kurzer Pass, wenn lang zu ist.",
      "Un défenseur gêne la relance ; finition contre le second gardien ; passe courte si le long est fermé.",
      "A defender disturbs the outlet; finish against the second goalkeeper; a short pass when the long one is closed.",
    ),
    sketch: sketch(() => ({
      court: "full",
      tokens: [keeper("own", true), me("LA", [8, 18.5]), me("RA", [8, 1.5]), op("1", [9.6, 12.4]), keeper("opp")],
      arrows: [shotLeft([9.6, 12.4]), run([8, 18.5], [26, 17.6]), run([8, 1.5], [26, 2.4]), pass([0.7, 10], [26, 17.6])],
      ball: [0.7, 10],
    })),
  },
  {
    id: "passing_pressure",
    focus: ["passing"],
    minutes: 12,
    players: "8-14",
    level: "basic",
    name: L("Passspiel gegen offensive Abwehr", "Passes contre une défense agressive", "Passing against an aggressive defence"),
    setup: L(
      "4 gegen 2 im Feld 12 x 14 m (Hütchen), maximal drei Sekunden Ballbesitz, Fehlpässe zählen als Punkt für die Abwehr.",
      "4 contre 2 sur 12 x 14 m (plots), trois secondes maximum avec le ballon, une mauvaise passe donne un point à la défense.",
      "4 against 2 in a 12 x 14 m area (cones), at most three seconds on the ball, bad passes score for the defence.",
    ),
    procedure: L(
      "Die vier Angreifer halten den Ball, die zwei Verteidiger versuchen ihn abzufangen. Nach jedem Ballgewinn tauscht der Fehlerverursacher mit dem Verteidiger.",
      "Les quatre attaquants gardent le ballon, les deux défenseurs tentent de l'intercepter. Après chaque interception, le fautif prend la place du défenseur.",
      "The four attackers keep the ball, the two defenders try to intercept. After every interception the player at fault swaps with the defender.",
    ),
    coaching: L(
      "Freilaufen vor dem Pass, Blickkontakt, Pass in die Laufrichtung.",
      "Se démarquer avant la passe, contact visuel, passe dans la course.",
      "Get open before the pass, eye contact, pass into the running direction.",
    ),
    variants: L(
      "Nur Bodenpässe; Pass mit der schwachen Hand; 5 gegen 3 in grösserem Feld.",
      "Seulement des passes à terre ; passe de la main faible ; 5 contre 3 sur un terrain plus grand.",
      "Bounce passes only; pass with the weak hand; 5 against 3 in a bigger area.",
    ),
    sketch: sketch(() => ({
      tokens: [me("1", [22.4, 4.4]), me("2", [31.6, 4.4]), me("3", [31.6, 15.6]), me("4", [22.4, 15.6]), op("1", [26, 8]), op("2", [28, 12])],
      arrows: [pass([22.4, 4.4], [31.6, 4.4]), run([31.6, 15.6], [30.2, 12.8])],
      ball: [22.4, 4.4],
      cones: [[21, 3], [33, 3], [33, 17], [21, 17]],
    })),
  },
  {
    id: "passing_triangle_move",
    focus: ["passing"],
    minutes: 10,
    players: "6-15",
    level: "basic",
    name: L("Passdreieck in Bewegung", "Triangle de passes en mouvement", "Passing triangle on the move"),
    setup: L(
      "Drei Hütchen im Dreieck (6 m Seitenlänge), an jedem Hütchen zwei bis drei Spieler, ein Ball.",
      "Trois plots en triangle (6 m de côté), deux ou trois joueurs à chaque plot, un ballon.",
      "Three cones in a triangle (6 m sides), two or three players at each cone, one ball.",
    ),
    procedure: L(
      "Pass zum nächsten Hütchen und dem Ball nachlaufen. Nach einer Minute die Richtung wechseln, dann einen zweiten Ball dazu.",
      "Passe au plot suivant et suivre son ballon. Après une minute changer de sens, puis ajouter un second ballon.",
      "Pass to the next cone and follow the ball. After a minute change direction, then add a second ball.",
    ),
    coaching: L(
      "Ball im Lauf fangen, höchstens drei Schritte, Pass auf Brusthöhe vor den Mitspieler.",
      "Recevoir en course, trois appuis au plus, passe à hauteur de poitrine devant le partenaire.",
      "Catch on the run, three steps at most, pass at chest height ahead of the team-mate.",
    ),
    variants: L(
      "Sprungpass; Pass hinter dem Rücken; als Wettkampf: wie viele Pässe in einer Minute ohne Fehler.",
      "Passe en suspension ; passe dans le dos ; en concours : combien de passes en une minute sans faute.",
      "Jump pass; behind-the-back pass; as a competition: how many passes in a minute without a mistake.",
    ),
    sketch: sketch(() => ({
      tokens: [me("1", [23.4, 6.6]), me("2", [29.2, 10]), me("3", [23.4, 13.4]), me("4", [22, 5.2])],
      arrows: [pass([23.4, 6.6], [29.2, 10]), run([23.4, 6.6], [27.4, 8.6]), pass([29.2, 10], [23.4, 13.4])],
      ball: [23.4, 6.6],
      cones: [[23.4, 7.8], [30.4, 10], [23.4, 12.2]],
    })),
  },
  {
    id: "passing_circulation",
    focus: ["passing", "back_court"],
    minutes: 10,
    players: "6-12",
    level: "basic",
    name: L("Ballzirkulation 6 gegen 0 mit Tempowechsel", "Circulation du ballon à 6 contre 0 avec changement de rythme", "Ball circulation 6 on 0 with change of pace"),
    setup: L(
      "Angriff in der 3:3-Aufstellung ohne Abwehr, Torhüter im Tor.",
      "Attaque en 3-3 sans défense, gardien dans le but.",
      "Attack in a 3-3 set-up without defence, goalkeeper in goal.",
    ),
    procedure: L(
      "Ball langsam von Aussen zu Aussen, auf Zuruf des Trainers volles Tempo: Stossbewegung zum Tor vor jedem Pass. Nach drei Zirkulationen Abschluss.",
      "Le ballon circule lentement d'une aile à l'autre ; au signal, plein rythme : attaque du but avant chaque passe. Après trois circulations, tir.",
      "Ball slowly from wing to wing; on the coach's call full speed: a drive towards the goal before every pass. Finish after three circulations.",
    ),
    coaching: L(
      "Jeder Spieler stösst zum Tor, bevor er passt (Torgefahr), Ball nicht stehend annehmen.",
      "Chaque joueur attaque le but avant de passer (menace), ne pas recevoir à l'arrêt.",
      "Every player drives at the goal before he passes (threat), never receive standing still.",
    ),
    variants: L(
      "Mit passiver Abwehr; Kreisanspiel nach jeder zweiten Zirkulation; Pässe nur mit Sprung.",
      "Avec défense passive ; passe au pivot toutes les deux circulations ; passes seulement en suspension.",
      "With a passive defence; a pass to the pivot after every second circulation; jump passes only.",
    ),
    sketch: sketch(() => ({
      tokens: [keeper("opp"), me("LA", [36.2, 19.2]), me("RL", RL), me("RM", RM), me("RR", RR), me("RA", [36.2, 0.8]), me("KM", lineSpot(6.3, 0))],
      arrows: [pass(RM, RL), pass(RL, [36.2, 19.2]), run(RM, [30.4, 10.4])],
      ball: RM,
    })),
  },
  {
    id: "passing_ten_passes",
    focus: ["passing", "transition_defence"],
    minutes: 12,
    players: "8-14",
    level: "basic",
    name: L("Zehnerball", "Jeu des dix passes", "Ten passes game"),
    setup: L(
      "Zwei Teams in einer Feldhälfte (ohne Torraum), ein Ball, Leibchen.",
      "Deux équipes dans un demi-terrain (sans la zone), un ballon, chasubles.",
      "Two teams in one half (without the goal area), one ball, bibs.",
    ),
    procedure: L(
      "Das Team mit Ball sammelt zehn Pässe ohne Ballverlust für einen Punkt. Bei Ballverlust sofort umschalten: das andere Team zählt.",
      "L'équipe en possession enchaîne dix passes sans perte pour un point. En cas de perte, transition immédiate : l'autre équipe compte.",
      "The team with the ball collects ten passes without losing it for a point. On a turnover switch at once: the other team counts.",
    ),
    coaching: L(
      "Freie Räume suchen, kurze Pässe unter Druck, nach Ballverlust sofort den Ballführer stören.",
      "Chercher les espaces libres, passes courtes sous pression, après la perte presser tout de suite le porteur.",
      "Look for free space, short passes under pressure, after a turnover pressure the ball carrier at once.",
    ),
    variants: L(
      "Kein Rückpass zum Passgeber; nur drei Schritte; Punkt auch für Ballgewinn innerhalb von fünf Sekunden.",
      "Pas de retour au passeur ; trois appuis seulement ; un point aussi pour une récupération en cinq secondes.",
      "No pass back to the passer; three steps only; a point also for winning the ball within five seconds.",
    ),
    sketch: sketch(() => ({
      tokens: [me("1", [23, 4]), me("2", [29, 6]), me("3", [30, 14]), me("4", [23, 15]), op("1", [26, 6.5]), op("2", [27, 11]), op("3", [24, 10]), op("4", [28.5, 16])],
      arrows: [pass([23, 4], [29, 6]), pass([29, 6], [30, 14]), run([23, 15], [25.6, 13.2])],
      ball: [23, 4],
    })),
  },
];
