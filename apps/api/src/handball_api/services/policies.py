"""Role-based permissions (BRIEF 3), enforced server-side for every resource.

One table maps each action to the roles allowed to perform it. Org-level actions are checked
against the organisation role, team-level actions against the team role (org admins may do
everything a coach may do in every team of their organisation).

Four roles in the product (finding K18, decided 2026-11-16); the stored roles stay and map onto
them (`person_role`):

- **Trainer**: coach of a team and club admin (`coach` + `org_admin`). Everything.
- **Co-Trainer**: coach rights in the team without the club and the subscription. Stored as
  `coach`, `analyst`, `team_manager`, `goalkeeper_coach` or `athletic_coach` with the plain
  organisation role `member`; all five have the same rights in the team.
- **Spieler**: `player` and `goalkeeper` (the goalkeeper is a player with a position). They see
  everything of the team, mark scenes, build collections and share them by link, comment, check
  what the analysis asks and upload videos. They do not delete matches or videos, invite people,
  manage the squad, the team or the club.
- **Eltern**: `parent`, only their own children (guardianships).

`guest` gets no team access: guests see shared links only.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from handball_api.core.errors import ProblemError
from handball_api.models.enums import OrgRole, PersonRole, TeamRole


class Action(StrEnum):
    # organisation level
    ORG_READ = "org.read"
    ORG_UPDATE = "org.update"
    ORG_MEMBERS_READ = "org.members.read"
    TEAM_CREATE = "team.create"
    TEAM_DELETE = "team.delete"
    INVITE_ORG = "invite.org"
    AUDIT_READ = "audit.read"
    ORG_ACCESS_MANAGE = "org.access.manage"
    # team level
    TEAM_READ = "team.read"
    TEAM_UPDATE = "team.update"
    SEASON_WRITE = "season.write"
    ROSTER_READ = "roster.read"
    ROSTER_WRITE = "roster.write"
    PLAYER_STATUS = "player_status.manage"
    CONSENT_READ = "consent.read"
    CONSENT_WRITE = "consent.write"
    CONSENT_OVERVIEW = "consent.overview"
    TEAM_MEMBERS_READ = "team.members.read"
    TEAM_MEMBERS_MANAGE = "team.members.manage"
    INVITE_TEAM = "invite.team"
    MATCH_READ = "match.read"
    MATCH_WRITE = "match.write"
    # deleting a match or a video of it (Trainer and Co-Trainer, never players: K18)
    MATCH_DELETE = "match.delete"
    VIDEO_UPLOAD = "video.upload"
    CLIP_WRITE = "clip.write"
    PLAYLIST_READ_ALL = "playlist.read_all"
    PLAYLIST_WRITE = "playlist.write"
    COMMENT_WRITE = "comment.write"
    COMMENT_MODERATE = "comment.moderate"
    ANNOTATION_WRITE = "annotation.write"
    EVENT_WRITE = "event.write"
    PLAY_READ_ALL = "play.read_all"
    PLAY_WRITE = "play.write"
    ASSIGNMENT_WRITE = "assignment.write"
    ASSISTANT_USE = "assistant.use"
    TRAINING_WRITE = "training.write"
    PLAYER_LINE_READ_ALL = "player_line.read_all"
    OFFICIAL_MANAGE = "official.manage"
    JOIN_REQUESTS_MANAGE = "join_requests.manage"


ORG_ACTIONS: dict[Action, frozenset[OrgRole]] = {
    Action.ORG_READ: frozenset({OrgRole.ORG_ADMIN, OrgRole.MEMBER}),
    Action.ORG_UPDATE: frozenset({OrgRole.ORG_ADMIN}),
    Action.ORG_MEMBERS_READ: frozenset({OrgRole.ORG_ADMIN}),
    Action.TEAM_CREATE: frozenset({OrgRole.ORG_ADMIN}),
    Action.TEAM_DELETE: frozenset({OrgRole.ORG_ADMIN}),
    Action.INVITE_ORG: frozenset({OrgRole.ORG_ADMIN}),
    Action.AUDIT_READ: frozenset({OrgRole.ORG_ADMIN}),
    # access requests to a club claimed from the official data
    Action.ORG_ACCESS_MANAGE: frozenset({OrgRole.ORG_ADMIN}),
}

# Co-Trainer roles: coach rights in the team (K18). The old specialist roles keep working and
# read as Co-Trainer in the product.
_COACHES = frozenset(
    {
        TeamRole.COACH,
        TeamRole.ANALYST,
        TeamRole.TEAM_MANAGER,
        TeamRole.GOALKEEPER_COACH,
        TeamRole.ATHLETIC_COACH,
    }
)
_PLAYERS = frozenset({TeamRole.PLAYER, TeamRole.GOALKEEPER})
# parents are deliberately not readers: they only reach their own children (guardianships)
_READERS = _COACHES | _PLAYERS
# kept for callers that ask who works with video in a team: everyone who reads the team
_STAFF = _COACHES

TEAM_ACTIONS: dict[Action, frozenset[TeamRole]] = {
    # see everything of the team
    Action.TEAM_READ: _READERS,
    Action.ROSTER_READ: _READERS,
    Action.MATCH_READ: _READERS,
    Action.PLAYLIST_READ_ALL: _READERS,
    Action.PLAY_READ_ALL: _READERS,
    # a player's season line (figures per match with event links)
    Action.PLAYER_LINE_READ_ALL: _READERS,
    # work with the video: upload, mark scenes, draw, comment, answer the analysis' questions,
    # build collections and share them by link (players too, K18)
    Action.MATCH_WRITE: _READERS,
    Action.VIDEO_UPLOAD: _READERS,
    Action.CLIP_WRITE: _READERS,
    Action.ANNOTATION_WRITE: _READERS,
    Action.COMMENT_WRITE: _READERS,
    Action.EVENT_WRITE: _READERS,
    Action.PLAYLIST_WRITE: _READERS,
    # the team's people (with their e-mail addresses), the squad and the team itself
    Action.TEAM_MEMBERS_READ: _COACHES,
    Action.TEAM_MEMBERS_MANAGE: _COACHES,
    Action.INVITE_TEAM: _COACHES,
    Action.JOIN_REQUESTS_MANAGE: _COACHES,
    Action.TEAM_UPDATE: _COACHES,
    Action.SEASON_WRITE: _COACHES,
    Action.ROSTER_WRITE: _COACHES,
    # injured or absent on the squad: the staff set it; players see only their own status
    Action.PLAYER_STATUS: _COACHES,
    Action.CONSENT_READ: _COACHES,
    Action.CONSENT_WRITE: _COACHES,
    Action.CONSENT_OVERVIEW: _COACHES,
    # official data: sync and suggestions carry names from the official data
    Action.OFFICIAL_MANAGE: _COACHES,
    # deleting is for the staff only
    Action.MATCH_DELETE: _COACHES,
    Action.COMMENT_MODERATE: _COACHES,
    # plays, tasks, sessions and the assistant (which reads and costs per question)
    Action.PLAY_WRITE: _COACHES,
    Action.ASSIGNMENT_WRITE: _COACHES,
    Action.ASSISTANT_USE: _COACHES,
    Action.TRAINING_WRITE: _COACHES,
}

# Actions that change rights, billing or the organisation.
# Org admins need 2FA for them after the grace period.
REQUIRES_2FA = frozenset(ORG_ACTIONS) - {Action.ORG_READ}


@dataclass(frozen=True, slots=True)
class Actor:
    user_id: uuid.UUID
    organization_id: uuid.UUID
    org_role: OrgRole
    team_roles: dict[uuid.UUID, TeamRole] = field(default_factory=dict)
    has_2fa: bool = False
    org_created_at: datetime | None = None

    @property
    def is_org_admin(self) -> bool:
        return self.org_role == OrgRole.ORG_ADMIN

    def team_role(self, team_id: uuid.UUID) -> TeamRole | None:
        return self.team_roles.get(team_id)


@dataclass(frozen=True, slots=True)
class TwoFactorPolicy:
    required: bool
    grace_days: int


def can(actor: Actor, action: Action, team_id: uuid.UUID | None = None) -> bool:
    if action in ORG_ACTIONS:
        return actor.org_role in ORG_ACTIONS[action]
    if action in TEAM_ACTIONS:
        if team_id is None:
            raise ValueError(f"{action} needs a team")
        if actor.is_org_admin:
            return True
        role = actor.team_role(team_id)
        return role is not None and role in TEAM_ACTIONS[action]
    raise ValueError(f"unknown action {action}")


def two_factor_missing(actor: Actor, policy: TwoFactorPolicy, now: datetime | None = None) -> bool:
    if not policy.required or not actor.is_org_admin or actor.has_2fa:
        return False
    if actor.org_created_at is None:
        return True
    now = now or datetime.now(UTC)
    return now > actor.org_created_at + timedelta(days=policy.grace_days)


def authorize(
    actor: Actor,
    action: Action,
    team_id: uuid.UUID | None = None,
    two_factor: TwoFactorPolicy | None = None,
) -> None:
    if not can(actor, action, team_id):
        raise ProblemError(403, "forbidden", f"Missing permission {action.value}")
    if two_factor and action in REQUIRES_2FA and two_factor_missing(actor, two_factor):
        raise ProblemError(
            403, "two-factor-required", "Organisation admins must enable two-factor authentication"
        )


def is_staff_somewhere(actor: Actor) -> bool:
    """Org admins, or anyone who works with the matches of a team (Trainer, Co-Trainer, players:
    K18): may add opponents and their numbers."""
    return actor.is_org_admin or any(r in _READERS for r in actor.team_roles.values())


def is_coach(actor: Actor, team_id: uuid.UUID) -> bool:
    """Trainer or Co-Trainer of the team (or club admin)."""
    return actor.is_org_admin or actor.team_role(team_id) in _COACHES


def person_role(org_role: OrgRole | None, team_role: TeamRole | None) -> PersonRole | None:
    """Stored roles to the product's four. None: no role in the team (a guest, or nobody)."""
    if team_role in _COACHES:
        return PersonRole.TRAINER if org_role == OrgRole.ORG_ADMIN else PersonRole.CO_TRAINER
    if team_role in _PLAYERS:
        return PersonRole.PLAYER
    if team_role == TeamRole.PARENT:
        return PersonRole.PARENT
    if org_role == OrgRole.ORG_ADMIN:
        return PersonRole.TRAINER
    return None


