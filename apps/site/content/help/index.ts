/** Help centre index (addendum 01, 4.13). Slugs match apps/web/src/components/support/help-map.ts. */
export type HelpLocale = "de" | "fr" | "en";

export interface HelpEntry {
  slug: string;
  group: "start" | "video" | "team" | "work" | "account";
  /** false: a guide to a function outside the core (SPEC 1); reachable for the app's links, not listed */
  listed?: boolean;
  title: Record<HelpLocale, string>;
  summary: Record<HelpLocale, string>;
  keywords: Record<HelpLocale, string>;
}

export const HELP: HelpEntry[] = [
  {
    slug: "erste-schritte",
    group: "start",
    title: { de: "Erste Schritte", fr: "Premiers pas", en: "Getting started" },
    summary: {
      de: "Vom Konto bis zu den ersten drei Dingen.",
      fr: "Du compte aux trois premiers points.",
      en: "From your account to your first three things.",
    },
    keywords: { de: "start konto team anmelden demo", fr: "début compte équipe inscription démo", en: "start account team sign up demo" },
  },
  {
    slug: "aufnahme",
    group: "start",
    title: { de: "Spiel richtig filmen", fr: "Bien filmer un match", en: "Filming a match" },
    summary: {
      de: "Wo das Handy steht, wie hoch, welche Einstellungen.",
      fr: "Où placer le téléphone, à quelle hauteur, quels réglages.",
      en: "Where the phone goes, how high, which settings.",
    },
    keywords: { de: "kamera handy stativ aufnahme filmen mittellinie", fr: "caméra téléphone trépied enregistrement filmer ligne médiane", en: "camera phone tripod recording filming halfway line" },
  },
  {
    slug: "video-hochladen",
    group: "start",
    title: { de: "Video hochladen", fr: "Téléverser une vidéo", en: "Uploading a video" },
    summary: {
      de: "Welche Datei, abgebrochene Uploads, Spielbericht, Speicherdauer.",
      fr: "Quel fichier, envois interrompus, feuille de match, conservation.",
      en: "Which file, interrupted uploads, match report, retention.",
    },
    keywords: { de: "upload datei mp4 mov link wlan spielbericht", fr: "upload fichier mp4 mov lien wifi feuille de match", en: "upload file mp4 mov link wifi match report" },
  },
  {
    slug: "analyse-lesen",
    group: "video",
    title: { de: "Analyse lesen", fr: "Lire l'analyse", en: "Reading the analysis" },
    summary: {
      de: "Drei Dinge, Taktikkamera, Zahlen und woher sie kommen.",
      fr: "Trois points, caméra tactique, chiffres et leur source.",
      en: "Three things, tactics camera, figures and where they come from.",
    },
    keywords: { de: "drei dinge taktikkamera zahlen quelle geschätzt", fr: "trois points caméra tactique chiffres source estimé", en: "three things tactics camera figures source estimated" },
  },
  {
    slug: "highlights",
    group: "work",
    title: { de: "Highlights", fr: "Temps forts", en: "Highlights" },
    summary: {
      de: "Automatische Highlights, quer und hoch, mit Einwilligung.",
      fr: "Temps forts automatiques, en paysage et portrait, avec consentement.",
      en: "Automatic highlights, landscape and portrait, with consent.",
    },
    keywords: { de: "highlights reel social media", fr: "temps forts réseaux sociaux", en: "reel social media clips" },
  },
  {
    slug: "kader",
    group: "team",
    title: { de: "Team und Kader", fr: "Équipe et effectif", en: "Team and squad" },
    summary: {
      de: "Kader vom Verband, was fehlt, wer ist wer im Video, Trainerbank.",
      fr: "Effectif de la fédération, ce qui manque, qui est qui dans la vidéo, staff.",
      en: "Squad from the federation, what is missing, who is who in the video, coaching staff.",
    },
    keywords: { de: "kader nummer spieler trainerbank einladen", fr: "effectif numéro joueurs staff inviter", en: "squad number players staff invite" },
  },
  {
    slug: "rollen-und-rechte",
    group: "team",
    listed: false,
    title: { de: "Rollen und Rechte", fr: "Rôles et droits", en: "Roles and permissions" },
    summary: {
      de: "Wer was sieht und darf, vom Admin bis zum Elternteil.",
      fr: "Qui voit et fait quoi, de l'admin au parent.",
      en: "Who sees and does what, from admin to parent.",
    },
    keywords: { de: "rolle admin trainer eltern einladen", fr: "rôle admin entraîneur parents inviter", en: "role admin coach parent invite" },
  },
  {
    slug: "einwilligungen",
    group: "team",
    title: { de: "Einwilligungen", fr: "Consentements", en: "Consents" },
    summary: {
      de: "Ein Link im Teamchat, ohne Konto. Kinder: die Eltern.",
      fr: "Un lien dans le chat d'équipe, sans compte. Enfants : les parents.",
      en: "One link in the team chat, no account. Children: the parents.",
    },
    keywords: { de: "einwilligung datenschutz kinder eltern", fr: "consentement protection enfants parents", en: "consent privacy children parents" },
  },
  {
    slug: "tags-und-filter",
    group: "work",
    title: { de: "Szenen suchen", fr: "Chercher des scènes", en: "Searching scenes" },
    summary: {
      de: "Suchen über alle Spiele, die Antwort mit Basis, Sammlungen.",
      fr: "Chercher dans tous les matchs, la réponse avec sa base, sélections.",
      en: "Search across all matches, the answer with its base, collections.",
    },
    keywords: { de: "szenen suchen filter sammlung", fr: "scènes chercher filtre sélection", en: "scenes search filter collection" },
  },
  {
    slug: "praesentation",
    group: "work",
    listed: false,
    title: { de: "Präsentation für die Videositzung", fr: "Présentation pour la séance vidéo", en: "Presentation for the video session" },
    summary: {
      de: "Clips, Zeichnungen, Handy als Fernbedienung, Export.",
      fr: "Clips, dessins, téléphone comme télécommande, export.",
      en: "Clips, drawings, phone as remote, export.",
    },
    keywords: { de: "präsentation videositzung zeichnen export", fr: "présentation séance dessin export", en: "presentation session drawing export" },
  },
  {
    slug: "deine-szenen",
    group: "work",
    listed: false,
    title: { de: "Meine Szenen", fr: "Mes scènes", en: "My scenes" },
    summary: {
      de: "Was Spielerinnen und Spieler sehen und wie sie kommentieren.",
      fr: "Ce que voient les joueurs et comment ils commentent.",
      en: "What players see and how they comment.",
    },
    keywords: { de: "spieler feed kommentar aufgabe", fr: "joueur fil commentaire tâche", en: "player feed comment task" },
  },
  {
    slug: "vorbereitungsbericht",
    group: "work",
    listed: false,
    title: { de: "Vorbereitungsbericht", fr: "Rapport de préparation", en: "Scouting report" },
    summary: {
      de: "Was die Daten über den nächsten Gegner sagen.",
      fr: "Ce que les données disent du prochain adversaire.",
      en: "What the data says about the next opponent.",
    },
    keywords: { de: "gegner scouting bericht pdf", fr: "adversaire scouting rapport pdf", en: "opponent scouting report pdf" },
  },
  {
    slug: "taktiktafel",
    group: "work",
    listed: false,
    title: { de: "Taktiktafel", fr: "Tableau tactique", en: "Tactics board" },
    summary: {
      de: "Spielzüge in Phasen zeichnen und animieren.",
      fr: "Dessiner et animer des combinaisons en phases.",
      en: "Drawing and animating plays in phases.",
    },
    keywords: { de: "taktik spielzug abwehr", fr: "tactique combinaison défense", en: "tactics play defence" },
  },
  {
    slug: "live-erfassung",
    group: "video",
    title: { de: "Spieltag", fr: "Jour de match", en: "Matchday" },
    summary: {
      de: "Am Spielfeldrand tippen, wenn es keinen Spielbericht gibt. Auch ohne Netz.",
      fr: "Saisir au bord du terrain sans feuille de match. Même hors ligne.",
      en: "Tap courtside when there is no match report. Works offline.",
    },
    keywords: { de: "spieltag live tor offline", fr: "jour de match direct but hors ligne", en: "matchday live goal offline" },
  },
  {
    slug: "frag-deine-daten",
    group: "work",
    listed: false,
    title: { de: "Frag deine Daten", fr: "Interroge tes données", en: "Ask your data" },
    summary: {
      de: "Fragen in normaler Sprache, Antworten nur aus euren Daten.",
      fr: "Des questions en langage courant, des réponses tirées uniquement de tes données.",
      en: "Questions in plain language, answers only from your data.",
    },
    keywords: { de: "assistent frage chat ki", fr: "assistant question chat ia", en: "assistant question chat ai" },
  },
  {
    slug: "statistik-matrix",
    group: "video",
    listed: false,
    title: { de: "Statistik-Matrix und Export", fr: "Matrice statistique et export", en: "Statistics matrix and export" },
    summary: {
      de: "Eigene Auswertungen, Excel, CSV und Sportscode-XML.",
      fr: "Analyses personnalisées, Excel, CSV et XML Sportscode.",
      en: "Own reports, Excel, CSV and Sportscode XML.",
    },
    keywords: { de: "matrix excel csv sportscode export import", fr: "matrice excel csv sportscode export import", en: "matrix excel csv sportscode export import" },
  },
  {
    slug: "training-planen",
    group: "team",
    listed: false,
    title: { de: "Training planen", fr: "Planifier l'entraînement", en: "Planning training" },
    summary: {
      de: "Einheiten, Anwesenheit, Kalender und Schwerpunkte aus Spielen.",
      fr: "Séances, présences, calendrier et objectifs tirés des matchs.",
      en: "Sessions, attendance, calendar and focus from matches.",
    },
    keywords: { de: "training einheit anwesenheit kalender ics übung", fr: "entraînement séance présence calendrier ics exercice", en: "training session attendance calendar ics drill" },
  },
  {
    slug: "abo-und-rechnung",
    group: "account",
    title: { de: "Abo und Rechnung", fr: "Abonnement et facture", en: "Subscription and invoice" },
    summary: {
      de: "Pläne, 30 Tage gratis, QR-Rechnung, Kündigen.",
      fr: "Formules, 30 jours gratuits, facture QR, résiliation.",
      en: "Plans, 30 days free, QR bill, cancelling.",
    },
    keywords: { de: "preis abo rechnung gutschein kündigen", fr: "prix abonnement facture bon résilier", en: "price subscription invoice voucher cancel" },
  },
  {
    slug: "datenschutz-und-loeschen",
    group: "account",
    title: { de: "Datenschutz und Löschen", fr: "Protection des données et suppression", en: "Privacy and deletion" },
    summary: {
      de: "Wo die Daten liegen, wer was sieht, herunterladen und löschen.",
      fr: "Où sont les données, qui voit quoi, télécharger et supprimer.",
      en: "Where data lives, who sees what, download and delete.",
    },
    keywords: { de: "datenschutz löschen export dsg", fr: "protection supprimer export lpd", en: "privacy delete export gdpr" },
  },
];
