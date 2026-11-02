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
    VIDEO_ANALYSIS = "video_analysis"
    IDENTIFICATION = "identification"


class ConsentGivenBy(StrEnum):
    SELF = "self"
    PARENT = "parent"
    GUARDIAN = "guardian"


class TokenPurpose(StrEnum):
    MAGIC_LINK = "magic_link"
