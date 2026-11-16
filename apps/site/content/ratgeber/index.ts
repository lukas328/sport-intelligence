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
  /** what Handball Intelligence takes off the coach's hands for this question (honest, only what it can do) */
  product?: Partial<Record<HelpLocale, string>>;
  related: string[];
}

export const GUIDES: Guide[] = [
  {
    slug: "handballspiel-filmen",
    group: "filmen",
    published: "2026-11-13",
    updated: "2026-11-16",
    locales: ["de", "fr", "en"],
    title: {
      de: "Wie filme ich ein Handballspiel mit Handy oder Kamera?",
      fr: "Comment filmer un match de handball avec un téléphone ou une caméra ?",
      en: "How do I film a handball match with a phone or camera?",
    },
    metaTitle: { de: "Handballspiel filmen mit Handy oder Kamera", fr: "Filmer un match de handball : téléphone ou caméra", en: "Filming a handball match: phone or camera" },
    answer: {
      de: "Stell Handy oder Kamera quer auf ein Stativ, so hoch wie möglich und auf Höhe der Mittellinie, so dass beide Tore und Torräume im Bild sind; am Handy hilft der Weitwinkel (0,5×). Starte vor dem Anpfiff, zoome nicht, und lass die Aufnahme bis zum Schluss laufen. Am besten steht die Kamera fest; schwenken geht auch, dann findet die Analyse das Feld schwerer.",
      fr: "Pose le téléphone ou la caméra à l'horizontale sur un trépied, le plus haut possible et à hauteur de la ligne médiane, pour avoir les deux buts et les zones de but dans l'image ; au téléphone, le grand-angle (0,5×) aide. Lance l'enregistrement avant le coup d'envoi, ne zoome pas, et laisse tourner jusqu'à la fin. Le mieux, c'est fixe ; suivre le jeu marche aussi, l'analyse trouve alors le terrain plus difficilement.",
      en: "Put the phone or camera in landscape on a tripod, as high as possible and level with the halfway line, so both goals and goal areas are in the picture; on a phone the wide angle (0.5×) helps. Start before throw-off, do not zoom, and let it run to the end. Fixed is best; panning works too, the analysis then finds the court harder.",
    },
    description: {
      de: "Standort, Höhe, Stativ, Einstellungen, Akku und Speicher: so filmst du ein Handballspiel mit Handy oder Kamera, damit du es danach auswerten kannst.",
      fr: "Emplacement, hauteur, trépied, réglages, batterie et mémoire : comment filmer un match de handball au téléphone ou à la caméra pour pouvoir l'analyser ensuite.",
      en: "Position, height, tripod, settings, battery and storage: how to film a handball match with a phone or camera so you can analyse it afterwards.",
    },
    product: { de: "Die App nimmt die Datei so, wie Handy oder Kamera sie speichern, auch mehrere Dateien pro Spiel oder einen Download-Link von Veo. Die Analyse findet das Feld selbst und folgt auch einer Kamera, die mitschwenkt; ob das Feld passt, bestätigst du mit einem Tipp. Beim Hochladen erinnert dich die App an die wichtigsten Punkte.", fr: "L'app prend le fichier tel que le téléphone ou la caméra l'enregistre, aussi plusieurs fichiers par match ou un lien de téléchargement de Veo. L'analyse trouve le terrain elle-même et suit aussi une caméra qui pivote ; s'il est juste, tu le confirmes d'une touche. Au téléversement, l'app te rappelle les points importants.", en: "The app takes the file as the phone or camera saves it, also several files per match or a download link from Veo. The analysis finds the court by itself and also follows a camera that pans; whether it is right, you confirm with one tap. When you upload, the app reminds you of the key points." },
    related: ["spiel-auswerten-20-minuten", "video-im-verein-einwilligung", "wege-zur-videoanalyse"],
  },
  {
    slug: "videoanalyse-amateurteam",
    group: "auswerten",
    published: "2026-11-13",
    updated: "2026-11-16",
    locales: ["de", "fr", "en"],
    title: {
      de: "Was bringt Videoanalyse einem Amateurteam?",
      fr: "Qu'apporte l'analyse vidéo à une équipe amateur ?",
      en: "What does video analysis give an amateur team?",
    },
    metaTitle: { de: "Videoanalyse im Amateurhandball", fr: "L'analyse vidéo en handball amateur", en: "Video analysis for amateur handball teams" },
    answer: {
      de: "Sie zeigt dir, was im Spiel wirklich passiert ist, und deinem Team Szenen statt Worte. Sie ersetzt weder das Training noch dein Auge, und sie kostet Zeit. Am meisten bringt sie mit einer Frage pro Spiel und wenigen Szenen.",
      fr: "Elle te montre ce qui s'est vraiment passé pendant le match, et à ton équipe des séquences plutôt que des mots. Elle ne remplace ni l'entraînement ni ton œil, et elle prend du temps. Elle apporte le plus avec une question par match et peu de séquences.",
      en: "It shows you what really happened in the match, and shows your team scenes instead of words. It replaces neither training nor your eye, and it takes time. It helps most with one question per match and a few scenes.",
    },
    description: {
      de: "Was Videoanalyse einem Amateur-Handballteam wirklich bringt, was nicht, wie viel Zeit sie kostet und wie du klein anfängst.",
      fr: "Ce que l'analyse vidéo apporte vraiment à une équipe de handball amateur, ce qu'elle n'apporte pas, combien de temps elle prend et comment commencer.",
      en: "What video analysis really gives an amateur handball team, what it does not, how much time it takes and how to start small.",
    },
    product: { de: "Handball Intelligence nimmt dir das Suchen und Schneiden ab: Die Analyse schlägt die Tore vor, du bestätigst sie und hast jedes Tor als Szene. Bei genug Toren zeigt sie drei Dinge zum Mitnehmen, über die Saison, was sich wiederholt. Was das Team sehen soll, schickst du als Sammlung per Link in den Teamchat, ohne Konto für die Spieler.", fr: "Handball Intelligence t'épargne la recherche et le montage : l'analyse propose les buts, tu les confirmes et tu as chaque but en séquence. Avec assez de buts, elle montre trois choses à retenir, et sur la saison ce qui se répète. Ce que l'équipe doit voir, tu l'envoies en sélection par lien dans le chat de l'équipe, sans compte pour les joueurs.", en: "Handball Intelligence takes the searching and cutting off your hands: the analysis suggests the goals, you confirm them and have every goal as a scene. With enough goals it shows three things to take away, and over the season what repeats. What the team should see, you send as a collection by link to the team chat, with no account for the players." },
    related: ["spiel-auswerten-20-minuten", "szenen-im-training-zeigen", "wege-zur-videoanalyse"],
  },
  {
    slug: "spiel-auswerten-20-minuten",
    group: "auswerten",
    published: "2026-11-13",
    updated: "2026-11-16",
    locales: ["de", "fr"],
    title: { de: "Wie werte ich ein Spiel in 20 Minuten aus?", fr: "Comment analyser un match en 20 minutes ?" },
    metaTitle: { de: "Handballspiel in 20 Minuten auswerten", fr: "Analyser un match en 20 minutes" },
    answer: {
      de: "Schau nicht das ganze Spiel noch einmal. Nimm dir eine Frage vor, spring zu den Toren und Gegentoren und mach zu jeder Szene einen Strich. Nach 20 Minuten hast du ein Muster und drei Szenen für das Team.",
      fr: "Ne revois pas tout le match. Prends une question, saute aux buts marqués et encaissés et fais un bâton pour chaque séquence. Après 20 minutes, tu as une tendance et trois séquences pour l'équipe.",
    },
    description: { de: "Eine Frage, der Spielverlauf, die Gegentore, eine Strichliste und drei Szenen: so wertest du ein Handballspiel in 20 Minuten aus. Mit Vorlage.", fr: "Une question, l'évolution du score, les buts encaissés, une feuille de pointage et trois séquences : analyser un match de handball en 20 minutes." },
    product: { de: "Mit Handball Intelligence fällt das Spulen weg: Nach dem Prüfen springst du mit einem Tipp zu jedem Tor. Die Strichliste nach Position führt die App für dich, aus dem Wurfort, den du pro Tor antippst, und die drei Szenen fürs Team legst du in eine Sammlung und schickst den Link.", fr: "Avec Handball Intelligence, plus besoin de rembobiner : après la vérification, tu sautes d'une touche à chaque but. La feuille de pointage par poste, l'app la tient pour toi, à partir du lieu de tir que tu indiques pour chaque but, et les trois séquences pour l'équipe vont dans une sélection dont tu envoies le lien." },
    related: ["gegentore-nach-position", "gegenstoss-und-ballverluste", "szenen-im-training-zeigen"],
  },
  {
    slug: "gegentore-nach-position",
    group: "auswerten",
    published: "2026-11-13",
    updated: "2026-11-16",
    locales: ["de", "fr"],
    title: { de: "Wie lese ich Gegentore nach Position?", fr: "Comment lire les buts encaissés par poste ?" },
    metaTitle: { de: "Gegentore nach Position lesen", fr: "Buts encaissés par poste" },
    answer: {
      de: "Zähl die Gegentore danach, von wo geworfen wurde: Aussen, Rückraum links, Mitte, rechts, Kreis, Siebenmeter, Gegenstoss. Eine Häufung zeigt dir, wo du zuerst hinschaust. Ob es an der Abwehr, am Torhüter oder an Ballverlusten liegt, sagt dir erst die Szene.",
      fr: "Compte les buts encaissés selon l'endroit d'où le tir est parti : ailes, arrière gauche, demi-centre, arrière droit, pivot, jet de 7 mètres, contre-attaque. Une accumulation te montre où regarder en premier. Si c'est la défense, le gardien ou les pertes de balle, seule la séquence te le dit.",
    },
    description: { de: "Gegentore nach Wurfposition zählen, Häufungen richtig lesen und typische Ursachen erkennen: Rückraum, Aussen, Kreis, Siebenmeter, Gegenstoss.", fr: "Compter les buts encaissés selon la position du tir, bien lire les accumulations et reconnaître les causes : arrières, ailes, pivot, 7 mètres." },
    product: { de: "Handball Intelligence zählt die Gegentore nach Position für dich, aus dem Wurfort, den du beim Prüfen pro Tor antippst. Zu jeder Häufung gibt es die Szenen mit einem Tipp, und die Saison zeigt, ob sie in mehreren Spielen auftaucht.", fr: "Handball Intelligence compte les buts encaissés par poste pour toi, à partir du lieu de tir que tu indiques pour chaque but à la vérification. Chaque accumulation a ses séquences à une touche, et la saison montre si elle revient sur plusieurs matchs." },
    related: ["spiel-auswerten-20-minuten", "wurfquote-torhueterquote", "handball-begriffe"],
  },
  {
    slug: "gegenstoss-und-ballverluste",
    group: "auswerten",
    published: "2026-11-13",
    updated: "2026-11-16",
    locales: ["de", "fr"],
    title: { de: "Wie werte ich Gegenstösse und Ballverluste aus?", fr: "Comment analyser contre-attaques et pertes de balle ?" },
    metaTitle: { de: "Gegenstösse und Ballverluste auswerten", fr: "Contre-attaques et pertes de balle" },
    answer: {
      de: "Zähl, wie viele Tore beide Teams nach Gegenstoss werfen, und schau dir die Ballverluste davor an. Meist liegt die Ursache nicht im Rückzug, sondern ein paar Sekunden vorher: ein Fehlpass, ein Schrittfehler, ein überhasteter Wurf.",
      fr: "Compte combien de buts les deux équipes marquent sur contre-attaque, et regarde les pertes de balle juste avant. Le plus souvent, la cause n'est pas dans le repli, mais quelques secondes plus tôt : une mauvaise passe, un marcher, un tir précipité.",
    },
    description: { de: "Gegenstoss, zweite Welle, Ballverlust: was du zählst, wo du im Video hinschaust und was daraus fürs Training folgt.", fr: "Contre-attaque, deuxième vague, perte de balle : ce que tu comptes, où regarder dans la vidéo et ce que ça donne pour l'entraînement." },
    product: { de: "Handball Intelligence zeigt Gegentore nach Gegenstoss als eigenes Ding, mit den Szenen dazu. Ballverluste kommen aus dem Spielbericht, oder du markierst sie im Video; von jeder Szene aus spulst du ein paar Sekunden zurück und siehst, was davor passiert ist.", fr: "Handball Intelligence montre les buts encaissés sur contre-attaque comme un point à part, avec les séquences. Les pertes de balle viennent de la feuille de match, ou tu les marques dans la vidéo ; depuis chaque séquence, tu reviens quelques secondes en arrière pour voir ce qui s'est passé avant." },
    related: ["spiel-auswerten-20-minuten", "gegentore-nach-position", "szenen-im-training-zeigen"],
  },
  {
    slug: "wurfquote-torhueterquote",
    group: "auswerten",
    published: "2026-11-13",
    updated: "2026-11-16",
    locales: ["de", "fr"],
    title: { de: "Wie rechne ich Wurfquote und Torhüterquote?", fr: "Comment calculer le pourcentage au tir et le pourcentage d'arrêts ?" },
    metaTitle: { de: "Wurfquote und Torhüterquote berechnen", fr: "Pourcentage au tir et d'arrêts" },
    answer: {
      de: "Wurfquote: Tore geteilt durch Würfe, mal 100. Torhüterquote: Paraden geteilt durch Paraden plus Gegentore, mal 100. Schreib immer die Basis dazu, zum Beispiel «12 von 20, 60 %», und zähl jedes Mal gleich.",
      fr: "Pourcentage de réussite au tir : buts divisés par tirs, fois 100. Pourcentage d'arrêts du gardien : arrêts divisés par arrêts plus buts encaissés, fois 100. Écris toujours la base, par exemple « 12 sur 20, 60 % », et compte chaque fois de la même façon.",
    },
    description: { de: "Wurfquote und Torhüterquote im Handball richtig berechnen: Formeln, was als Wurf zählt, eine Tabelle zum Übernehmen und fünf Regeln für ehrliche Zahlen.", fr: "Pourcentage de réussite au tir et d'arrêts au handball : les formules, ce qui compte comme tir, un tableau et cinq règles pour des chiffres honnêtes." },
    product: { de: "Handball Intelligence rechnet die Quoten mit ihrer Basis und schreibt bei jeder Zahl dazu, woher sie kommt. Tore kommen aus dem Prüfen oder dem Spielbericht; Würfe und Paraden markierst du im Video, wenn du die Quoten willst.", fr: "Handball Intelligence calcule les pourcentages avec leur base et indique pour chaque chiffre d'où il vient. Les buts viennent de la vérification ou de la feuille de match ; les tirs et les arrêts, tu les marques dans la vidéo si tu veux les pourcentages." },
    related: ["gegentore-nach-position", "handball-begriffe", "spiel-auswerten-20-minuten"],
  },
  {
    slug: "szenen-im-training-zeigen",
    group: "training",
    published: "2026-11-13",
    updated: "2026-11-16",
    locales: ["de", "fr"],
    title: { de: "Wie zeige ich Szenen, ohne das halbe Training zu verlieren?", fr: "Comment montrer des séquences sans perdre la moitié de l'entraînement ?" },
    metaTitle: { de: "Videositzung: Szenen im Training zeigen", fr: "Séance vidéo à l'entraînement" },
    answer: {
      de: "Zeig höchstens fünf Szenen zu einem Thema, in zehn Minuten. Beginne mit einer guten Szene, sag vorher, worauf alle schauen sollen, und geh danach gleich in die Übung dazu.",
      fr: "Montre au plus cinq séquences sur un thème, en dix minutes. Commence par une bonne séquence, dis avant à quoi tout le monde doit faire attention, et passe ensuite tout de suite à l'exercice qui va avec.",
    },
    description: { de: "Eine Videositzung in zehn Minuten: ein Thema, drei bis fünf Szenen, wie du darüber sprichst und was bei Kindern und Jugendlichen gilt.", fr: "Une séance vidéo en dix minutes : un thème, trois à cinq séquences, comment en parler et ce qui vaut avec des enfants et des jeunes." },
    product: { de: "In Handball Intelligence legst du die Szenen mit einem Tipp in eine Sammlung, schreibst eine Notiz dazu und zeigst sie am Bildschirm oder Beamer, Szene für Szene. Für zu Hause schickst du denselben Link in den Teamchat, ohne Konto für die Spieler.", fr: "Dans Handball Intelligence, tu mets les séquences d'une touche dans une sélection, tu ajoutes une note et tu les montres à l'écran ou au projecteur, séquence après séquence. Pour la maison, tu envoies le même lien dans le chat de l'équipe, sans compte pour les joueurs." },
    related: ["spiel-auswerten-20-minuten", "videoanalyse-amateurteam", "video-im-verein-einwilligung"],
  },
  {
    slug: "video-im-verein-einwilligung",
    group: "verein",
    published: "2026-11-13",
    updated: "2026-11-16",
    locales: ["de", "fr", "en"],
    title: {
      de: "Was gilt beim Filmen im Verein: Einwilligung, Kinder, Aufbewahrung?",
      fr: "Filmer au club : consentement, enfants, conservation, que faut-il savoir ?",
      en: "Filming in a club: consent, children, retention. What applies?",
    },
    metaTitle: { de: "Video im Verein: Einwilligung und Kinder", fr: "Vidéo au club : consentement et enfants", en: "Club video: consent and children" },
    answer: {
      de: "In der Schweiz hat jede Person ein Recht am eigenen Bild, und wer im Video erkennbar ist, dessen Personendaten bearbeitest du. Für die Analyse im Team heisst das: vorher informieren, für einen klaren Zweck filmen, nur dem Team zeigen, um Einwilligung fragen und löschen, wenn das Video nicht mehr gebraucht wird. Für Kinder entscheiden die Eltern; das Gesetz kennt keine feste Altersgrenze, es kommt auf die Urteilsfähigkeit an.",
      fr: "En Suisse, chaque personne a un droit à sa propre image, et quiconque est reconnaissable dans la vidéo voit ses données personnelles traitées. Pour l'analyse en équipe, cela veut dire : informer avant, filmer dans un but précis, ne montrer qu'à l'équipe, demander le consentement et effacer quand la vidéo ne sert plus. Pour les enfants, ce sont les parents qui décident ; la loi ne fixe pas d'âge, tout dépend de la capacité de discernement.",
      en: "In Switzerland everyone has a right to their own image, and anyone recognisable in a video is personal data. For team analysis that means: inform beforehand, film for a clear purpose, show it only to the team, ask for consent and delete the video when it is no longer needed. For children, the parents decide; the law has no fixed age, it depends on capacity of judgement.",
    },
    description: {
      de: "Spiele filmen im Verein: was in der Schweiz gilt (EDÖB, Swiss Olympic), Einwilligung von Kindern und Jugendlichen, Aufbewahrung und ein Mustertext.",
      fr: "Filmer les matchs au club : ce qui vaut en Suisse (PFPDT, Swiss Olympic), consentement des enfants et des jeunes, conservation, et un modèle de texte.",
      en: "Filming matches in a club: what applies in Switzerland (FDPIC, Swiss Olympic), consent of children and young people, retention, and a sample text.",
    },
    product: { de: "Handball Intelligence fragt die Einwilligung per Link im Teamchat ab, für jeden Zweck einzeln und ohne Konto; bis 16 entscheiden die Eltern. Wer nein sagt, erscheint nicht in Highlights, und geteilte Links zeigen Rückennummern statt Namen. Das Originalvideo wird nach 90 Tagen gelöscht.", fr: "Handball Intelligence demande le consentement par lien dans le chat de l'équipe, pour chaque usage séparément et sans compte ; jusqu'à 16 ans, les parents décident. Qui dit non n'apparaît pas dans les highlights, et les liens partagés montrent les numéros au lieu des noms. La vidéo originale est supprimée après 90 jours.", en: "Handball Intelligence asks for consent by link in the team chat, for each purpose separately and without an account; up to 16, the parents decide. Whoever says no does not appear in highlights, and shared links show shirt numbers instead of names. The original video is deleted after 90 days." },
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
      fr: "Quatre solutions : revoir et découper la vidéo à la main, une caméra automatique, un logiciel pour marquer les séquences et une analyse automatique comme Handball Intelligence. Le bon choix dépend de ton temps, de ton budget et de ta salle.",
    },
    description: { de: "Von Hand schneiden, automatische Kamera, Analyse-Software oder automatische Analyse: die Wege zur Videoanalyse im Handball ehrlich verglichen.", fr: "À la main, caméra automatique, logiciel d'analyse ou analyse automatique : les solutions d'analyse vidéo au handball, comparées honnêtement." },
    related: ["videoanalyse-amateurteam", "handballspiel-filmen", "spiel-auswerten-20-minuten"],
  },
];
