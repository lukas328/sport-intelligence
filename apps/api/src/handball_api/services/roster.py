"""Players, roster entries, CSV import, consents."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select

from handball_api.core.errors import ProblemError
from handball_api.models import (
    Consent,
    Membership,
    Player,
    PlayerStatus,
    RosterEntry,
    Season,
    User,
)
from handball_api.models.enums import ConsentGivenBy, ConsentKind, Position, TeamRole
from handball_api.schemas.roster import (
    ConsentCreate,
    ImportResult,
    ImportRowError,
    PlayerAccountOut,
    PlayerStatusIn,
    PlayerStatusOut,
    RosterEntryCreate,
    RosterEntryOut,
    RosterEntryUpdate,
)
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.csv_import import parse_roster_csv
from handball_api.services.orgs import get_season, get_team
from handball_api.services.policies import Action, can

PLAYER_FIELDS = (
    "first_name",
    "last_name",
    "birth_year",
    "shooting_hand",
    "main_position",
    "secondary_positions",
)


async def numbers(ctx: Ctx, season_id: uuid.UUID, team_id: uuid.UUID) -> dict[int, uuid.UUID]:
    """Shirt number -> player of a team's active roster in a season (entries without a number
    are left out). Used to link official reports, overlays, feeds and paper reports to players."""
    rows = await ctx.db.execute(
        select(RosterEntry.jersey_number, RosterEntry.player_id).where(
            RosterEntry.season_id == season_id,
            RosterEntry.team_id == team_id,
            RosterEntry.active.is_(True),
        )
    )
    return {n: pid for n, pid in rows.all() if n is not None}


async def _consented_players(ctx: Ctx, player_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not player_ids:
        return set()
    rows = await ctx.db.execute(
        select(Consent.player_id, Consent.kind).where(
            Consent.player_id.in_(player_ids), Consent.revoked_at.is_(None)
        )
    )
    kinds: dict[uuid.UUID, set[ConsentKind]] = {}
    for pid, kind in rows:
        kinds.setdefault(pid, set()).add(kind)
    # a roster entry is complete when video analysis is consented; other purposes are opt-ins
    return {pid for pid, k in kinds.items() if ConsentKind.ANALYSIS in k}


def _out(
    entry: RosterEntry,
    player: Player,
    consented: bool,
    status: PlayerStatusOut | None = None,
    show_account: bool = True,
) -> RosterEntryOut:
    return RosterEntryOut(
        id=entry.id,
        player_id=player.id,
        season_id=entry.season_id,
        jersey_number=entry.jersey_number,
        active=entry.active,
        first_name=player.first_name,
        last_name=player.last_name,
        birth_year=player.birth_year,
        shooting_hand=player.shooting_hand,
        main_position=player.main_position,
        secondary_positions=[Position(p) for p in player.secondary_positions],
        has_account=player.user_id is not None,
        account_user_id=player.user_id if show_account else None,
        consent_complete=consented,
        status=status,
    )


async def list_roster(ctx: Ctx, team_id: uuid.UUID, season_id: uuid.UUID) -> list[RosterEntryOut]:
    await get_team(ctx, team_id, Action.ROSTER_READ)
    await get_season(ctx, team_id, season_id)
    rows = [
        (e, p)
        for e, p in await ctx.db.execute(
            select(RosterEntry, Player)
            .join(Player, Player.id == RosterEntry.player_id)
            .where(RosterEntry.season_id == season_id)
            .order_by(
                RosterEntry.active.desc(),
                RosterEntry.jersey_number.nulls_last(),
                Player.last_name,
            )
        )
    ]
    staff = can(ctx.require_actor(), Action.ROSTER_WRITE, team_id)
    if not staff:
        rows = await _without_official_only(ctx, rows)
    consented = await _consented_players(ctx, [p.id for _, p in rows])
    if can(ctx.require_actor(), Action.PLAYER_STATUS, team_id):
        shown = [p.id for _, p in rows]
    else:  # players see only their own status
        shown = [p.id for _, p in rows if p.user_id is not None and p.user_id == ctx.user_id]
    statuses = await _current_statuses(ctx, team_id, shown)
    return [_out(e, p, p.id in consented, statuses.get(p.id), staff) for e, p in rows]


# ---- player status on the squad (injured, absent; no status means fit) ----------------------


def today() -> date:
    """The club's day (Switzerland): an until-date counts up to its end there."""
    return datetime.now(ZoneInfo("Europe/Zurich")).date()


