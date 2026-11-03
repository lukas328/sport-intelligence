"""SQLAlchemy models (BRIEF 5)."""

from handball_api.models.audit import AuditLog
from handball_api.models.identity import AuthSession, AuthToken, OAuthIdentity, User
from handball_api.models.matches import (
    Annotation,
    CameraCalibration,
    Clip,
    Comment,
    Correction,
    Event,
    Match,
    Opponent,
    Playlist,
    PlaylistItem,
    Possession,
    ProcessingJob,
    StatsCache,
    Track,
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
    "CameraCalibration",
    "Clip",
    "Comment",
    "Consent",
    "Correction",
    "Event",
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
    "Possession",
    "ProcessingJob",
    "RosterEntry",
    "Season",
    "StatsCache",
    "Team",
    "Track",
    "User",
    "VideoAsset",
]
