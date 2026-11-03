from __future__ import annotations

from enum import StrEnum


class OrgRole(StrEnum):
    ORG_ADMIN = "org_admin"
    MEMBER = "member"


class TeamRole(StrEnum):
    COACH = "coach"
    ANALYST = "analyst"
    PLAYER = "player"
    GOALKEEPER = "goalkeeper"
    GUEST = "guest"
    # addendum 01
    GOALKEEPER_COACH = "goalkeeper_coach"
    ATHLETIC_COACH = "athletic_coach"
    TEAM_MANAGER = "team_manager"
    PARENT = "parent"  # sees only content of their own children (guardianships)


class Position(StrEnum):
    LA = "LA"
    RL = "RL"
    RM = "RM"
    RR = "RR"
    RA = "RA"
    KM = "KM"
    TW = "TW"


class Hand(StrEnum):
    LEFT = "left"
    RIGHT = "right"


class TeamGender(StrEnum):
    MEN = "men"
    WOMEN = "women"
    MIXED = "mixed"


class Plan(StrEnum):
    FREE = "free"
    TEAM = "team"
    CLUB = "club"


class DataRegion(StrEnum):
    CH = "ch"
    EU = "eu"


class ConsentKind(StrEnum):
    """Consent purposes (addendum 01 section 3); history = rows, latest unrevoked row counts."""

    ANALYSIS = "analysis"
    HIGHLIGHTS_INTERNAL = "highlights_internal"
    HIGHLIGHTS_PUBLIC = "highlights_public"
    PUBLIC_PROFILE = "public_profile"
    TRAINING_DATA = "training_data"


class ConsentGivenBy(StrEnum):
    SELF = "self"
    PARENT = "parent"
    GUARDIAN = "guardian"


class TokenPurpose(StrEnum):
    MAGIC_LINK = "magic_link"
    PASSWORD_RESET = "password_reset"  # noqa: S105 (enum value, not a secret)
    EMAIL_VERIFY = "email_verify"


class OAuthProvider(StrEnum):
    GOOGLE = "google"
    APPLE = "apple"


class MatchStatus(StrEnum):
    SCHEDULED = "scheduled"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class VideoRole(StrEnum):
    MAIN = "main"
    GOAL_CAM_LEFT = "goal_cam_left"
    GOAL_CAM_RIGHT = "goal_cam_right"
    OTHER = "other"


class VideoStatus(StrEnum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ClipSource(StrEnum):
    MANUAL = "manual"
    EVENT = "event"
    POSSESSION = "possession"
    PLAY = "play"


# ---- addendum 01 section 3 ----------------------------------------------------------------------


class PaymentMethod(StrEnum):
    CARD = "card"
    INVOICE_QR = "invoice_qr"


class SlideType(StrEnum):
    CLIP = "clip"
    TACTICS_BOARD = "tactics_board"
    TEXT = "text"
    STAT_CARD = "stat_card"
    IMAGE = "image"


class ReelFormat(StrEnum):
    LANDSCAPE = "16x9"
    PORTRAIT = "9x16"


class ReelStatus(StrEnum):
    QUEUED = "queued"
    RENDERING = "rendering"
    READY = "ready"
    FAILED = "failed"
    BLOCKED_CONSENT = "blocked_consent"


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    EXCUSED = "excused"
    INJURED = "injured"  # absence only, never a diagnosis (health data minimised)
    LATE = "late"


class UploadStatus(StrEnum):
    PENDING = "pending"
    EXTRACTED = "extracted"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class MatchFormatKey(StrEnum):
    """Templates (4.8). The match stores the resolved values so later template edits do not change
    old matches."""

    ADULT_2X30 = "adult_2x30"
    YOUTH_2X25 = "youth_2x25"
    YOUTH_2X20 = "youth_2x20"
    MINI = "mini"
    TOURNAMENT = "tournament"
    CUSTOM = "custom"
