/** Help centre index (addendum 01, 4.13). Slugs match apps/web/src/components/support/help-map.ts. */
export type HelpLocale = "de" | "fr" | "en";

export interface HelpEntry {
  slug: string;
  group: "start" | "video" | "team" | "work" | "account";
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
      de: "In fünf Schritten von der Anmeldung zur ersten Analyse.",
      fr: "De l'inscription à la première analyse en cinq étapes.",
      en: "From sign-up to your first analysis in five steps.",
    },
    keywords: { de: "start anmelden verein team", fr: "début inscription club équipe", en: "start sign up club team" },
  },
  {
    slug: "aufnahme",
    group: "video",
    title: { de: "Spiel richtig filmen", fr: "Bien filmer un match", en: "Filming a match" },
    summary: {
      de: "Kamera, Position und Einstellungen für eine gute Analyse.",
      fr: "Caméra, position et réglages pour une bonne analyse.",
      en: "Camera, position and settings for a good analysis.",
    },
    keywords: { de: "kamera handy stativ aufnahme filmen", fr: "caméra téléphone trépied enregistrement", en: "camera phone tripod recording" },
  },
  {
    slug: "video-hochladen",
    group: "video",
    title: { de: "Video hochladen", fr: "Téléverser une vidéo", en: "Uploading a video" },
    summary: {
      de: "Upload, Kamera-Rollen, Import per Link und Speicherdauer.",
      fr: "Téléversement, rôles de caméra, import par lien et durée de conservation.",
      en: "Upload, camera roles, import by link and retention.",
    },
    keywords: { de: "upload datei link wlan", fr: "upload fichier lien wifi", en: "upload file link wifi" },
  },
  {
    slug: "analyse-lesen",
    group: "video",
    title: { de: "Analyse lesen", fr: "Lire l'analyse", en: "Reading the analysis" },
    summary: {
      de: "Ereignisse, Kennzahlen, xG und Erkenntnisse verstehen.",
      fr: "Comprendre les événements, les chiffres clés, les xG et les constats.",
      en: "Understanding events, key figures, xG and insights.",
    },
    keywords: { de: "statistik xg wurfquote ereignisse", fr: "statistiques xg tirs événements", en: "statistics xg shooting events" },
  },
  {
    slug: "highlights",
    group: "video",
    title: { de: "Highlights", fr: "Temps forts", en: "Highlights" },
    summary: {
      de: "Automatische Highlight-Videos für Team und Spieler.",
      fr: "Vidéos de temps forts automatiques pour l'équipe et les joueurs.",
      en: "Automatic highlight videos for team and players.",
    },
    keywords: { de: "highlights reel social media", fr: "temps forts réseaux sociaux", en: "reel social media clips" },
  },
  {
    slug: "kader",
    group: "team",
    title: { de: "Kader verwalten", fr: "Gérer l'effectif", en: "Managing the roster" },
    summary: {
      de: "Spieler erfassen, CSV-Import, Nummern und Zuordnung im Video.",
      fr: "Saisir les joueurs, import CSV, numéros et attribution dans la vidéo.",
      en: "Adding players, CSV import, numbers and matching in video.",
    },
    keywords: { de: "kader spieler csv nummer", fr: "effectif joueurs csv numéro", en: "roster players csv number" },
  },
  {
    slug: "rollen-und-rechte",
    group: "team",
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
      de: "Zwecke, Widerruf und Einwilligungen für Minderjährige.",
      fr: "Finalités, révocation et consentements pour les mineurs.",
      en: "Purposes, withdrawal and consent for minors.",
    },
    keywords: { de: "einwilligung datenschutz kinder eltern", fr: "consentement protection enfants parents", en: "consent privacy children parents" },
  },
  {
    slug: "tags-und-filter",
    group: "work",
    title: { de: "Szenen suchen und taggen", fr: "Chercher et taguer des scènes", en: "Searching and tagging scenes" },
    summary: {
      de: "Filter über alle Spiele, eigene Tags und Playlists.",
      fr: "Filtres sur tous les matchs, tags personnels et playlists.",
      en: "Filters across all matches, own tags and playlists.",
    },
    keywords: { de: "suche filter tag playlist clip", fr: "recherche filtre tag playlist clip", en: "search filter tag playlist clip" },
  },
  {
    slug: "praesentation",
    group: "work",
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
    group: "work",
    title: { de: "Live-Erfassung", fr: "Saisie en direct", en: "Live tagging" },
    summary: {
      de: "Ereignisse am Spielfeldrand erfassen, auch ohne Netz.",
      fr: "Saisir les événements au bord du terrain, même hors ligne.",
      en: "Tagging events courtside, even offline.",
    },
    keywords: { de: "live offline handy tablet", fr: "direct hors ligne téléphone tablette", en: "live offline phone tablet" },
  },
  {
    slug: "frag-deine-daten",
    group: "work",
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
    group: "work",
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
      de: "Pläne, Testphase, QR-Rechnung, Gutscheine und Kündigung.",
      fr: "Formules, essai, QR-facture, bons et résiliation.",
      en: "Plans, trial, QR-bill, vouchers and cancellation.",
    },
    keywords: { de: "preis abo rechnung gutschein kündigen", fr: "prix abonnement facture bon résilier", en: "price subscription invoice voucher cancel" },
  },
  {
    slug: "datenschutz-und-loeschen",
    group: "account",
    title: { de: "Datenschutz und Löschen", fr: "Protection des données et suppression", en: "Privacy and deletion" },
    summary: {
      de: "Daten herunterladen, Konto oder Verein löschen, Speicherdauer.",
      fr: "Télécharger ses données, supprimer le compte ou le club, durée de conservation.",
      en: "Download your data, delete account or club, retention.",
    },
    keywords: { de: "datenschutz löschen export dsg", fr: "protection supprimer export lpd", en: "privacy delete export gdpr" },
  },
];