def _status_out(st: PlayerStatus) -> PlayerStatusOut:
    return PlayerStatusOut(
        player_id=st.player_id,
        team_id=st.team_id,
        kind=st.kind,
        until=st.until,
        note=st.note,
        updated_at=st.updated_at,
    )


async def _current_statuses(
    ctx: Ctx, team_id: uuid.UUID, player_ids: list[uuid.UUID] | None = None
) -> dict[uuid.UUID, PlayerStatusOut]:
    """Statuses still in force; a status past its until-date reads as no status."""
    if player_ids is not None and not player_ids:
        return {}
    q = select(PlayerStatus).where(
        PlayerStatus.team_id == team_id,
        or_(PlayerStatus.until.is_(None), PlayerStatus.until >= today()),
    )
    if player_ids is not None:
        q = q.where(PlayerStatus.player_id.in_(player_ids))
    return {st.player_id: _status_out(st) for st in (await ctx.db.scalars(q)).all()}


async def list_statuses(ctx: Ctx, team_id: uuid.UUID) -> list[PlayerStatusOut]:
    """The squad's injured and absent players (staff); players hidden from this actor in the
    roster list (official data not yet joined) are left out here too."""
    await get_team(ctx, team_id, Action.PLAYER_STATUS)
    statuses = await _current_statuses(ctx, team_id)
    if statuses and not can(ctx.require_actor(), Action.ROSTER_WRITE, team_id):
        rows = [
            (e, p)
            for e, p in await ctx.db.execute(
                select(RosterEntry, Player)
                .join(Player, Player.id == RosterEntry.player_id)
                .where(RosterEntry.team_id == team_id, Player.id.in_(list(statuses)))
            )
        ]
        visible = {p.id for _, p in await _without_official_only(ctx, rows)}
        statuses = {pid: st for pid, st in statuses.items() if pid in visible}
    return sorted(statuses.values(), key=lambda st: (st.until or date.max, str(st.player_id)))


async def set_status(
    ctx: Ctx, team_id: uuid.UUID, player_id: uuid.UUID, data: PlayerStatusIn
) -> PlayerStatusOut:
    team = await get_team(ctx, team_id, Action.PLAYER_STATUS)
    await _player_in_team(ctx, team_id, player_id)
    if data.until is not None and data.until < today():
        raise ProblemError(422, "validation", "The until-date lies in the past")
    note = (data.note or "").strip() or None
    st = await ctx.db.scalar(
        select(PlayerStatus).where(
            PlayerStatus.team_id == team_id, PlayerStatus.player_id == player_id
        )
    )
    if st is None:
        st = PlayerStatus(
            organization_id=team.organization_id, team_id=team_id, player_id=player_id
        )
        ctx.db.add(st)
    st.kind, st.until, st.note, st.set_by_id = data.kind, data.until, note, ctx.user_id
    await ctx.db.flush()
    await ctx.db.refresh(st)
    # the kind only: notes stay out of the audit log
    await audit.record(
        ctx,
        "player_status.set",
        target_type="player",
        target_id=player_id,
        data={"kind": data.kind.value},
    )
    return _status_out(st)


async def clear_status(ctx: Ctx, team_id: uuid.UUID, player_id: uuid.UUID) -> None:
    """Back to fit."""
    await get_team(ctx, team_id, Action.PLAYER_STATUS)
    await _player_in_team(ctx, team_id, player_id)
    st = await ctx.db.scalar(
        select(PlayerStatus).where(
            PlayerStatus.team_id == team_id, PlayerStatus.player_id == player_id
        )
    )
    if st is not None:
        await ctx.db.delete(st)
        await audit.record(ctx, "player_status.cleared", target_type="player", target_id=player_id)


