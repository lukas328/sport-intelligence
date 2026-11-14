/**
 * Ratgeber: guides that answer a coach's real question and are useful without the product
 * (docs/site/SEO.md, «Plan»). Bodies in content/ratgeber/{locale}/{slug}.mdx. A guide exists in
 * German and, where `locales` says so, in French and English; the others are listed in those
 * languages as German pages (hreflang de-CH only).
 *
 * `title` is the question (h1), `answer` the two or three sentences that answer it (lead under the
 * title, and the start of the meta description), `metaTitle` the short title for the browser tab.
 */
import type { HelpLocale } from "../help";

export type GuideGroup = "filmen" | "auswerten" | "training" | "verein" | "wissen";

export interface Guide {
  slug: string;
  group: GuideGroup;
  published: string;
  updated: string;
  locales: HelpLocale[];
  title: Partial<Record<HelpLocale, string>> & { de: string };
  metaTitle: Partial<Record<HelpLocale, string>> & { de: string };
  answer: Partial<Record<HelpLocale, string>> & { de: string };
  description: Partial<Record<HelpLocale, string>> & { de: string };
  related: string[];
}

export const GUIDES: Guide[] = [
  {
    slug: "handballspiel-filmen",
    group: "filmen",
    published: "2026-11-13",
    updated: "2026-11-13",
    locales: ["de", "fr", "en"],
    title: {
      de: "Wie filme ich ein Handballspiel mit dem Handy?",
      fr: "Comment filmer un match de handball avec un téléphone ?",
      en: "How do I film a handball match with a phone?",
    },
    metaTitle: { de: "Handballspiel mit dem Handy filmen", fr: "Filmer un match de handball au téléphone", en: "Filming a handball match with a phone" },
    answer: {
      de: "Stell das Handy quer auf ein Stativ, so hoch wie möglich und auf Höhe der Mittellinie, und nimm den Weitwinkel (0,5×), damit beide Tore und Torräume im Bild sind. Starte vor dem Anpfiff, zoome und schwenke nicht, und lass die Aufnahme bis zum Schluss laufen.",
      fr: "Pose le téléphone à l'horizontale sur un trépied, le plus haut possible et à hauteur de la ligne médiane, et prends le grand-angle (0,5×) pour avoir les deux buts et les zones de but dans l'image. Lance l'enregistrement avant le coup d'envoi, ne zoome pas, ne pivote pas, et laisse tourner jusqu'à la fin.",
      en: "Put the phone in landscape on a tripod, as high as possible and level with the halfway line, and use the wide angle (0.5×) so both goals and goal areas are in the picture. Start before throw-off, do not zoom or pan, and let it run to the end.",
    },
    description: {
      de: "Standort, Höhe, Stativ, Einstellungen, Akku und Speicher: so filmst du ein Handballspiel mit dem Handy, damit du es danach auswerten kannst.",
      fr: "Emplacement, hauteur, trépied, réglages, batterie et mémoire : comment filmer un match de handball au téléphone pour pouvoir l'analyser ensuite.",
      en: "Position, height, tripod, settings, battery and storage: how to film a handball match with a phone so you can analyse it afterwards.",
    },
    related: ["spiel-auswerten-20-minuten", "video-im-verein-einwilligung", "wege-zur-videoanalyse"],
  },
  {
    slug: "videoanalyse-amateurteam",
    group: "auswerten",
    published: "2026-11-13",
    updated: "2026-11-13",
    locales: ["de", "fr", "en"],
    title: {
      de: "Was bringt Videoanalyse einem Amateurteam?",
      fr: "Qu'apporte l'analyse vidéo à une équipe amateur ?",
      en: "What does video analysis give an amateur team?",
    },
    metaTitle: { de: "Videoanalyse im Amateurhandball", fr: "L'analyse vidéo en handball amateur", en: "Video analysis for amateur handball teams" },
    answer: {
      de: "Sie zeigt dir, was im Spiel wirklich passiert ist, und deinem Team Szenen statt Worte. Sie ersetzt weder das Training noch dein Auge, und sie kostet Zeit. Am meisten bringt sie mit einer Frage pro Spiel und wenigen Szenen.",
      fr: "Elle te montre ce qui s'est vraiment passé pendant le match, et à ton équipe des scènes plutôt que des mots. Elle ne remplace ni l'entraînement ni ton œil, et elle prend du temps. Elle apporte le plus avec une question par match et peu de scènes.",
      en: "It shows you what really happened in the match, and shows your team scenes instead of words. It replaces neither training nor your eye, and it takes time. It helps most with one question per match and a few scenes.",
    },
    description: {
      de: "Was Videoanalyse einem Amateur-Handballteam wirklich bringt, was nicht, wie viel Zeit sie kostet und wie du klein anfängst.",
      fr: "Ce que l'analyse vidéo apporte vraiment à une équipe de handball amateur, ce qu'elle n'apporte pas, combien de temps elle prend et comment commencer.",
      en: "What video analysis really gives an amateur handball team, what it does not, how much time it takes and how to start small.",
    },
    related: ["spiel-auswerten-20-minuten", "szenen-im-training-zeigen", "wege-zur-videoanalyse"],
  },
  {
    slug: "spiel-auswerten-20-minuten",
    group: "auswerten",
    published: "2026-11-13",
    updated: "2026-11-13",
    locales: ["de", "fr"],
    title: { de: "Wie werte ich ein Spiel in 20 Minuten aus?", fr: "Comment analyser un match en 20 minutes ?" },
    metaTitle: { de: "Handballspiel in 20 Minuten auswerten", fr: "Analyser un match en 20 minutes" },
    answer: {
      de: "Schau nicht das ganze Spiel noch einmal. Nimm dir eine Frage vor, spring zu den Toren und Gegentoren und mach zu jeder Szene einen Strich. Nach 20 Minuten hast du ein Muster und drei Szenen für das Team.",
      fr: "Ne revois pas tout le match. Prends une question, saute aux buts marqués et encaissés et fais un bâton pour chaque scène. Après 20 minutes, tu as une tendance et trois scènes pour l'équipe.",
    },
    description: { de: "Eine Frage, der Spielverlauf, die Gegentore, eine Strichliste und drei Szenen: so wertest du ein Handballspiel in 20 Minuten aus. Mit Vorlage.", fr: "Une question, l'évolution du score, les buts encaissés, une feuille de pointage et trois scènes : analyser un match de handball en 20 minutes." },
    related: ["gegentore-nach-position", "gegenstoss-und-ballverluste", "szenen-im-training-zeigen"],
  },
  {
    slug: "gegentore-nach-position",
    group: "auswerten",
    published: "2026-11-13",
    updated: "2026-11-13",
    locales: ["de", "fr"],
    title: { de: "Wie lese ich Gegentore nach Position?", fr: "Comment lire les buts encaissés par poste ?" },
    metaTitle: { de: "Gegentore nach Position lesen", fr: "Buts encaissés par poste" },
    answer: {
      de: "Zähl die Gegentore danach, von wo geworfen wurde: Aussen, Rückraum links, Mitte, rechts, Kreis, Siebenmeter, Gegenstoss. Eine Häufung zeigt dir, wo du zuerst hinschaust. Ob es an der Abwehr, am Torhüter oder an Ballverlusten liegt, sagt dir erst die Szene.",
      fr: "Compte les buts encaissés selon l'endroit d'où le tir est parti : ailes, arrière gauche, demi-centre, arrière droit, pivot, jet de 7 mètres, contre-attaque. Une accumulation te montre où regarder en premier. Si c'est la défense, le gardien ou les pertes de balle, seule la scène te le dit.",
    },
    description: { de: "Gegentore nach Wurfposition zählen, Häufungen richtig lesen und typische Ursachen erkennen: Rückraum, Aussen, Kreis, Siebenmeter, Gegenstoss.", fr: "Compter les buts encaissés selon la position du tir, bien lire les accumulations et reconnaître les causes : arrières, ailes, pivot, 7 mètres." },
    related: ["spiel-auswerten-20-minuten", "wurfquote-torhueterquote", "handball-begriffe"],
  },
  {
    slug: "gegenstoss-und-ballverluste",
    group: "auswerten",
    published: "2026-11-13",
    updated: "2026-11-13",
    locales: ["de", "fr"],
    title: { de: "Wie werte ich Gegenstösse und Ballverluste aus?", fr: "Comment analyser contre-attaques et pertes de balle ?" },
    metaTitle: { de: "Gegenstösse und Ballverluste auswerten", fr: "Contre-attaques et pertes de balle" },
    answer: {
      de: "Zähl, wie viele Tore beide Teams nach Gegenstoss werfen, und schau dir die Ballverluste davor an. Meist liegt die Ursache nicht im Rückzug, sondern ein paar Sekunden vorher: ein Fehlpass, ein Schrittfehler, ein überhasteter Wurf.",
      fr: "Compte combien de buts les deux équipes marquent sur contre-attaque, et regarde les pertes de balle juste avant. Le plus souvent, la cause n'est pas dans le repli, mais quelques secondes plus tôt : une mauvaise passe, un marcher, un tir précipité.",
    },
    description: { de: "Gegenstoss, zweite Welle, Ballverlust: was du zählst, wo du im Video hinschaust und was daraus fürs Training folgt.", fr: "Contre-attaque, deuxième vague, perte de balle : ce que tu comptes, où regarder dans la vidéo et ce que ça donne pour l'entraînement." },
    related: ["spiel-auswerten-20-minuten", "gegentore-nach-position", "szenen-im-training-zeigen"],
  },
  {
    slug: "wurfquote-torhueterquote",
    group: "auswerten",
    published: "2026-11-13",
    updated: "2026-11-13",
    locales: ["de", "fr"],
    title: { de: "Wie rechne ich Wurfquote und Torhüterquote?", fr: "Comment calculer le pourcentage au tir et le pourcentage d'arrêts ?" },
    metaTitle: { de: "Wurfquote und Torhüterquote berechnen", fr: "Pourcentage au tir et d'arrêts" },
    answer: {
      de: "Wurfquote: Tore geteilt durch Würfe, mal 100. Torhüterquote: Paraden geteilt durch Paraden plus Gegentore, mal 100. Schreib immer die Basis dazu, zum Beispiel «12 von 20, 60 %», und zähl jedes Mal gleich.",
      fr: "Pourcentage de réussite au tir : buts divisés par tirs, fois 100. Pourcentage d'arrêts du gardien : arrêts divisés par arrêts plus buts encaissés, fois 100. Écris toujours la base, par exemple « 12 sur 20, 60 % », et compte chaque fois de la même façon.",
    },
    description: { de: "Wurfquote und Torhüterquote im Handball richtig berechnen: Formeln, was als Wurf zählt, eine Tabelle zum Übernehmen und fünf Regeln für ehrliche Zahlen.", fr: "Pourcentage de réussite au tir et d'arrêts au handball : les formules, ce qui compte comme tir, un tableau et cinq règles pour des chiffres honnêtes." },
    related: ["gegentore-nach-position", "handball-begriffe", "spiel-auswerten-20-minuten"],
  },
  {
    slug: "szenen-im-training-zeigen",
    group: "training",
    published: "2026-11-13",
    updated: "2026-11-13",
    locales: ["de", "fr"],
    title: { de: "Wie zeige ich Szenen, ohne das halbe Training zu verlieren?", fr: "Comment montrer des scènes sans perdre la moitié de l'entraînement ?" },
    metaTitle: { de: "Videositzung: Szenen im Training zeigen", fr: "Séance vidéo à l'entraînement" },
    answer: {
      de: "Zeig höchstens fünf Szenen zu einem Thema, in zehn Minuten. Beginne mit einer guten Szene, sag vorher, worauf alle schauen sollen, und geh danach gleich in die Übung dazu.",
      fr: "Montre au plus cinq scènes sur un thème, en dix minutes. Commence par une bonne scène, dis avant à quoi tout le monde doit faire attention, et passe ensuite tout de suite à l'exercice qui va avec.",
    },
    description: { de: "Eine Videositzung in zehn Minuten: ein Thema, drei bis fünf Szenen, wie du darüber sprichst und was bei Kindern und Jugendlichen gilt.", fr: "Une séance vidéo en dix minutes : un thème, trois à cinq scènes, comment en parler et ce qui vaut avec des enfants et des jeunes." },
    related: ["spiel-auswerten-20-minuten", "videoanalyse-amateurteam", "video-im-verein-einwilligung"],
  },
  {
    slug: "video-im-verein-einwilligung",
    group: "verein",
    published: "2026-11-13",
    updated: "2026-11-13",
    locales: ["de", "fr", "en"],
    title: {
      de: "Was gilt beim Filmen im Verein: Einwilligung, Kinder, Aufbewahrung?",
      fr: "Filmer au club : consentement, enfants, conservation, que faut-il savoir ?",
      en: "Filming in a club: consent, children, retention. What applies?",
    },
    metaTitle: { de: "Video im Verein: Einwilligung und Kinder", fr: "Vidéo au club : consentement et enfants", en: "Club video: consent and children" },
    answer: {
      de: "In der Schweiz hat jede Person ein Recht am eigenen Bild, und wer im Video erkennbar ist, dessen Personendaten bearbeitest du. Für die Analyse im Team heisst das: vorher informieren, für einen klaren Zweck filmen, nur dem Team zeigen, um Einwilligung fragen und löschen, wenn das Video nicht mehr gebraucht wird. Für Kinder entscheiden die Eltern.",
      fr: "En Suisse, chaque personne a un droit à sa propre image, et quiconque est reconnaissable dans la vidéo voit ses données personnelles traitées. Pour l'analyse en équipe, cela veut dire : informer avant, filmer dans un but précis, ne montrer qu'à l'équipe, demander le consentement et effacer quand la vidéo ne sert plus. Pour les enfants, ce sont les parents qui décident.",
      en: "In Switzerland everyone has a right to their own image, and anyone recognisable in a video is personal data. For team analysis that means: inform beforehand, film for a clear purpose, show it only to the team, ask for consent and delete the video when it is no longer needed. For children, the parents decide.",
    },
    description: {
      de: "Spiele filmen im Verein: was in der Schweiz gilt (EDÖB, Swiss Olympic), Einwilligung von Kindern und Jugendlichen, Aufbewahrung und ein Mustertext.",
      fr: "Filmer les matchs au club : ce qui vaut en Suisse (PFPDT, Swiss Olympic), consentement des enfants et des jeunes, conservation, et un modèle de texte.",
      en: "Filming matches in a club: what applies in Switzerland (FDPIC, Swiss Olympic), consent of children and young people, retention, and a sample text.",
    },
    related: ["handballspiel-filmen", "szenen-im-training-zeigen", "videoanalyse-amateurteam"],
  },
  {
    slug: "handball-begriffe",
    group: "wissen",
    published: "2026-11-13",
    updated: "2026-11-13",
    locales: ["de", "fr"],
    title: { de: "Was bedeuten die Begriffe der Spielanalyse?", fr: "Que veulent dire les termes de l'analyse de match ?" },
    metaTitle: { de: "Handball-Begriffe kurz erklärt", fr: "Les termes du handball expliqués" },
    answer: {
      de: "Hier stehen die Wörter, die in Spielanalyse und Statistik immer wieder vorkommen: Positionen, Abwehrsysteme, Spielphasen, Wurfquote und mehr. Wo die Schweiz und Deutschland verschiedene Wörter brauchen, stehen beide, dazu die Begriffe auf Französisch und Englisch.",
      fr: "Voici les mots qui reviennent sans cesse dans l'analyse de match et les statistiques : postes, systèmes défensifs, phases de jeu, pourcentage au tir et plus encore. Pour chaque terme, tu trouves aussi le mot allemand et anglais.",
    },
    description: { de: "Rückraum, Kreisläufer, 6:0, 5:1, 3:2:1, Gegenstoss, Wurfquote, Torhüterquote: die Begriffe der Handball-Spielanalyse kurz erklärt, mit fr und en.", fr: "Arrière, pivot, 6-0, 5-1, 3-2-1, contre-attaque, pourcentage au tir et d'arrêts : les termes de l'analyse de match au handball, avec de et en." },
    related: ["gegentore-nach-position", "wurfquote-torhueterquote", "gegenstoss-und-ballverluste"],
  },
  {
    slug: "wege-zur-videoanalyse",
    group: "wissen",
    published: "2026-11-13",
    updated: "2026-11-13",
    locales: ["de", "fr"],
    title: { de: "Welche Wege zur Videoanalyse gibt es für ein Handballteam?", fr: "Quelles solutions d'analyse vidéo pour une équipe de handball ?" },
    metaTitle: { de: "Wege zur Videoanalyse im Vergleich", fr: "Analyse vidéo : les solutions comparées" },
    answer: {
      de: "Vier Wege: das Video von Hand durchsehen und schneiden, eine automatische Kamera, eine Analyse-Software zum Markieren und eine automatische Analyse wie Handball Intelligence. Welcher passt, hängt von deiner Zeit, deinem Budget und deiner Halle ab.",
      fr: "Quatre solutions : revoir et découper la vidéo à la main, une caméra automatique, un logiciel pour marquer les scènes et une analyse automatique comme Handball Intelligence. Le bon choix dépend de ton temps, de ton budget et de ta salle.",
    },
    description: { de: "Von Hand schneiden, automatische Kamera, Analyse-Software oder automatische Analyse: die Wege zur Videoanalyse im Handball ehrlich verglichen.", fr: "À la main, caméra automatique, logiciel d'analyse ou analyse automatique : les solutions d'analyse vidéo au handball, comparées honnêtement." },
    related: ["videoanalyse-amateurteam", "handballspiel-filmen", "spiel-auswerten-20-minuten"],
  },
];
