from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from handball_api.core.db import Base, EntityMixin, TenantMixin


class Collection(Base, EntityMixin, TenantMixin):
    """Sammlung (SPEC 7.7): one object for what playlists, presentations and assignments did.
    An ordered run of scenes, plays and notes, shared by link or shown on the big screen."""

    __tablename__ = "collections"

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # draft: made from the three things of a match and not trimmed yet
    draft: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    # the match it was made from, if any (the three things)
    match_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("matches.id", ondelete="SET NULL"), index=True
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class CollectionItem(Base, EntityMixin, TenantMixin):
    """One entry of a collection: a scene (a clip, i.e. a window of a match video), a play or a
    note."""

    __tablename__ = "collection_items"
    __table_args__ = (
        CheckConstraint("kind IN ('scene', 'play', 'note')", name="kind_values"),
        CheckConstraint(
            "(kind = 'scene' AND clip_id IS NOT NULL) OR (kind = 'play' AND play_id IS NOT NULL)"
            " OR (kind = 'note' AND text IS NOT NULL)",
            name="kind_target",
        ),
    )

    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    clip_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clips.id", ondelete="CASCADE"))
    play_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plays.id", ondelete="CASCADE"))
    # the note itself, or the coach's note at a scene or play
    text: Mapped[str | None] = mapped_column(Text)