async def _without_official_only(
    ctx: Ctx, rows: list[tuple[RosterEntry, Player]]
) -> list[tuple[RosterEntry, Player]]:
    """Entries taken over from the official data stay with the organisers until the person has
    joined (an account) or a consent is recorded (docs/plans/federation-onboarding.md)."""
    pending = [p.id for e, p in rows if e.official_player_id is not None and p.user_id is None]
    if not pending:
        return rows
    known = set(
        (
            await ctx.db.scalars(
                select(Consent.player_id).where(
                    Consent.player_id.in_(pending), Consent.revoked_at.is_(None)
                )
            )
        ).all()
    )
    hidden = set(pending) - known
    return [(e, p) for e, p in rows if p.id not in hidden]


async def visible_players(
    ctx: Ctx, team_id: uuid.UUID, season_id: uuid.UUID
) -> set[uuid.UUID] | None:
    """The season's roster players whose names this actor may see, by the rule of the roster
    list (`_without_official_only`); None when the actor organises the team and sees them all.
    Names from the official data reach other team members only through such an entry: event
    and statistics views ask here before they show one."""
    if can(ctx.require_actor(), Action.ROSTER_WRITE, team_id):
        return None
    rows = [
        (e, p)
        for e, p in await ctx.db.execute(
            select(RosterEntry, Player)
            .join(Player, Player.id == RosterEntry.player_id)
            .where(RosterEntry.season_id == season_id, RosterEntry.team_id == team_id)
        )
    ]
    return {p.id for _, p in await _without_official_only(ctx, rows)}


async def _check_number_free(
    ctx: Ctx, season_id: uuid.UUID, number: int | None, exclude_entry: uuid.UUID | None = None
) -> None:
    if number is None:
        return
    q = select(RosterEntry.id).where(
        RosterEntry.season_id == season_id,
        RosterEntry.jersey_number == number,
        RosterEntry.active.is_(True),
    )
    if exclude_entry:
        q = q.where(RosterEntry.id != exclude_entry)
    if await ctx.db.scalar(q):
        raise ProblemError(
            409, "jersey-number-taken", f"Number {number} is already taken in this season"
        )


async def _add(ctx: Ctx, season: Season, data: RosterEntryCreate) -> tuple[RosterEntry, Player]:
    player = Player(
        organization_id=season.organization_id,
        **{k: v for k, v in data.model_dump().items() if k in PLAYER_FIELDS},
    )
    ctx.db.add(player)
    await ctx.db.flush()
    entry = RosterEntry(
        organization_id=season.organization_id,
        player_id=player.id,
        team_id=season.team_id,
        season_id=season.id,
        jersey_number=data.jersey_number,
        active=True,
    )
    ctx.db.add(entry)
    await ctx.db.flush()
    return entry, player


async def add_entry(
    ctx: Ctx, team_id: uuid.UUID, season_id: uuid.UUID, data: RosterEntryCreate
) -> RosterEntryOut:
    await get_team(ctx, team_id, Action.ROSTER_WRITE)
    season = await get_season(ctx, team_id, season_id)
    await _check_number_free(ctx, season.id, data.jersey_number)
    entry, player = await _add(ctx, season, data)
    await audit.record(ctx, "roster.player_added", target_type="player", target_id=player.id)
    return _out(entry, player, False)


async def _entry(ctx: Ctx, team_id: uuid.UUID, entry_id: uuid.UUID) -> tuple[RosterEntry, Player]:
    row = (
        await ctx.db.execute(
            select(RosterEntry, Player)
            .join(Player, Player.id == RosterEntry.player_id)
            .where(RosterEntry.id == entry_id, RosterEntry.team_id == team_id)
        )
    ).first()
    if row is None:
        raise ProblemError(404, "not-found", "Roster entry not found")
    entry, player = row
    return entry, player


async def update_entry(
    ctx: Ctx, team_id: uuid.UUID, entry_id: uuid.UUID, data: RosterEntryUpdate
) -> RosterEntryOut:
    await get_team(ctx, team_id, Action.ROSTER_WRITE)
    entry, player = await _entry(ctx, team_id, entry_id)
    values = data.model_dump(exclude_unset=True)
    if "jersey_number" in values or values.get("active"):
        active = values.get("active", entry.active)
        if active:
            await _check_number_free(
                ctx, entry.season_id, values.get("jersey_number", entry.jersey_number), entry.id
            )
    for k, v in values.items():
        if k in PLAYER_FIELDS:
            setattr(player, k, v)
        else:
            setattr(entry, k, v)
    await ctx.db.flush()
    consented = await _consented_players(ctx, [player.id])
    return _out(entry, player, player.id in consented)


