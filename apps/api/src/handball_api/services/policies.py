"""Role-based permissions (BRIEF 3), enforced server-side for every resource.

One table maps each action to the roles allowed to perform it. Org-level actions are checked
against the organisation role, team-level actions against the team role (org admins may do
everything a coach may do in every team of their organisation).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from handball_api.core.errors import ProblemError
from handball_api.models.enums import OrgRole, TeamRole


class Action(StrEnum):
    # organisation level
    ORG_READ = "org.read"
    ORG_UPDATE = "org.update"
    ORG_MEMBERS_READ = "org.members.read"
    TEAM_CREATE = "team.create"
    TEAM_DELETE = "team.delete"
    INVITE_ORG = "invite.org"
    AUDIT_READ = "audit.read"
    # team level
    TEAM_READ = "team.read"
    TEAM_UPDATE = "team.update"
    SEASON_WRITE = "season.write"
    ROSTER_READ = "roster.read"
    ROSTER_WRITE = "roster.write"
    CONSENT_READ = "consent.read"
    CONSENT_WRITE = "consent.write"
    TEAM_MEMBERS_READ = "team.members.read"
    TEAM_MEMBERS_MANAGE = "team.members.manage"
    INVITE_TEAM = "invite.team"
    MATCH_READ = "match.read"
    MATCH_WRITE = "match.write"
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


ORG_ACTIONS: dict[Action, frozenset[OrgRole]] = {
    Action.ORG_READ: frozenset({OrgRole.ORG_ADMIN, OrgRole.MEMBER}),
    Action.ORG_UPDATE: frozenset({OrgRole.ORG_ADMIN}),
    Action.ORG_MEMBERS_READ: frozenset({OrgRole.ORG_ADMIN}),
    Action.TEAM_CREATE: frozenset({OrgRole.ORG_ADMIN}),
    Action.TEAM_DELETE: frozenset({OrgRole.ORG_ADMIN}),
    Action.INVITE_ORG: frozenset({OrgRole.ORG_ADMIN}),
    Action.AUDIT_READ: frozenset({OrgRole.ORG_ADMIN}),
}

_STAFF = frozenset({TeamRole.COACH, TeamRole.ANALYST})
# specialist coaches read everything and work with video, but do not manage team or data
_ASSISTANTS = frozenset({TeamRole.GOALKEEPER_COACH, TeamRole.ATHLETIC_COACH})
_MANAGER = frozenset({TeamRole.TEAM_MANAGER})
# parents are deliberately not readers: they only reach their own children (guardianships)
_READERS = frozenset({TeamRole.PLAYER, TeamRole.GOALKEEPER}) | _STAFF | _ASSISTANTS | _MANAGER
_COACH = frozenset({TeamRole.COACH})
_VIDEO_WORK = _STAFF | _ASSISTANTS
_ORGANISE = _COACH | _MANAGER

TEAM_ACTIONS: dict[Action, frozenset[TeamRole]] = {
    Action.TEAM_READ: _READERS,
    Action.ROSTER_READ: _READERS,
    Action.TEAM_MEMBERS_READ: _STAFF | _ASSISTANTS | _MANAGER,
    Action.SEASON_WRITE: _STAFF | _MANAGER,
    Action.TEAM_UPDATE: _COACH,
    Action.ROSTER_WRITE: _ORGANISE,
    Action.CONSENT_READ: _ORGANISE,
    Action.CONSENT_WRITE: _ORGANISE,
    Action.TEAM_MEMBERS_MANAGE: _COACH,
    Action.INVITE_TEAM: _ORGANISE,
    Action.MATCH_READ: _READERS,
    Action.MATCH_WRITE: _STAFF | _MANAGER,
    Action.VIDEO_UPLOAD: _STAFF | _MANAGER,
    Action.CLIP_WRITE: _VIDEO_WORK,
    Action.PLAYLIST_READ_ALL: _VIDEO_WORK,
    Action.PLAYLIST_WRITE: _VIDEO_WORK,
    Action.COMMENT_WRITE: _READERS,
    Action.COMMENT_MODERATE: _STAFF,
    Action.ANNOTATION_WRITE: _VIDEO_WORK,
    Action.EVENT_WRITE: _STAFF,
    Action.PLAY_READ_ALL: _VIDEO_WORK,
    Action.PLAY_WRITE: _STAFF,
    Action.ASSIGNMENT_WRITE: _VIDEO_WORK,
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
    """Org admins, or coach/analyst/team manager of a team (e.g. may manage opponents)."""
    return actor.is_org_admin or any(r in _STAFF | _MANAGER for r in actor.team_roles.values())


def visible_team_ids(actor: Actor) -> set[uuid.UUID] | None:
    """None means all teams of the organisation (org admin)."""
    if actor.is_org_admin:
        return None
    return {t for t, r in actor.team_roles.items() if r in _READERS}


def matrix_markdown() -> str:
    """Human-readable permission matrix (docs/policy-matrix.md is generated from this)."""
    roles = ["org_admin", *[r.value for r in TeamRole]]
    lines = [
        "# Permission matrix",
        "",
        "Generated from `handball_api/services/policies.py` (`make policy-doc`). Do not edit.",
        "Enforced server-side; verified by `apps/api/tests/test_policy_matrix.py`.",
        "",
        "| Action | " + " | ".join(roles) + " |",
        "|---|" + "---|" * len(roles),
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
        "- Org admins need two-factor sign-in for org-level write actions after the grace period "
        "(`HB_ORG_ADMIN_2FA_GRACE_DAYS`, default 14).",
        "- Guests get access only through share links (M8).",
        "- Parents (`parent`) get no team access: they see their own children only "
        "(guardianships, `/me/consents`) and manage their consents per purpose.",
        "- Players decide their own consents (`/me/consents`); minors need a parent or guardian.",
        "- Youth teams (addendum 01, 4.9): share links only for plays, no consent for public "
        "purposes (public highlights, public profile), season player lists unranked.",
        "- Opponent players: number only; a name needs a public source and is never public.",
        "- Club admin handover: `PATCH /orgs/{id}/members/{user}`; "
        "the last admin cannot step down.",
        "",
    ]
    return "\n".join(lines)
