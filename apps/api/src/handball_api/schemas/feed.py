from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from handball_api.schemas.common import ApiModel


class SelfAssessmentIn(ApiModel):
    rating: int = Field(ge=1, le=5)
    text: str | None = Field(default=None, max_length=500)
    player_id: uuid.UUID | None = None


class SelfAssessmentOut(ApiModel):
    rating: int
    text: str | None
    submitted_at: datetime


class FeedScene(ApiModel):
    id: uuid.UUID
    rank: int
    reason: str
    positive: bool
    clip_id: uuid.UUID
    start_ms: int
    end_ms: int
    event_id: uuid.UUID | None
    coach_comment: str | None


class PlayerFeed(ApiModel):
    match_id: uuid.UUID
    player_id: uuid.UUID
    video_id: uuid.UUID | None
    youth: bool
    self_assessment: SelfAssessmentOut | None
    items: list[FeedScene]
    coach_comments_waiting: int = Field(
        description="comments the player sees after the self-assessment"
    )


class FeedListItem(ApiModel):
    player_id: uuid.UUID
    player_first_name: str
    relation: str
    match_id: uuid.UUID
    kickoff_at: datetime
    opponent: str | None
    assessed: bool


class CoachScene(FeedScene):
    seen: bool


class CoachFeedPlayer(ApiModel):
    player_id: uuid.UUID
    name: str
    number: int | None
    self_assessment: SelfAssessmentOut | None
    items: list[CoachScene]


class FeedComment(ApiModel):
    coach_comment: str | None = Field(default=None, max_length=1000)


class FeedSwap(ApiModel):
    event_id: uuid.UUID


class FeedGenerated(ApiModel):
    players: int