async def remove_entry(ctx: Ctx, team_id: uuid.UUID, entry_id: uuid.UUID) -> None:
    await get_team(ctx, team_id, Action.ROSTER_WRITE)
    entry, player = await _entry(ctx, team_id, entry_id)
    await ctx.db.delete(entry)
    await audit.record(ctx, "roster.player_removed", target_type="player", target_id=player.id)


async def import_csv(
    ctx: Ctx, team_id: uuid.UUID, season_id: uuid.UUID, data: bytes, dry_run: bool
) -> ImportResult:
    await get_team(ctx, team_id, Action.ROSTER_WRITE)
    season = await get_season(ctx, team_id, season_id)
    rows, errors = parse_roster_csv(data)
    taken = set(
        (
            await ctx.db.scalars(
                select(RosterEntry.jersey_number).where(
                    RosterEntry.season_id == season.id, RosterEntry.active.is_(True)
                )
            )
        ).all()
    )
    for i, row in enumerate(rows):
        if row.jersey_number is not None and row.jersey_number in taken:
            errors.append(
                ImportRowError(
                    row=i + 2,
                    field="jersey_number",
                    message=f"Number {row.jersey_number} is already in the roster",
                )
            )
    if not rows and not errors:
        errors.append(ImportRowError(row=0, field=None, message="The file contains no players"))
    created = 0
    if not dry_run and not errors:
        for row in rows:
            await _add(ctx, season, row)
            created += 1
        await audit.record(
            ctx,
            "roster.imported",
            target_type="season",
            target_id=season.id,
            data={"count": created},
        )
    return ImportResult(
        dry_run=dry_run, rows=rows, errors=sorted(errors, key=lambda e: e.row), created=created
    )


async def _player_in_team(
    ctx: Ctx, team_id: uuid.UUID, player_id: uuid.UUID, lock: bool = False
) -> Player:
    q = (
        select(Player)
        .join(RosterEntry, RosterEntry.player_id == Player.id)
        .where(Player.id == player_id, RosterEntry.team_id == team_id)
        .limit(1)
    )
    if lock:
        q = q.with_for_update(of=Player).execution_options(populate_existing=True)
    player = await ctx.db.scalar(q)
    if player is None:
        raise ProblemError(404, "not-found", "Player not found in this team")
    return player


# ---- the account of a roster player (invitations and join requests link it; staff fix it) ----


async def link_account(
    ctx: Ctx, team_id: uuid.UUID, player_id: uuid.UUID, user_id: uuid.UUID
) -> PlayerAccountOut:
    """Link a team member's account to a roster player: the person then sees their dates,
    status, assignments and scenes. An entry with another account is not taken over (409:
    unlink first). Parents are linked to a child by guardianship, never as the player."""
    await get_team(ctx, team_id, Action.ROSTER_WRITE)
    player = await _player_in_team(ctx, team_id, player_id, lock=True)
    row = (
        await ctx.db.execute(
            select(Membership.role, User.name)
            .join(User, User.id == Membership.user_id)
            .where(Membership.team_id == team_id, Membership.user_id == user_id)
        )
    ).first()
    if row is None:
        raise ProblemError(404, "not-found", "Team member not found")
    role, name = row
    if role == TeamRole.PARENT:
        raise ProblemError(
            422, "parent-not-player", "A parent is linked to the child, not as the player"
        )
    if player.user_id is not None and player.user_id != user_id:
        raise ProblemError(409, "player-linked", "This player already has an account")
    if player.user_id is None:
        player.user_id = user_id
        await ctx.db.flush()
        await audit.record(
            ctx,
            "roster.account_linked",
            target_type="player",
            target_id=player.id,
            data={"user_id": str(user_id)},
        )
    return PlayerAccountOut(player_id=player.id, user_id=user_id, name=name)


