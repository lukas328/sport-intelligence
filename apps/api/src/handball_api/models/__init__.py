"""SQLAlchemy models (BRIEF 5)."""

from handball_api.models.audit import AuditLog
from handball_api.models.identity import AuthSession, AuthToken, OAuthIdentity, User
from handball_api.models.matches import (
    Annotation,
    Clip,
    Comment,
    Match,
    Opponent,
    Playlist,
    PlaylistItem,
    ProcessingJob,
    VideoAsset,
)
from handball_api.models.roster import Consent, Player, RosterEntry
from handball_api.models.tenancy import (
    Invitation,
    Membership,
    Organization,
    OrgMembership,
    Season,
    Team,
)

__all__ = [
    "Annotation",
    "AuditLog",
    "AuthSession",
    "AuthToken",
    "Clip",
    "Comment",
    "Consent",
    "Invitation",
    "Match",
    "Membership",
    "OAuthIdentity",
    "Opponent",
    "OrgMembership",
    "Organization",
    "Player",
    "Playlist",
    "PlaylistItem",
    "ProcessingJob",
    "RosterEntry",
    "Season",
    "Team",
    "User",
    "VideoAsset",
]
