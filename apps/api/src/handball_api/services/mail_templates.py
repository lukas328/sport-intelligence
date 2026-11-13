"""Transactional e-mail texts (de-CH, en, fr). No long dashes, de-CH uses "ss"."""

from __future__ import annotations

from handball_api.core.email import Email

_T: dict[str, dict[str, tuple[str, str]]] = {
    "password_reset": {
        "de-CH": (
            "Passwort zurücksetzen",
            "Hallo {name}\n\nMit diesem Link setzt du ein neues Passwort. Er ist {minutes} Minuten "
            "gültig und funktioniert nur einmal:\n\n{link}\n\nFalls du das nicht angefordert hast, "
            "kannst du diese E-Mail ignorieren. Dein Passwort bleibt dann unverändert.",
        ),
        "en": (
            "Reset your password",
            "Hello {name}\n\nUse this link to set a new password. It is valid for {minutes} minutes "
            "and works once:\n\n{link}\n\nIf you did not request it, ignore this e-mail. Your "
            "password stays unchanged.",
        ),
        "fr": (
            "Réinitialiser votre mot de passe",
            "Bonjour {name}\n\nCe lien vous permet de définir un nouveau mot de passe. Il est valable "
            "{minutes} minutes et ne fonctionne qu'une fois :\n\n{link}\n\nSi vous ne l'avez pas "
            "demandé, ignorez cet e-mail. Votre mot de passe reste inchangé.",
        ),
    },
    "email_verify": {
        "de-CH": (
            "Bitte bestätige deine E-Mail-Adresse",
            "Hallo {name}\n\nBitte bestätige deine E-Mail-Adresse mit diesem Link:\n\n{link}\n\n"
            "Der Link ist {hours} Stunden gültig.",
        ),
        "en": (
            "Please confirm your e-mail address",
            "Hello {name}\n\nPlease confirm your e-mail address with this link:\n\n{link}\n\n"
            "The link is valid for {hours} hours.",
        ),
        "fr": (
            "Veuillez confirmer votre adresse e-mail",
            "Bonjour {name}\n\nVeuillez confirmer votre adresse e-mail avec ce lien :\n\n{link}\n\n"
            "Le lien est valable {hours} heures.",
        ),
    },
    "assignment": {
        "de-CH": (
            "Neue Aufgabe: {title}",
            "Hallo {name}\n\n{coach} hat dir eine Aufgabe im Team {team} gegeben: {title}.{due}\n\n"
            "Zur Aufgabe: {link}",
        ),
        "en": (
            "New assignment: {title}",
            "Hello {name}\n\n{coach} gave you an assignment in team {team}: {title}.{due}\n\n"
            "Open it: {link}",
        ),
        "fr": (
            "Nouvelle tâche : {title}",
            "Bonjour {name}\n\n{coach} t'a confié une tâche dans l'équipe {team} : {title}.{due}\n\n"
            "Ouvrir la tâche : {link}",
        ),
    },
    "analysis_ready": {
        "de-CH": (
            "Die drei Dinge gegen {opponent} sind da",
            "Hallo {name}\n\nDie Analyse des Spiels {team} gegen {opponent} ist fertig. Die drei "
            "Dinge und die Szenen warten:\n\n{link}",
        ),
        "en": (
            "The three things against {opponent} are ready",
            "Hello {name}\n\nThe analysis of {team} against {opponent} is done. The three things "
            "and the scenes are waiting:\n\n{link}",
        ),
        "fr": (
            "Les trois choses contre {opponent} sont prêtes",
            "Bonjour {name}\n\nL'analyse du match {team} contre {opponent} est terminée. Les "
            "trois choses et les scènes t'attendent :\n\n{link}",
        ),
    },
    # the analysis is done, but there are no three things yet (UX test N05): say what is there
    "analysis_questions": {
        "de-CH": (
            "Die Analyse gegen {opponent} ist fertig",
            "Hallo {name}\n\nDie Analyse des Spiels {team} gegen {opponent} ist fertig. "
            "{questions} Fragen an dich, dann zeigt sie mehr:\n\n{link}",
        ),
        "en": (
            "The analysis against {opponent} is done",
            "Hello {name}\n\nThe analysis of {team} against {opponent} is done. {questions} "
            "questions for you, then it shows more:\n\n{link}",
        ),
        "fr": (
            "L'analyse contre {opponent} est terminée",
            "Bonjour {name}\n\nL'analyse du match {team} contre {opponent} est terminée. "
            "{questions} questions pour toi, ensuite elle en montre plus :\n\n{link}",
        ),
    },
    "analysis_no_goals": {
        "de-CH": (
            "Die Analyse gegen {opponent} ist fertig",
            "Hallo {name}\n\nDie Analyse des Spiels {team} gegen {opponent} ist fertig. Sie hat "
            "im Video keine Tore gefunden. Das Video und die Szenen von Hand sind da:\n\n{link}",
        ),
        "en": (
            "The analysis against {opponent} is done",
            "Hello {name}\n\nThe analysis of {team} against {opponent} is done. It found no goals "
            "in the video. The video and the scenes by hand are there:\n\n{link}",
        ),
        "fr": (
            "L'analyse contre {opponent} est terminée",
            "Bonjour {name}\n\nL'analyse du match {team} contre {opponent} est terminée. Elle "
            "n'a trouvé aucun but dans la vidéo. La vidéo et les scènes à la main sont là :"
            "\n\n{link}",
        ),
    },
    "analysis_failed": {
        "de-CH": (
            "Das Video gegen {opponent} liess sich nicht auswerten",
            "Hallo {name}\n\nDie Analyse des Spiels {team} gegen {opponent} hat nicht geklappt. "
            "Das Video bleibt abspielbar, der Spielbericht und alles, was du erfasst hast, "
            "bleiben. Du kannst ein anderes Video hochladen oder einfach auf diese Mail "
            "antworten:\n\n{link}",
        ),
        "en": (
            "The video against {opponent} could not be analysed",
            "Hello {name}\n\nThe analysis of {team} against {opponent} did not work. The video "
            "stays playable; the match report and everything you entered stay. You can upload "
            "another video or simply reply to this e-mail:\n\n{link}",
        ),
        "fr": (
            "La vidéo contre {opponent} n'a pas pu être analysée",
            "Bonjour {name}\n\nL'analyse du match {team} contre {opponent} n'a pas fonctionné. "
            "La vidéo reste lisible, la feuille de match et tout ce que tu as saisi restent. Tu "
            "peux charger une autre vidéo ou simplement répondre à cet e-mail :\n\n{link}",
        ),
    },
    "video_failed": {
        "de-CH": (
            "Das Video gegen {opponent} liess sich nicht lesen",
            "Hallo {name}\n\nDie Datei zum Spiel {team} gegen {opponent} ist kein Video, das wir "
            "lesen können (MP4, MOV, MKV). Der Spielbericht bleibt. Wähl eine andere "
            "Datei:\n\n{link}",
        ),
        "en": (
            "The video against {opponent} could not be read",
            "Hello {name}\n\nThe file for {team} against {opponent} is not a video we can read "
            "(MP4, MOV, MKV). The match report stays. Choose another file:\n\n{link}",
        ),
        "fr": (
            "La vidéo contre {opponent} n'a pas pu être lue",
            "Bonjour {name}\n\nLe fichier du match {team} contre {opponent} n'est pas une vidéo "
            "lisible (MP4, MOV, MKV). La feuille de match reste. Choisis un autre "
            "fichier :\n\n{link}",
        ),
    },
    "magic_link": {
        "de-CH": (
            "Dein Anmeldelink",
            "Hallo {name}\n\nMit diesem Link meldest du dich an. Er ist {minutes} Minuten gültig "
            "und funktioniert nur einmal:\n\n{link}\n\nFalls du das nicht angefordert hast, "
            "kannst du diese E-Mail ignorieren.",
        ),
        "en": (
            "Your sign-in link",
            "Hello {name}\n\nUse this link to sign in. It is valid for {minutes} minutes and "
            "works once:\n\n{link}\n\nIf you did not request it, ignore this e-mail.",
        ),
        "fr": (
            "Votre lien de connexion",
            "Bonjour {name}\n\nUtilisez ce lien pour vous connecter. Il est valable {minutes} "
            "minutes et ne fonctionne qu'une fois :\n\n{link}\n\nSi vous ne l'avez pas demandé, "
            "ignorez cet e-mail.",
        ),
    },
    "invitation": {
        "de-CH": (
            "Einladung zu {org}",
            "Hallo\n\n{inviter} lädt dich zu {org}{team} ein.\n\nEinladung annehmen:\n{link}\n\n"
            "Der Link ist {days} Tage gültig.",
        ),
        "en": (
            "Invitation to {org}",
            "Hello\n\n{inviter} invited you to {org}{team}.\n\nAccept the invitation:\n{link}\n\n"
            "The link is valid for {days} days.",
        ),
        "fr": (
            "Invitation à {org}",
            "Bonjour\n\n{inviter} vous invite à rejoindre {org}{team}.\n\nAccepter l'invitation :\n"
            "{link}\n\nLe lien est valable {days} jours.",
        ),
    },
    "onboarding_0": {
        "de-CH": (
            "Willkommen bei Handball Intelligence",
            "Hallo {name}\n\nschön, dass du da bist. Der schnellste Weg zur ersten Analyse:\n1. Team anlegen und Spieler eintragen (CSV geht auch)\n2. Ein Spielvideo hochladen, Handy auf Stativ reicht\n3. Nach der Analyse: die drei Dinge, Würfe und deine Szenen ansehen\n\nOhne eigenes Video? Probier das Demo-Spiel aus:\n{link}\n\nKeine weiteren Tipps per E-Mail: {unsubscribe}",
        ),
        "en": (
            "Welcome to Handball Intelligence",
            "Hello {name}\n\ngreat to have you. The fastest way to your first analysis:\n1. Create a team and enter the players (CSV works too)\n2. Upload a match video, a phone on a tripod is enough\n3. After the analysis: the three things, shots and your scenes\n\nNo video yet? Try the demo match:\n{link}\n\nNo more tips by e-mail: {unsubscribe}",
        ),
        "fr": (
            "Bienvenue sur Handball Intelligence",
            "Bonjour {name}\n\nravi de vous accueillir. Le chemin le plus court vers la première analyse :\n1. Créer l'équipe et saisir les joueur·euse·s (CSV possible)\n2. Envoyer une vidéo de match, un téléphone sur trépied suffit\n3. Après l'analyse : les trois points, tirs et vos scènes\n\nPas encore de vidéo ? Essayez le match de démonstration :\n{link}\n\nPlus de conseils par e-mail : {unsubscribe}",
        ),
    },
    "onboarding_1": {
        "de-CH": (
            "So filmst du ein Spiel richtig",
            "Hallo {name}\n\nfür eine gute Analyse: Kamera erhöht (Tribüne oder Stativ ab 3 m), ganzes Spielfeld im Bild, quer filmen, nicht zoomen. Das Hallen-WLAN braucht es nicht, hochladen geht auch später.\n\nAnleitung mit Bildern:\n{link}\n\nKeine weiteren Tipps per E-Mail: {unsubscribe}",
        ),
        "en": (
            "How to film a match",
            "Hello {name}\n\nfor a good analysis: camera up high (stands or tripod from 3 m), the whole court in the picture, landscape, no zoom. You do not need the hall Wi-Fi, upload later.\n\nGuide with pictures:\n{link}\n\nNo more tips by e-mail: {unsubscribe}",
        ),
        "fr": (
            "Comment filmer un match",
            "Bonjour {name}\n\npour une bonne analyse : caméra en hauteur (tribune ou trépied dès 3 m), tout le terrain dans l'image, en paysage, sans zoom. Le Wi-Fi de la salle n'est pas nécessaire, l'envoi peut se faire plus tard.\n\nGuide illustré :\n{link}\n\nPlus de conseils par e-mail : {unsubscribe}",
        ),
    },
    "onboarding_3": {
        "de-CH": (
            "Die Videositzung in 5 Minuten",
            "Hallo {name}\n\nunter Szenen stellst du die Videositzung schnell zusammen: Szenen suchen, mit eigenen Tags versehen, in eine Sammlung legen und am Bildschirm zeigen, mit dem Handy weiterschalten.\n\nSo geht's:\n{link}\n\nKeine weiteren Tipps per E-Mail: {unsubscribe}",
        ),
        "en": (
            "The video session in 5 minutes",
            "Hello {name}\n\nunder Scenes you build the video session quickly: search scenes, add your own tags, put them in a collection and show it on screen, click through with your phone.\n\nHow it works:\n{link}\n\nNo more tips by e-mail: {unsubscribe}",
        ),
        "fr": (
            "La séance vidéo en 5 minutes",
            "Bonjour {name}\n\nsous Scènes, la séance vidéo est vite prête : chercher des scènes, ajouter vos tags, les mettre dans une sélection et la montrer à l'écran, avancer avec le téléphone.\n\nMode d'emploi :\n{link}\n\nPlus de conseils par e-mail : {unsubscribe}",
        ),
    },
    "onboarding_7": {
        "de-CH": (
            "Deine Spieler mitnehmen",
            "Hallo {name}\n\nlade dein Team ein: Spieler sehen nach jedem Spiel ihre wichtigsten Szenen und schätzen sich zuerst selbst ein. Eltern verwalten die Einwilligungen ihrer Kinder.\n\nTeam einladen:\n{link}\n\nKeine weiteren Tipps per E-Mail: {unsubscribe}",
        ),
        "en": (
            "Bring your players along",
            "Hello {name}\n\ninvite your team: after every match players see their most important scenes and rate themselves first. Parents manage their children's consents.\n\nInvite the team:\n{link}\n\nNo more tips by e-mail: {unsubscribe}",
        ),
        "fr": (
            "Embarquez vos joueur·euse·s",
            "Bonjour {name}\n\ninvitez votre équipe : après chaque match, les joueur·euse·s voient leurs scènes les plus importantes et s'évaluent d'abord. Les parents gèrent les consentements de leurs enfants.\n\nInviter l'équipe :\n{link}\n\nPlus de conseils par e-mail : {unsubscribe}",
        ),
    },
    "onboarding_14": {
        "de-CH": (
            "Wie läuft es?",
            "Hallo {name}\n\nzwei Wochen mit Handball Intelligence: Was hilft dir, was fehlt? Antworte einfach auf diese E-Mail oder nutze den Feedback-Knopf in der App. Wir lesen alles.\n\nZur App:\n{link}\n\nKeine weiteren Tipps per E-Mail: {unsubscribe}",
        ),
        "en": (
            "How is it going?",
            "Hello {name}\n\ntwo weeks with Handball Intelligence: what helps, what is missing? Just reply to this e-mail or use the feedback button in the app. We read everything.\n\nTo the app:\n{link}\n\nNo more tips by e-mail: {unsubscribe}",
        ),
        "fr": (
            "Comment ça se passe ?",
            "Bonjour {name}\n\ndeux semaines avec Handball Intelligence : qu'est-ce qui vous aide, qu'est-ce qui manque ? Répondez simplement à cet e-mail ou utilisez le bouton de feedback dans l'app. Nous lisons tout.\n\nVers l'app :\n{link}\n\nPlus de conseils par e-mail : {unsubscribe}",
        ),
    },
}


def render(template: str, locale: str, to: str, **values: object) -> Email:
    texts = _T[template]
    subject, body = texts.get(locale, texts["de-CH"])
    # an account from the entry has no name yet, only the part before the @: then just «Hallo»
    # (UX test N20)
    if values.get("name") and str(values["name"]) == to.split("@", 1)[0][:120]:
        values = {**values, "name": ""}
    text = body.format(**values)
    first, _, rest = text.partition("\n")
    return Email(to=to, subject=subject.format(**values), text=f"{first.rstrip()}\n{rest}")
