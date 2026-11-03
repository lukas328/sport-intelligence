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
from handball_api.models.sharing import ShareLink
from handball_api.models.tactics import Play
from handball_api.models.tenancy import (
    Invitation,
    Membership,
    Organization,
    OrgMembership,
    Season,
    StripeEvent,
    Team,
)
from handball_api.models.training import Assignment, AssignmentStatus, Notification

__all__ = [
    "Annotation",
    "Assignment",
    "AssignmentStatus",
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
    "Notification",
    "OAuthIdentity",
    "Opponent",
    "OrgMembership",
    "Organization",
    "Play",
    "Player",
    "Playlist",
    "PlaylistItem",
    "Possession",
    "ProcessingJob",
    "RosterEntry",
    "Season",
    "ShareLink",
    "StatsCache",
    "StripeEvent",
    "Team",
    "Track",
    "User",
    "VideoAsset",
]
