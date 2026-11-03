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
}


def render(template: str, locale: str, to: str, **values: object) -> Email:
    texts = _T[template]
    subject, body = texts.get(locale, texts["de-CH"])
    return Email(to=to, subject=subject.format(**values), text=body.format(**values))