async def unlink_account(ctx: Ctx, team_id: uuid.UUID, player_id: uuid.UUID) -> None:
    await get_team(ctx, team_id, Action.ROSTER_WRITE)
    player = await _player_in_team(ctx, team_id, player_id, lock=True)
    if player.user_id is not None:
        previous = player.user_id
        player.user_id = None
        await ctx.db.flush()
        await audit.record(
            ctx,
            "roster.account_unlinked",
            target_type="player",
            target_id=player.id,
            data={"user_id": str(previous)},
        )


async def list_consents(ctx: Ctx, team_id: uuid.UUID, player_id: uuid.UUID) -> list[Consent]:
    await get_team(ctx, team_id, Action.CONSENT_READ)
    await _player_in_team(ctx, team_id, player_id)
    rows = await ctx.db.scalars(
        select(Consent).where(Consent.player_id == player_id).order_by(Consent.given_at.desc())
    )
    return list(rows.all())


async def add_consent(
    ctx: Ctx, team_id: uuid.UUID, player_id: uuid.UUID, data: ConsentCreate
) -> Consent:
    team = await get_team(ctx, team_id, Action.CONSENT_WRITE)
    player = await _player_in_team(ctx, team_id, player_id)
    check_consent_giver(player, data.given_by, data.given_at, team.is_youth)
    # youth teams never go public (4.9); minors in adult teams may, with a parent's consent (5.8)
    check_youth_purpose(data.kind, team.is_youth)
    consent = Consent(
        organization_id=team.organization_id,
        player_id=player.id,
        recorded_by_id=ctx.user_id,
        **data.model_dump(),
    )
    ctx.db.add(consent)
    await ctx.db.flush()
    await audit.record(
        ctx, "consent.recorded", target_type="player", target_id=player.id, data={"kind": data.kind}
    )
    return consent


def is_minor(birth_year: int | None, at: datetime) -> bool | None:
    """True/False when known; with only the birth year a player of 18 may still be 17 (minor)."""
    if birth_year is None:
        return None
    return at.year - birth_year <= 18


def check_consent_giver(
    player: Player, given_by: ConsentGivenBy, at: datetime, youth_team: bool
) -> None:
    """Minors (or players of youth teams with unknown age) need a parent or guardian (P6)."""
    minor = is_minor(player.birth_year, at)
    if (minor or (minor is None and youth_team)) and given_by == ConsentGivenBy.SELF:
        raise ProblemError(
            422, "parent-consent-required", "For minors a parent or guardian must consent"
        )


PUBLIC_PURPOSES = frozenset({ConsentKind.HIGHLIGHTS_PUBLIC, ConsentKind.PUBLIC_PROFILE})


def check_youth_purpose(kind: ConsentKind, youth: bool) -> None:
    """Youth protection (4.9): no public profiles or public highlights in youth teams."""
    if youth and kind in PUBLIC_PURPOSES:
        raise ProblemError(
            403, "youth-protection", "Public profiles and highlights are off for youth players"
        )


async def consented(ctx: Ctx, player_ids: list[uuid.UUID], purpose: ConsentKind) -> set[uuid.UUID]:
    """Players with an unrevoked consent for the purpose (used by highlights, sharing, training)."""
    if not player_ids:
        return set()
    rows = await ctx.db.scalars(
        select(Consent.player_id).where(
            Consent.player_id.in_(player_ids),
            Consent.kind == purpose,
            Consent.revoked_at.is_(None),
        )
    )
    return set(rows.all())


async def revoke_consent(
    ctx: Ctx, team_id: uuid.UUID, player_id: uuid.UUID, consent_id: uuid.UUID
) -> Consent:
    await get_team(ctx, team_id, Action.CONSENT_WRITE)
    await _player_in_team(ctx, team_id, player_id)
    consent = await ctx.db.get(Consent, consent_id)
    if consent is None or consent.player_id != player_id:
        raise ProblemError(404, "not-found", "Consent not found")
    consent.revoked_at = consent.revoked_at or datetime.now(UTC)
    await audit.record(
        ctx,
        "consent.revoked",
        target_type="player",
        target_id=player_id,
        data={"kind": consent.kind},
    )
    return consent
