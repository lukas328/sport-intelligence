/** Drills for finishing, wings, back court, pivot and 7 m (own texts, see drills.ts). */
import { L, dribble, keeper, me, op, pass, run, screen, shot, sketch } from "./drill-kit";
import type { Drill } from "./drill-types";
import { lineSpot } from "./geometry";

const RM = lineSpot(11, 0);
const RL = lineSpot(10.8, 0.36);
const RR = lineSpot(10.8, -0.36);

export const ATTACK_DRILLS: Drill[] = [
  {
    id: "finishing_wings",
    focus: ["finishing", "wings"],
    minutes: 15,
    players: "6-12",
    level: "basic",
    name: L("Flügelwürfe unter Druck", "Tirs à l'aile sous pression", "Wing shots under pressure"),
    setup: L(
      "Zwei Kolonnen auf den Flügeln, Zuspiel aus dem Rückraum, ein passiver Verteidiger engt den Winkel ein.",
      "Deux colonnes aux ailes, passe depuis la base arrière, un défenseur passif réduit l'angle.",
      "Two lines on the wings, pass from the back court, one passive defender narrows the angle.",
    ),
    procedure: L(
      "Der Flügel startet, wenn RM den Ball hat, fängt im Lauf und springt aus dem Winkel ab. Danach wechselt er auf die andere Seite in die Kolonne.",
      "L'ailier démarre quand le DC a le ballon, reçoit en course et prend son appel dans l'angle. Ensuite il rejoint la colonne de l'autre côté.",
      "The wing starts when the centre back has the ball, catches on the run and takes off from the angle. Then he joins the line on the other side.",
    ),
    coaching: L(
      "Absprung möglichst nah an der Seitenlinie, Wurfbild variieren (kurze und lange Ecke).",
      "Appel près de la ligne de touche, varier la cible (premier et second poteau).",
      "Take off close to the side line, vary the target (near and far corner).",
    ),
    variants: L(
      "Verteidiger wird aktiv; Abschluss nur mit Dreher oder Heber; nach jedem Wurf zählt der Torhüter mit.",
      "Le défenseur devient actif ; finir seulement en roucoulette ou lob ; le gardien compte les arrêts.",
      "The defender becomes active; finish only with a spin or a lob; the goalkeeper counts the saves.",
    ),
    sketch: sketch(() => {
      const end = [35.2, 17.2] as const;
      return {
        tokens: [keeper(), me("LA", [31.5, 18.8]), me("LA", [29.6, 18.8]), me("RA", [31.5, 1.2]), me("RA", [29.6, 1.2]), me("RM", RM), op("1", lineSpot(7, 0.75))],
        arrows: [run([31.5, 18.8], end), pass(RM, end), shot(end)],
        ball: RM,
      };
    }),
  },
  {
    id: "finishing_back",
    focus: ["finishing", "back_court"],
    minutes: 15,
    players: "6-12",
    level: "basic",
    name: L("Rückraumwurf aus dem Lauf", "Tir de la base arrière en course", "Back court shot on the run"),
    setup: L(
      "Drei Rückraumpositionen, Stossbewegung auf die Lücke, Sprungwurf über einen Blockspieler.",
      "Trois postes arrière, attaque de l'intervalle, tir en suspension au-dessus d'un contreur.",
      "Three back court positions, attack the gap, jump shot over a blocking defender.",
    ),
    procedure: L(
      "RL spielt RM im Lauf an, RM stösst in drei Schritten auf den Block zu und wirft aus 9 m. Danach rotieren die Positionen.",
      "L'arrière gauche passe au DC lancé, qui attaque le contreur en trois appuis et tire à 9 m. Puis les postes tournent.",
      "LB passes to the running centre back, who drives at the block in three steps and shoots from 9 m. Then the positions rotate.",
    ),
    coaching: L(
      "Wurfarm früh oben, Wurf am höchsten Punkt, nicht immer in die gleiche Ecke.",
      "Bras armé tôt, lâcher au point le plus haut, varier les angles.",
      "Throwing arm up early, release at the highest point, do not always pick the same corner.",
    ),
    variants: L(
      "Wurf am Block vorbei (Hüftwurf); der Blockspieler darf einen Schritt heraustreten; Serie von fünf Würfen auf Zeit.",
      "Tir à côté du contreur (à la hanche) ; le contreur peut avancer d'un pas ; série de cinq tirs chronométrée.",
      "Shot past the block (hip shot); the blocker may step out once; a timed series of five shots.",
    ),
    sketch: sketch(() => {
      const end = [31.2, 10.6] as const;
      return {
        tokens: [keeper(), me("RL", RL), me("RM", RM), me("RR", RR), op("1", lineSpot(7, 0))],
        arrows: [pass(RL, end), run(RM, end), shot(end)],
        ball: RL,
      };
    }),
  },
  {
    id: "finishing_pivot",
    focus: ["finishing", "pivot"],
    minutes: 12,
    players: "4-8",
    level: "basic",
    name: L("Kreisanspiel und Abschluss", "Passe au pivot et finition", "Pivot pass and finish"),
    setup: L(
      "Kreisläufer sperrt gegen einen Verteidiger, Rückraum spielt in den Lauf, Abschluss mit Fallwurf.",
      "Le pivot fait écran, la base arrière passe dans la course, finition en tir en chute.",
      "Pivot screens a defender, back court passes into the run, finish with a falling shot.",
    ),
    procedure: L(
      "Der Kreisläufer löst sich vom Verteidiger zur Ballseite, RM spielt den Bodenpass oder hoch in die Hand, Abschluss aus der Drehung.",
      "Le pivot se démarque côté ballon, le DC joue à terre ou en l'air dans la main, finition en pivotant.",
      "The pivot gets free towards the ball, the centre back plays a bounce pass or high into the hand, finish out of the turn.",
    ),
    coaching: L(
      "Sicher fangen vor dem Drehen, Torhüter mit Täuschung bewegen.",
      "Sécuriser la réception avant de pivoter, faire bouger le gardien par une feinte.",
      "Secure the catch before turning, move the goalkeeper with a feint.",
    ),
    variants: L(
      "Verteidiger aktiv mit Körperkontakt; Anspiel von beiden Halbpositionen; Abschluss nach Wurftäuschung.",
      "Défenseur actif avec contact ; passes des deux postes arrière ; finition après feinte de tir.",
      "Active defender with contact; passes from both half positions; finish after a shot feint.",
    ),
    sketch: sketch(() => {
      const free = lineSpot(6.4, -0.12);
      return {
        tokens: [keeper(), me("KM", lineSpot(6.4, 0.1)), me("RM", [28.6, 10]), op("1", lineSpot(7.4, 0.25))],
        arrows: [run(lineSpot(6.4, 0.1), free), pass([28.6, 10], free), shot(free, false)],
        ball: [28.6, 10],
      };
    }),
  },
  {
    id: "finishing_feint_keeper",
    focus: ["finishing"],
    minutes: 12,
    players: "4-10",
    level: "basic",
    name: L("Wurftäuschung gegen den Torhüter", "Feinte de tir contre le gardien", "Shot feint against the goalkeeper"),
    setup: L(
      "Werfer in einer Kolonne auf 13 m, ein Zuspieler auf der Gegenseite, Torhüter im Tor.",
      "Tireurs en colonne à 13 m, un passeur de l'autre côté, gardien dans le but.",
      "Shooters in a line at 13 m, one passer on the other side, goalkeeper in goal.",
    ),
    procedure: L(
      "Der Werfer läuft an, bekommt den Ball auf 9 m, täuscht einen Wurf an und schliesst aus 7 bis 8 m in die andere Ecke ab.",
      "Le tireur s'élance, reçoit à 9 m, feinte un tir et finit à 7 ou 8 m dans l'autre coin.",
      "The shooter runs in, gets the ball at 9 m, feints a shot and finishes from 7 to 8 m into the other corner.",
    ),
    coaching: L(
      "Die Täuschung muss echt aussehen (Arm und Blick), dann ruhig bleiben und den Torhüter laufen lassen.",
      "La feinte doit être crédible (bras et regard), puis rester calme et laisser le gardien bouger.",
      "The feint must look real (arm and eyes), then stay calm and let the goalkeeper move.",
    ),
    variants: L(
      "Torhüter ruft vor dem Wurf eine Ecke; nur Bodenwürfe; Werfer entscheidet selbst zwischen Wurf und Täuschung.",
      "Le gardien annonce un coin ; seulement des tirs au sol ; le tireur choisit entre tir et feinte.",
      "The goalkeeper calls a corner; ground shots only; the shooter chooses between shot and feint.",
    ),
    sketch: sketch(() => {
      const catchAt = lineSpot(9.6, 0.15);
      const end = lineSpot(7.6, 0.08);
      return {
        tokens: [keeper(), me("1", lineSpot(13, 0.2)), me("2", lineSpot(14.8, 0.22)), me("Z", lineSpot(10, -0.35))],
        arrows: [run(lineSpot(13, 0.2), catchAt, end), pass(lineSpot(10, -0.35), catchAt), shot(end, false)],
        ball: lineSpot(10, -0.35),
      };
    }),
  },
  {
    id: "finishing_tired",
    focus: ["finishing", "back_court"],
    minutes: 12,
    players: "6-12",
    level: "advanced",
    name: L("Abschluss unter Belastung", "Finition sous fatigue", "Finishing under fatigue"),
    setup: L(
      "Zwei Hütchen an der Mittellinie, ein Zuspieler auf der Halbposition, Torhüter im Tor.",
      "Deux plots à la ligne médiane, un passeur au poste arrière, gardien dans le but.",
      "Two cones at the centre line, a passer at the half position, goalkeeper in goal.",
    ),
    procedure: L(
      "Sprint um das Hütchen, Pass im Lauf auf 10 m, sofort Wurf. Fünf Durchgänge ohne Pause, dann wechseln.",
      "Sprint autour du plot, passe en course à 10 m, tir immédiat. Cinq passages sans pause, puis changer.",
      "Sprint round the cone, pass on the run at 10 m, shoot at once. Five runs without a break, then swap.",
    ),
    coaching: L(
      "Auch müde die Wurftechnik halten: Schritte zählen, Arm hoch, Ziel vor dem Fangen wählen.",
      "Garder la technique même fatigué : compter les appuis, bras haut, choisir la cible avant la réception.",
      "Keep the technique when tired: count the steps, arm up, pick the target before the catch.",
    ),
    variants: L(
      "Mit Gegenspieler, der nach dem Hütchen nachläuft; Wurf nur in die Ecken unten; Wettkampf zwei Gruppen.",
      "Avec un défenseur qui poursuit après le plot ; tirs seulement en bas ; concours à deux groupes.",
      "With a defender chasing after the cone; shots only low; competition between two groups.",
    ),
    sketch: sketch(() => {
      const end = lineSpot(9.8, 0.25);
      return {
        tokens: [keeper(), me("1", [22.5, 13.5]), me("2", [21.2, 15.4]), me("Z", lineSpot(10.5, -0.35))],
        arrows: [run([22.5, 13.5], [24.6, 15.4], [26.6, 13.4], end), pass(lineSpot(10.5, -0.35), end), shot(end)],
        ball: lineSpot(10.5, -0.35),
        cones: [[24.6, 15.9], [24.6, 4.1]],
      };
    }),
  },
  {
    id: "wings_run_in",
    focus: ["wings", "pivot"],
    minutes: 15,
    players: "6-12",
    level: "advanced",
    name: L("Einlaufen Aussen zum zweiten Kreis", "Entrée de l'ailier en second pivot", "Wing runs in as a second pivot"),
    setup: L(
      "Linksaussen, Rückraum links und Kreisläufer gegen drei Verteidiger an der 6-m-Linie, Torhüter.",
      "Ailier gauche, arrière gauche et pivot contre trois défenseurs sur les 6 m, gardien.",
      "Left wing, left back and pivot against three defenders at the 6 m line, goalkeeper.",
    ),
    procedure: L(
      "Mit dem Pass zu RL läuft LA entlang der 6-m-Linie zwischen die Verteidiger 1 und 2 ein. RL spielt ihn an oder wirft, wenn die Abwehr zurückweicht.",
      "Sur la passe à l'arrière gauche, l'ailier entre le long des 6 m entre les défenseurs 1 et 2. L'arrière le sert ou tire si la défense recule.",
      "On the pass to LB, the left wing runs in along the 6 m line between defenders 1 and 2. LB passes to him or shoots if the defence drops back.",
    ),
    coaching: L(
      "Einlaufen im Rücken des Verteidigers, Hände früh zeigen, nicht in den Torraum treten.",
      "Entrer dans le dos du défenseur, montrer les mains tôt, ne pas marcher dans la zone.",
      "Run in behind the defender, show the hands early, do not step into the goal area.",
    ),
    variants: L(
      "Auch von rechts; mit Kreuzen RL und RM davor; Abwehr darf übergeben und übernehmen.",
      "Aussi à droite ; avec croisé arrière gauche et DC avant ; la défense peut se transmettre l'ailier.",
      "From the right too; with a cross of LB and centre back first; the defence may switch.",
    ),
    sketch: sketch(() => {
      const end = lineSpot(6.3, 0.55);
      return {
        tokens: [keeper(), me("LA", [36.2, 19.2]), me("RL", RL), me("KM", lineSpot(6.3, -0.12)), op("1", lineSpot(6.8, 0.72)), op("2", lineSpot(6.8, 0.4)), op("3", lineSpot(6.8, 0.08))],
        arrows: [run([36.2, 19.2], [35.1, 17.6], end), pass(RL, end)],
        ball: RL,
      };
    }),
  },
  {
    id: "wings_1v1_line",
    focus: ["wings"],
    minutes: 12,
    players: "4-10",
    level: "basic",
    name: L("Aussen 1 gegen 1 an der Seitenlinie", "Ailier 1 contre 1 le long de la touche", "Wing 1 on 1 at the side line"),
    setup: L(
      "Auf beiden Flügeln ein Angreifer mit Ball gegen einen Verteidiger vor der 6-m-Linie, Torhüter.",
      "Sur chaque aile un attaquant avec ballon contre un défenseur devant les 6 m, gardien.",
      "On each wing an attacker with the ball against a defender in front of the 6 m line, goalkeeper.",
    ),
    procedure: L(
      "Der Aussen täuscht nach innen an und geht aussen an der Seitenlinie vorbei, oder umgekehrt. Abschluss aus dem Winkel, dann die andere Seite.",
      "L'ailier feinte vers l'intérieur et passe le long de la touche, ou l'inverse. Finition dans l'angle, puis l'autre côté.",
      "The wing feints inside and goes past along the side line, or the other way round. Finish from the angle, then the other side.",
    ),
    coaching: L(
      "Tempo erst nach der Täuschung, Körper zwischen Ball und Verteidiger, Absprung weg vom Verteidiger.",
      "Accélérer après la feinte, corps entre ballon et défenseur, appel loin du défenseur.",
      "Speed up only after the feint, body between ball and defender, take off away from the defender.",
    ),
    variants: L(
      "Verteidiger startet erst auf Zuruf; maximal drei Sekunden; mit Anspiel aus dem Rückraum statt Ball in der Hand.",
      "Le défenseur part au signal ; trois secondes maximum ; avec passe de la base arrière.",
      "The defender starts on a call; three seconds at most; with a pass from the back court instead.",
    ),
    sketch: sketch(() => ({
      tokens: [keeper(), me("LA", [33, 18.8]), me("RA", [33, 1.2]), op("1", lineSpot(7, 0.72)), op("2", lineSpot(7, -0.72))],
      arrows: [dribble([33, 18.8], [34.4, 17.2], [35.6, 19]), shot([35.6, 19]), dribble([33, 1.2], [34.6, 2.4], [35.6, 3.4])],
      ball: [33, 18.8],
    })),
  },
  {
    id: "wings_fast_break_finish",
    focus: ["wings", "fast_break"],
    minutes: 12,
    players: "6-14",
    level: "basic",
    name: L("Gegenstoss-Abschluss auf dem Flügel", "Finition de contre-attaque à l'aile", "Fast break finish on the wing"),
    setup: L(
      "Flügelspieler an der Mittellinie, ein Zuspieler im Mittelkreis, Torhüter im Tor.",
      "Ailiers à la ligne médiane, un passeur au centre, gardien dans le but.",
      "Wings at the centre line, a passer in the centre circle, goalkeeper in goal.",
    ),
    procedure: L(
      "Der Flügel sprintet entlang der Seitenlinie, bekommt den langen Ball in den Lauf und schliesst ohne Prellen aus dem Winkel ab.",
      "L'ailier sprinte le long de la touche, reçoit la longue passe dans la course et finit dans l'angle sans dribbler.",
      "The wing sprints along the side line, gets the long ball into the run and finishes from the angle without bouncing.",
    ),
    coaching: L(
      "Blick über die Schulter zum Ball, Pass vor den Läufer, im Vollsprint fangen.",
      "Regard par-dessus l'épaule, passe devant le coureur, réception en plein sprint.",
      "Look over the shoulder to the ball, pass ahead of the runner, catch at full speed.",
    ),
    variants: L(
      "Torhüter spielt den Pass; ein Verteidiger läuft hinterher; Abschluss mit Heber.",
      "Le gardien fait la passe ; un défenseur poursuit ; finition en lob.",
      "The goalkeeper plays the pass; a defender chases; finish with a lob.",
    ),
    sketch: sketch(() => {
      const end = [35.4, 16.6] as const;
      return {
        tokens: [keeper(), me("LA", [21.4, 18.6]), me("LA", [21.4, 16.6]), me("Z", [21.4, 10])],
        arrows: [run([21.4, 18.6], [30, 18.6], end), pass([21.4, 10], [31.5, 18.2]), shot(end)],
        ball: [21.4, 10],
      };
    }),
  },
  {
    id: "back_1v1_breakthrough",
    focus: ["back_court"],
    minutes: 15,
    players: "4-12",
    level: "basic",
    name: L("Durchbruch 1 gegen 1 aus dem Rückraum", "Débordement 1 contre 1 de la base arrière", "Back court 1 on 1 breakthrough"),
    setup: L(
      "Ein Rückraumspieler mit Ball gegen einen Verteidiger in einer 4 m breiten Gasse (Hütchen), Torhüter.",
      "Un arrière avec ballon contre un défenseur dans un couloir de 4 m (plots), gardien.",
      "A back court player with the ball against a defender in a 4 m wide lane (cones), goalkeeper.",
    ),
    procedure: L(
      "Der Angreifer läuft mit Tempo an, täuscht zur einen Seite und bricht auf der anderen durch. Gelingt der Durchbruch, schliesst er ab.",
      "L'attaquant arrive lancé, feinte d'un côté et déborde de l'autre. S'il passe, il tire.",
      "The attacker comes in at speed, feints one way and breaks through on the other. If he gets past, he shoots.",
    ),
    coaching: L(
      "Tempo vor der Täuschung, Stemmschritt kurz und tief, Ball weg vom Verteidiger führen.",
      "Vitesse avant la feinte, appui de démarrage court et bas, ballon loin du défenseur.",
      "Speed before the feint, short and low plant step, keep the ball away from the defender.",
    ),
    variants: L(
      "Mit Zuspiel in den Lauf; Verteidiger startet auf 6 m und tritt heraus; Gasse enger machen.",
      "Avec passe dans la course ; le défenseur part des 6 m et sort ; couloir plus étroit.",
      "With a pass into the run; the defender starts at 6 m and steps out; a narrower lane.",
    ),
    sketch: sketch(() => ({
      tokens: [keeper(), me("RM", lineSpot(11.5, 0)), op("1", lineSpot(8, 0))],
      arrows: [dribble(lineSpot(11.5, 0), [29.6, 8.8], [31, 11.4]), shot([31, 11.4])],
      ball: lineSpot(11.5, 0),
      cones: [lineSpot(9.5, 0.2), lineSpot(9.5, -0.2), lineSpot(12, 0.17), lineSpot(12, -0.17)],
    })),
  },
  {
    id: "back_cross_2v2",
    focus: ["back_court", "passing"],
    minutes: 15,
    players: "4-12",
    level: "advanced",
    name: L("Kreuzen im Rückraum 2 gegen 2", "Croisé de la base arrière à 2 contre 2", "Back court cross 2 on 2"),
    setup: L(
      "RM und RL gegen zwei Verteidiger vor der 6-m-Linie, Torhüter.",
      "DC et arrière gauche contre deux défenseurs devant les 6 m, gardien.",
      "Centre back and left back against two defenders in front of the 6 m line, goalkeeper.",
    ),
    procedure: L(
      "RM stösst mit Ball schräg nach links, RL kreuzt hinter ihm durch. RM spielt ab oder wirft selbst, je nachdem, wie die Verteidiger übergeben.",
      "Le DC part en biais vers la gauche, l'arrière gauche croise derrière lui. Le DC passe ou tire selon la réaction des défenseurs.",
      "The centre back drives diagonally left, the left back crosses behind him. The centre back passes or shoots, depending on how the defenders switch.",
    ),
    coaching: L(
      "Der Ballführer muss den Verteidiger binden (Torgefahr), der Kreuzende startet spät und mit Tempo.",
      "Le porteur doit fixer son défenseur (menace de tir), le croiseur part tard et vite.",
      "The ball carrier must tie his defender (threat to score), the crossing player starts late and fast.",
    ),
    variants: L(
      "Mit Kreisläufer (3 gegen 3); Kreuzen auf der rechten Seite; nach dem Kreuzen Rückpass (Gegenkreuzen).",
      "Avec pivot (3 contre 3) ; croisé à droite ; après le croisé, passe en retour (contre-croisé).",
      "With a pivot (3 on 3); cross on the right side; after the cross a pass back (counter cross).",
    ),
    sketch: sketch(() => {
      const rmEnd = [30.4, 12.4] as const;
      const rlEnd = [28.8, 13.8] as const;
      return {
        tokens: [keeper(), me("RM", RM), me("RL", RL), op("1", lineSpot(7.6, 0.1)), op("2", lineSpot(7.6, 0.42))],
        arrows: [dribble(RM, rmEnd), run(RL, [28.4, 15.4], rlEnd), pass(rmEnd, rlEnd)],
        ball: RM,
      };
    }),
  },
  {
    id: "back_long_shot_block",
    focus: ["back_court", "finishing"],
    minutes: 12,
    players: "4-10",
    level: "advanced",
    name: L("Fernwurf über den Block", "Tir de loin au-dessus du contre", "Long shot over the block"),
    setup: L(
      "Werfer auf 11 m, Zuspieler auf der Halbposition, ein Blockspieler auf 8 m, Torhüter.",
      "Tireur à 11 m, passeur au poste arrière, un contreur à 8 m, gardien.",
      "Shooter at 11 m, passer at the half position, a blocker at 8 m, goalkeeper.",
    ),
    procedure: L(
      "Pass in den Lauf, ein bis zwei Schritte Anlauf, Sprungwurf über oder neben den Block. Der Block bewegt sich mit dem Wurfarm.",
      "Passe dans la course, un ou deux appuis d'élan, tir en suspension au-dessus ou à côté du contre. Le contreur suit le bras.",
      "Pass into the run, one or two steps of run-up, jump shot over or past the block. The blocker follows the throwing arm.",
    ),
    coaching: L(
      "Hoch abspringen und spät werfen, Wurfarm am Block vorbei führen, Torhüter hinter dem Block beachten.",
      "Sauter haut et lâcher tard, bras à côté du contre, attention au gardien derrière le contre.",
      "Jump high and release late, take the arm past the block, mind the goalkeeper behind the block.",
    ),
    variants: L(
      "Schlagwurf ohne Sprung; zwei Blockspieler; Werfer darf auch durchbrechen, wenn der Block zu früh springt.",
      "Tir à l'appui sans saut ; deux contreurs ; le tireur peut déborder si le contreur saute trop tôt.",
      "Set shot without jump; two blockers; the shooter may break through if the block jumps too early.",
    ),
    sketch: sketch(() => {
      const end = [29.2, 10.3] as const;
      return {
        tokens: [keeper(), me("RM", [28, 10]), me("RL", RL), op("1", lineSpot(8.4, 0))],
        arrows: [pass(RL, end), run([28, 10], end), shot(end)],
        ball: RL,
      };
    }),
  },
  {
    id: "back_parallel",
    focus: ["back_court", "passing"],
    minutes: 15,
    players: "5-12",
    level: "advanced",
    name: L("Parallelstoss 3 gegen 2", "Attaque en parallèle à 3 contre 2", "Parallel drive 3 on 2"),
    setup: L(
      "Drei Rückraumspieler gegen zwei Verteidiger auf 8 m, Torhüter.",
      "Trois arrières contre deux défenseurs à 8 m, gardien.",
      "Three back court players against two defenders at 8 m, goalkeeper.",
    ),
    procedure: L(
      "RM stösst in die Lücke zwischen die Verteidiger und bindet beide. RR stösst parallel mit und bekommt den Ball in den Lauf zum Abschluss.",
      "Le DC attaque l'intervalle et fixe les deux défenseurs. L'arrière droit attaque en parallèle et reçoit dans la course pour finir.",
      "The centre back drives into the gap and ties both defenders. The right back drives in parallel and gets the ball on the run to finish.",
    ),
    coaching: L(
      "Jeder Angreifer zieht zum Tor, nicht quer; Pass erst, wenn der Verteidiger gebunden ist.",
      "Chaque attaquant va vers le but, pas en travers ; passer seulement quand le défenseur est fixé.",
      "Every attacker goes towards the goal, not across; pass only once the defender is tied.",
    ),
    variants: L(
      "3 gegen 3; Start mit Pass von der anderen Seite; maximal zwei Pässe bis zum Wurf.",
      "3 contre 3 ; départ avec passe de l'autre côté ; deux passes maximum avant le tir.",
      "3 on 3; start with a pass from the other side; at most two passes before the shot.",
    ),
    sketch: sketch(() => {
      const rmEnd = [30.8, 9.6] as const;
      const rrEnd = [31.2, 4.6] as const;
      return {
        tokens: [keeper(), me("RL", RL), me("RM", RM), me("RR", RR), op("1", lineSpot(8, 0.22)), op("2", lineSpot(8, -0.22))],
        arrows: [dribble(RM, rmEnd), run(RR, rrEnd), pass(rmEnd, rrEnd)],
        ball: RM,
      };
    }),
  },
  {
    id: "pivot_position_fight",
    focus: ["pivot"],
    minutes: 10,
    players: "3-8",
    level: "basic",
    name: L("Kreisläufer: Position erkämpfen", "Pivot : gagner sa position", "Pivot: win the position"),
    setup: L(
      "Kreisläufer gegen einen Verteidiger an der 6-m-Linie, zwei Zuspieler im Rückraum.",
      "Pivot contre un défenseur sur les 6 m, deux passeurs à la base arrière.",
      "Pivot against a defender at the 6 m line, two passers in the back court.",
    ),
    procedure: L(
      "Die Zuspieler passen sich den Ball zu; der Kreisläufer verschiebt mit und sucht die Lücke neben dem Verteidiger. Ist er frei, kommt der Ball.",
      "Les passeurs se font des passes ; le pivot se déplace et cherche l'espace à côté du défenseur. S'il est libre, il reçoit.",
      "The passers pass to each other; the pivot shifts along and looks for the space beside the defender. When he is free, the ball comes.",
    ),
    coaching: L(
      "Tiefer Schwerpunkt, mit Hüfte und Rücken den Platz sichern, Arm als Ziel zeigen.",
      "Centre de gravité bas, garder la place avec hanches et dos, montrer la main comme cible.",
      "Low centre of gravity, secure the space with hips and back, show the arm as a target.",
    ),
    variants: L(
      "Verteidiger spielt aktiv mit Hand am Körper; zwei Verteidiger; Abschluss mit Fallwurf.",
      "Défenseur actif avec la main au corps ; deux défenseurs ; finition en chute.",
      "Defender plays actively with a hand on the body; two defenders; finish with a falling shot.",
    ),
    sketch: sketch(() => {
      const free = [33.5, 12.1] as const;
      return {
        tokens: [keeper(), me("KM", [33.7, 10]), me("RM", [28.6, 10]), me("RL", RL), op("1", [32, 10.8])],
        arrows: [screen([33.7, 10], free), pass(RL, [28.6, 10]), pass([28.6, 10], free)],
        ball: RL,
      };
    }),
  },
  {
    id: "pivot_screen_roll",
    focus: ["pivot", "back_court"],
    minutes: 15,
    players: "4-10",
    level: "advanced",
    name: L("Sperren und Abrollen 2 gegen 2", "Écran et roulé à 2 contre 2", "Screen and roll 2 on 2"),
    setup: L(
      "Rückraum links und Kreisläufer gegen zwei Verteidiger, Torhüter.",
      "Arrière gauche et pivot contre deux défenseurs, gardien.",
      "Left back and pivot against two defenders, goalkeeper.",
    ),
    procedure: L(
      "Der Kreisläufer stellt die Sperre innen am Verteidiger von RL. RL stösst an der Sperre vorbei; hilft der zweite Verteidiger, rollt der Kreisläufer ab und bekommt den Ball.",
      "Le pivot pose l'écran à l'intérieur du défenseur de l'arrière gauche. L'arrière passe l'écran ; si le second défenseur aide, le pivot roule et reçoit.",
      "The pivot sets the screen on the inside of LB's defender. LB drives past the screen; if the second defender helps, the pivot rolls off and gets the ball.",
    ),
    coaching: L(
      "Sperre breit und ruhig stellen (kein Stoss), Timing: RL startet, wenn die Sperre steht.",
      "Écran large et immobile (sans pousser), timing : l'arrière part quand l'écran est posé.",
      "Set the screen wide and still (no push), timing: LB starts when the screen stands.",
    ),
    variants: L(
      "Sperre aussen statt innen; mit RM als drittem Angreifer; Abwehr darf tauschen.",
      "Écran extérieur au lieu d'intérieur ; avec le DC en troisième attaquant ; la défense peut changer.",
      "Screen on the outside instead; with the centre back as a third attacker; the defence may switch.",
    ),
    sketch: sketch(() => {
      const scr = [33.5, 13.6] as const;
      const drive = [31.4, 13] as const;
      return {
        tokens: [keeper(), me("RL", RL), me("KM", [33.7, 10]), op("1", lineSpot(7, 0.44)), op("2", lineSpot(7.6, -0.12))],
        arrows: [screen([33.7, 10], scr), dribble(RL, drive)],
        ball: RL,
      };
    }),
  },
  {
    id: "seven_m_routine",
    focus: ["seven_m"],
    minutes: 10,
    players: "2-6",
    level: "basic",
    name: L("7-m-Routine mit Druck", "Routine de 7 m sous pression", "Penalty routine under pressure"),
    setup: L(
      "Jeder Werfer hat eine feste Routine, nach einem Sprint direkt an die Linie, Serie von fünf Würfen.",
      "Chaque tireur a une routine fixe, directement à la ligne après un sprint, série de cinq tirs.",
      "Each shooter has a fixed routine, straight to the line after a sprint, series of five shots.",
    ),
    procedure: L(
      "Sprint von der Mittellinie um das Hütchen, Ball holen, Routine (Atmen, Ziel, Wurf) an der 7-m-Linie. Treffer werden gezählt.",
      "Sprint depuis la ligne médiane autour du plot, prendre le ballon, routine (respirer, viser, tirer) aux 7 m. On compte les buts.",
      "Sprint from the centre line round the cone, take the ball, routine (breathe, target, shot) at the 7 m line. Goals are counted.",
    ),
    coaching: L(
      "Ziel vor dem Pfiff festlegen, ruhiger Atem, Torhüter nicht anschauen.",
      "Choisir la cible avant le coup de sifflet, respiration calme, ne pas regarder le gardien.",
      "Decide the target before the whistle, calm breathing, do not watch the goalkeeper.",
    ),
    variants: L(
      "Team zuschauend mit Lärm; nach jedem Fehlwurf Strafrunde; der Torhüter darf sich vorher bewegen.",
      "L'équipe regarde et fait du bruit ; tour de pénalité après chaque échec ; le gardien peut bouger avant.",
      "The team watches and makes noise; a penalty lap after each miss; the goalkeeper may move beforehand.",
    ),
    sketch: sketch(() => ({
      tokens: [keeper(), me("1", [32.4, 10]), me("2", [23.4, 14.6])],
      arrows: [run([23.4, 14.6], [21.6, 12.6], [27, 10.8]), shot([32.4, 10], false)],
      ball: [32.4, 10],
      cones: [[21.4, 14.6]],
    })),
  },
  {
    id: "seven_m_duel",
    focus: ["seven_m", "goalkeeping"],
    minutes: 10,
    players: "3-8",
    level: "basic",
    name: L("7-m-Duell Werfer gegen Torhüter", "Duel de 7 m tireur contre gardien", "Penalty duel shooter against goalkeeper"),
    setup: L(
      "Werfer in einer Kolonne hinter der 9-m-Linie, ein Torhüter im Tor, ein Schreiber für die Punkte.",
      "Tireurs en colonne derrière les 9 m, un gardien dans le but, un marqueur pour les points.",
      "Shooters in a line behind the 9 m line, a goalkeeper in goal, someone to keep score.",
    ),
    procedure: L(
      "Jeder Werfer hat einen Wurf, der Torhüter kennt die Reihenfolge. Treffer ein Punkt für die Werfer, Parade ein Punkt für den Torhüter. Bis zehn.",
      "Chaque tireur a un tir, le gardien connaît l'ordre. Un but : un point pour les tireurs, un arrêt : un point pour le gardien. Jusqu'à dix.",
      "Each shooter has one shot, the goalkeeper knows the order. A goal is a point for the shooters, a save a point for the goalkeeper. First to ten.",
    ),
    coaching: L(
      "Werfer: nicht die Ecke wechseln, weil der Torhüter sich bewegt. Torhüter: spät reagieren, Werfer lesen.",
      "Tireur : ne pas changer de coin parce que le gardien bouge. Gardien : réagir tard, lire le tireur.",
      "Shooter: do not change corners because the goalkeeper moves. Goalkeeper: react late, read the shooter.",
    ),
    variants: L(
      "Zwei Torhüter abwechselnd; Werfer müssen vorher die Ecke einem Mitspieler zeigen; Wurf nach Belastung.",
      "Deux gardiens en alternance ; le tireur montre le coin à un partenaire avant ; tir après effort.",
      "Two goalkeepers in turn; shooters show the corner to a team-mate beforehand; shot after a sprint.",
    ),
    sketch: sketch(() => ({
      tokens: [keeper(), me("1", [32.4, 10]), me("2", [29.6, 12.6]), me("3", [29.6, 7.4])],
      arrows: [shot([32.4, 10], true)],
      ball: [32.4, 10],
    })),
  },
];
