"""Plans, limits and feature flags in one place (BRIEF 13). Prices are placeholders from config."""

from __future__ import annotations

from dataclasses import dataclass, field

from handball_api.models.enums import Plan

FEATURES = (
    "events",  # tagging, match report, clips, playlists
    "tracking",  # video analysis (positions, mini court, physical load, formations)
    "insights",  # insights, summaries
    "tactics",  # play library and tactics board
    "season",  # season statistics, opponent profiles
    "share_links",
    "pdf_reports",
    "club_stats",
    "priority",  # priority processing queue
    "assistant",  # ask your data (5.1), capped per month by assistant_usd_month
)


@dataclass(frozen=True)
class PlanSpec:
    plan: Plan
    teams: int
    matches_per_season: int | None  # per team, None = unlimited (fair use)
    storage_gb: int
    gpu_minutes_month: int
    features: frozenset[str] = field(default_factory=frozenset)
    price_chf_month: int = 0
    trial_days: int = 0
    assistant_usd_month: float = 0.0  # model cost cap of the data assistant per organisation


_ALL = frozenset(FEATURES) - {"club_stats", "priority"}

PLANS: dict[Plan, PlanSpec] = {
    Plan.FREE: PlanSpec(
        Plan.FREE,
        teams=1,
        matches_per_season=2,
        storage_gb=10,
        gpu_minutes_month=0,
        features=frozenset({"events"}),
    ),
    Plan.TEAM: PlanSpec(
        Plan.TEAM,
        teams=1,
        matches_per_season=None,
        storage_gb=250,
        gpu_minutes_month=1500,
        features=_ALL,
        price_chf_month=39,
        trial_days=30,
        assistant_usd_month=5.0,
    ),
    Plan.CLUB: PlanSpec(
        Plan.CLUB,
        teams=10,
        matches_per_season=None,
        storage_gb=2500,
        gpu_minutes_month=15000,
        features=frozenset(FEATURES),
        price_chf_month=199,
        trial_days=30,
        assistant_usd_month=25.0,
    ),
}
GOALKEEPER_ADDON_CHF = 7
# fair use for "unlimited" matches; above this the UI asks to contact support
FAIR_USE_MATCHES_PER_SEASON = 80