def stored_roles(role: PersonRole) -> tuple[OrgRole, TeamRole]:
    """The product's role to what is stored for a new team member."""
    return {
        PersonRole.TRAINER: (OrgRole.ORG_ADMIN, TeamRole.COACH),
        PersonRole.CO_TRAINER: (OrgRole.MEMBER, TeamRole.COACH),
        PersonRole.PLAYER: (OrgRole.MEMBER, TeamRole.PLAYER),
        PersonRole.PARENT: (OrgRole.MEMBER, TeamRole.PARENT),
    }[role]


def visible_team_ids(actor: Actor) -> set[uuid.UUID] | None:
    """None means all teams of the organisation (org admin)."""
    if actor.is_org_admin:
        return None
    return {t for t, r in actor.team_roles.items() if r in _READERS}


def matrix_markdown() -> str:
    """Human-readable permission matrix (docs/policy-matrix.md is generated from this)."""
    roles = ["org_admin", *[r.value for r in TeamRole]]
    names = {
        PersonRole.TRAINER: "Trainer",
        PersonRole.CO_TRAINER: "Co-Trainer",
        PersonRole.PLAYER: "Spieler",
        PersonRole.PARENT: "Eltern",
    }
    shown = {"org_admin": "Trainer"} | {
        r.value: names.get(person_role(OrgRole.MEMBER, r), "Gast (Links)")  # type: ignore[arg-type]
        for r in TeamRole
    }
    lines = [
        "# Permission matrix",
        "",
        "Generated from `handball_api/services/policies.py` (`make policy-doc`). Do not edit.",
        "Enforced server-side; verified by `apps/api/tests/test_policy_matrix.py`.",
        "",
        "The product shows four roles (K18): **Trainer** (coach and club admin), **Co-Trainer** "
        "(coach rights in the team, no club or subscription), **Spieler**, **Eltern**. The "
        "stored roles stay; the second header row says which of the four each one is.",
        "",
        "| Action | " + " | ".join(roles) + " |",
        "|---|" + "---|" * len(roles),
        "| *shown as* | " + " | ".join(shown[r] for r in roles) + " |",
    ]
    for action, allowed_org in ORG_ACTIONS.items():
        # users with only a team role are plain organisation members
        org_role = {r: OrgRole.ORG_ADMIN if r == "org_admin" else OrgRole.MEMBER for r in roles}
        cells = ["✓" if org_role[r] in allowed_org else "" for r in roles]
        lines.append(f"| `{action.value}` | " + " | ".join(cells) + " |")
    for action, allowed_team in TEAM_ACTIONS.items():
        cells = ["✓" if r == "org_admin" or TeamRole(r) in allowed_team else "" for r in roles]
        lines.append(f"| `{action.value}` | " + " | ".join(cells) + " |")
    lines += [
        "",
        "- Team actions apply to the teams where the user has that role; "
        "org admins act in every team.",
        "- A Trainer is stored as `coach` with the organisation role `org_admin`; inviting a "
        "Trainer needs `invite.org`. A `coach` without it is a Co-Trainer.",
        "- `analyst`, `team_manager`, `goalkeeper_coach` and `athletic_coach` are older roles "
        "with the same rights as `coach`; the product shows them as Co-Trainer.",
        "- Players (`player`, `goalkeeper`) see everything of the team, mark scenes, build "
        "collections and share them by link, comment, answer the analysis' questions and upload "
        "videos. They do not delete matches or videos, invite people, change the squad, the team, "
        "the club or the subscription, and revoke only share links they made.",
        "- Org admins need two-factor sign-in for org-level write actions after the grace period "
        "(`HB_ORG_ADMIN_2FA_GRACE_DAYS`, default 14).",
        "- Guests get access only through share links (M8).",
        "- Parents (`parent`) get no team access: they see their own children only "
        "(guardianships, `/me/consents`) and manage their consents per purpose.",
        "- Players decide their own consents (`/me/consents`); minors need a parent or guardian.",
        "- Youth teams (addendum 01, 4.9): share links only for plays, no consent for public "
        "purposes (public highlights, public profile), season player lists unranked.",
        "- Public highlights need the public highlights consent of every featured player.",
        "- Opponent players: number only; a name needs a public source and is never public.",
        "- Training slots and own drills: `training.write` in the team. A drill shared in the "
        "club is read by the readers of every team and changed only by the team that made it.",
        "- Club admin handover: `PATCH /orgs/{id}/members/{user}`; "
        "the last admin cannot step down.",
        "",
    ]
    return "\n".join(lines)
