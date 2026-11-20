"""Track identity: jersey numbers to roster players (BRIEF 7.2 stage 6, M5).

Two parts:
- `JerseyReader`: reads a jersey number from player crops. `OnnxJerseyReader` runs any exported digit
  classifier with outputs [batch, 101] (class 100 = "not readable"); weights come from the model registry
  (ADR 003). Without a model nothing is read and identities stay manual.
- `assign_numbers`: turns noisy per-crop readings into one number per track. Greedy assignment in order of
  evidence (summed reading confidence), with the constraints that matter on a handball court:
  * a number belongs to one team (tracks only compete within their team),
  * two tracks that are on court at the same time cannot carry the same number,
  * tracks that never overlap in time (fragments of the same player) may share a number.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from itertools import pairwise
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

from handball_vision.numbers import MIN_CONFIDENCE, split_points, vote
from handball_vision.numbers import Reading as NumberReading
from handball_vision.reid import Fragment, assign, fragment_roles
from handball_vision.teams import TeamAssigner, colour_runs, side_of, team_centres
from handball_vision.tracking import TrackPoint

UNREADABLE = 100


@dataclass(frozen=True)
class Reading:
    track_id: int
    number: int  # 0..99
    confidence: float  # 0..1


@dataclass(frozen=True)
class TrackSpan:
    track_id: int
    team: str | None
    first_ms: int
    last_ms: int


@dataclass(frozen=True)
class Assignment:
    track_id: int
    number: int
    confidence: float
    votes: int


class JerseyReader(Protocol):
    def read(self, crops: list[NDArray[Any]]) -> list[tuple[int, float] | None]: ...


class OnnxJerseyReader:
    """Generic ONNX digit classifier: input [b, 3, h, w] RGB 0..1, output [b, 101] logits."""

    def __init__(self, model_path: Path, size: tuple[int, int] = (64, 64), min_conf: float = 0.5):
        import onnxruntime as ort

        providers = [
            p
            for p in ("CUDAExecutionProvider", "CPUExecutionProvider")
            if p in ort.get_available_providers()
        ]
        self.session = ort.InferenceSession(str(model_path), providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.size = size
        self.min_conf = min_conf

    def read(self, crops: list[NDArray[Any]]) -> list[tuple[int, float] | None]:
        import cv2

        if not crops:
            return []
        batch = np.stack(
            [
                cv2.cvtColor(cv2.resize(c, self.size), cv2.COLOR_BGR2RGB)
                .astype(np.float32)
                .transpose(2, 0, 1)
                / 255.0
                for c in crops
            ]
        )
        (logits,) = self.session.run(None, {self.input_name: batch})[:1]
        e = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs = e / e.sum(axis=1, keepdims=True)
        out: list[tuple[int, float] | None] = []
        for p in probs:
            k = int(p.argmax())
            out.append(None if k == UNREADABLE or p[k] < self.min_conf else (k, float(p[k])))
        return out


def _overlap(a: TrackSpan, b: TrackSpan) -> bool:
    return a.first_ms < b.last_ms and b.first_ms < a.last_ms


def assign_numbers(
    spans: list[TrackSpan], readings: list[Reading], min_votes: int = 3
) -> list[Assignment]:
    """One number per track from noisy readings, respecting team and time-overlap constraints."""
    by_track: dict[int, Counter[int]] = defaultdict(Counter)
    weight: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for r in readings:
        by_track[r.track_id][r.number] += 1
        weight[r.track_id][r.number] += r.confidence
    teams: dict[str | None, list[TrackSpan]] = defaultdict(list)
    for s in spans:
        if sum(by_track[s.track_id].values()) >= min_votes:
            teams[s.team].append(s)

    result: list[Assignment] = []
    for members in teams.values():
        # strongest evidence first: (track, number) pairs ordered by summed confidence. A pair is
        # taken unless the track already has a number or the number is worn by an overlapping track.
        pairs = sorted(
            ((w, s.track_id, n) for s in members for n, w in weight[s.track_id].items()),
            key=lambda p: (-p[0], p[1], p[2]),
        )
        holders: dict[int, list[TrackSpan]] = defaultdict(list)
        done: set[int] = set()
        span = {s.track_id: s for s in members}
        for w, tid, n in pairs:
            if tid in done or any(_overlap(span[tid], o) for o in holders[n]):
                continue
            holders[n].append(span[tid])
            done.add(tid)
            total = sum(weight[tid].values())
            result.append(Assignment(tid, n, round(w / total, 3), by_track[tid][n]))
    result.sort(key=lambda a: a.track_id)
    return result


def to_roster(
    assignments: list[Assignment], roster: dict[int, str], team: Mapping[int, str | None], own: str
) -> dict[int, tuple[str, float]]:
    """Map own-team track numbers to roster player ids: {track_id: (player_id, confidence)}."""
    out = {}
    for a in assignments:
        if team.get(a.track_id) in (own, f"{own}_gk") and a.number in roster:
            out[a.track_id] = (roster[a.number], a.confidence)
    return out


# ---- track identity in the analysis: numbers read on shirts, appearance -----------------------
# (moved from pipeline.py; `NumberReading` is numbers.Reading, a reading of a crop)


def split_by_reading_colour(
    points: list[TrackPoint],
    team_out: dict[int, dict[str, Any]],
    teams: TeamAssigner,
    reads: dict[int, list[NumberReading]],
    framed_items: Sequence[dict[int, list[tuple[int, Any]]]],
    fps: float,
    min_side: int = 2,
) -> tuple[list[TrackPoint], dict[str, int]]:
    """The team of a number is the colour of the shirt it was read on (ADR 027 addendum).

    Every confident reading gets the team of the torso colour sampled on the same crop
    (`teams.side_of` against this match's team colours). A field track whose readings disagree
    with its team label carries a second person for a while (the tracker swapped a white and a
    black player): with `min_side` or more such readings, the track is cut at its colour switches
    (`teams.colour_runs`) and each piece takes the team of its colour; then every reading that
    still disagrees with its track's team is dropped. Goalkeeper and referee tracks are left as
    they are (their kits differ from the teams'). `reads`, the per-track (frame, item) lists in
    `framed_items` (appearance vectors, role samples) and the colour samples in `teams` move to
    the new pieces in place."""
    stats = {"tracks_split": 0, "pieces": 0, "readings_dropped": 0}
    centres = team_centres(team_out, teams.samples)
    if not centres:
        return points, stats
    colour_at = {
        (t, f): c
        for t, cs in teams.samples.items()
        for f, c in zip(teams.frames[t], cs, strict=True)
    }

    def side(t: int, frame: int) -> str | None:
        return side_of(colour_at.get((t, frame)), centres)

    next_id = max([p.track_id for p in points], default=0) + 1
    cuts: dict[int, list[tuple[int, int, int]]] = {}  # track -> [(from, to frame, piece id)]
    for t, rs in reads.items():
        label = str(team_out.get(t, {}).get("label", ""))
        if label not in ("home", "away"):
            continue
        against = [
            r
            for r in rs
            if r.confidence >= MIN_CONFIDENCE and side(t, r.frame) not in (None, label)
        ]
        if len(against) < min_side:
            continue
        runs = colour_runs(teams.frames[t], [side_of(c, centres) for c in teams.samples[t]], fps)
        if len(runs) < 2:
            continue
        edges = [(a + b) // 2 + 1 for (_, a, _), (b, _, _) in pairwise(runs)]
        parent = {
            k: v
            for k, v in team_out[t].items()
            if k not in ("number", "number_confidence", "number_readings")
        }
        pieces = []
        for k, (_, _, run_side) in enumerate(runs):
            nid = t if k == 0 else next_id
            if k:
                pieces.append((edges[k - 1], edges[k] if k < len(edges) else 2**62, nid))
                next_id += 1
            team_out[nid] = (
                dict(parent)
                if run_side == label
                else {**parent, "label": run_side, "label_source": "reading_colour"}
            )
        cuts[t] = pieces
        stats["tracks_split"] += 1
        stats["pieces"] += len(runs)

    def owner(t: int, frame: int) -> int:
        for a, b, nid in cuts.get(t, []):
            if a <= frame < b:
                return nid
        return t

    if cuts:
        moved = {
            t: [(owner(t, f), f, c) for f, c in zip(teams.frames[t], teams.samples[t], strict=True)]
            for t in cuts
        }
        for t, items in moved.items():
            for nid in [t, *(n for _, _, n in cuts[t])]:
                teams.samples[nid], teams.frames[nid] = [], []
            for nid, f, c in items:
                teams.samples[nid].append(c)
                teams.frames[nid].append(f)
            for nid in [t, *(n for _, _, n in cuts[t])]:
                cs = teams.samples[nid]
                if cs:
                    lab = np.median(np.stack(cs), axis=0)
                    team_out[nid].update(lab=[round(float(v), 1) for v in lab], samples=len(cs))
        per_track: list[dict[int, list[Any]]] = [reads, *framed_items]
        for group in per_track:
            for t in [t for t in group if t in cuts]:
                for v in group.pop(t):
                    f = v.frame if isinstance(v, NumberReading) else int(v[0])
                    group.setdefault(owner(t, f), []).append(v)
        points = [replace(p, track_id=owner(p.track_id, p.frame)) for p in points]
        colour_at = {
            (t, f): c
            for t, cs in teams.samples.items()
            for f, c in zip(teams.frames[t], cs, strict=True)
        }
    for t, rs in reads.items():
        label = str(team_out.get(t, {}).get("label", ""))
        if label not in ("home", "away"):
            continue
        keep = [r for r in rs if r.confidence < MIN_CONFIDENCE or side(t, r.frame) in (None, label)]
        stats["readings_dropped"] += len(rs) - len(keep)
        rs[:] = keep
    return points, stats


def _split_at_switches(
    points: list[TrackPoint],
    team_out: dict[int, dict[str, Any]],
    reads: dict[int, list[NumberReading]],
    framed_items: Sequence[dict[int, list[tuple[int, Any]]]] = (),
) -> tuple[
    list[TrackPoint], dict[int, list[NumberReading]], list[dict[int, list[tuple[int, Any]]]]
]:
    """Cut tracks where the shirt numbers say the tracker swapped players; each part becomes its
    own track (same team entry) with its own readings and (frame, item) looks."""
    next_id = max([p.track_id for p in points], default=0) + 1
    cuts: dict[int, list[tuple[int, int]]] = {}  # track -> [(from_frame, new id)]
    out_reads: dict[int, list[NumberReading]] = defaultdict(list)
    for t, rs in reads.items():
        frames = split_points(rs) if t in team_out else []
        bounds = [(f, next_id + k) for k, f in enumerate(frames)]
        next_id += len(frames)
        if bounds:
            cuts[t] = bounds
            for _, nid in bounds:
                team_out[nid] = {
                    k: v
                    for k, v in team_out[t].items()
                    if k not in ("number", "number_confidence", "number_readings")
                }
        for r in rs:
            tid = t
            for f, nid in bounds:
                if r.frame >= f:
                    tid = nid
            out_reads[tid].append(r)

    def owner(t: int, frame: int) -> int:
        tid = t
        for f, nid in cuts.get(t, []):
            if frame >= f:
                tid = nid
        return tid

    out_items: list[dict[int, list[tuple[int, Any]]]] = []
    for items in framed_items:
        moved: dict[int, list[tuple[int, Any]]] = defaultdict(list)
        for t, vs in items.items():
            for f0, v in vs:
                moved[owner(t, f0)].append((f0, v))
        out_items.append(moved)
    if not cuts:
        return points, out_reads, out_items
    return (
        [replace(p, track_id=owner(p.track_id, p.frame)) for p in points],
        out_reads,
        out_items,
    )


MIN_ANCHOR_READINGS = 4


def identify_by_appearance(
    points: list[TrackPoint],
    team_out: dict[int, dict[str, Any]],
    looks: Mapping[int, Sequence[NDArray[np.float64] | tuple[int, NDArray[np.float64]]]],
    fps: float,
    reads: Mapping[int, list[NumberReading]] | None = None,
    roles: Mapping[int, Sequence[tuple[int, NDArray[np.float64]]]] | None = None,
) -> int:
    """Numbers for tracks nobody read a number on, by appearance (reid.py): the numbered tracks of
    this match teach what each player looks like. `looks` is keyed by the final track ids, as
    vectors or (frame, vector); with frames and the tracks' `reads` a numbered track teaches only
    with the vectors next to readings of its number (reid.anchor_vectors), and a track whose own
    readings say otherwise is not given the number (reid.contradicts). With the tracks' `roles`
    ((frame, role probabilities), roles.py) only fragments that look like field players teach or
    are given a number (reid.plays): not referees, goalkeepers, staff or the bench."""
    span: dict[int, list[TrackPoint]] = defaultdict(list)
    for p in points:
        span[p.track_id].append(p)
    frags = []
    for tid, ps in span.items():
        info = team_out.get(tid)
        if info is None or str(info["label"]) == "referee" or len(looks.get(tid, [])) < 3:
            continue
        ps.sort(key=lambda p: p.frame)
        # only well-read numbers teach; a number read a few times may be a misreading (24 for
        # 14) and is checked against the anchors like a track without number
        anchor = int(info.get("number_readings", 0)) >= MIN_ANCHOR_READINGS
        items = looks[tid]
        framed = all(isinstance(v, tuple) for v in items)
        vectors = np.stack([v[1] if isinstance(v, tuple) else v for v in items])
        frames = np.array([v[0] for v in items if isinstance(v, tuple)], np.int64)
        readings = tuple(
            (r.frame, r.number)
            for r in (reads or {}).get(tid, [])
            if r.confidence >= MIN_CONFIDENCE
        )
        number = info.get("number") if anchor else None
        frags.append(
            Fragment(
                tid,
                str(info["label"]),
                ps[0].frame,
                ps[-1].frame,
                (ps[0].x, ps[0].y),
                (ps[-1].x, ps[-1].y),
                vectors,
                number,
                frames if framed and reads is not None else None,
                readings,
                fragment_roles(list((roles or {}).get(tid, [])), readings, number, fps),
            )
        )
    found = assign(frags, fps)
    for tid, number in found.items():
        read = team_out[tid].get("number")
        team_out[tid].update(
            number=number, number_source="read" if read == number else "appearance"
        )
    return len(found)


def merge_by_number(
    points: list[TrackPoint],
    team_out: dict[int, dict[str, Any]],
    reads: dict[int, list[NumberReading]],
    fps: float,
    max_overlap_s: float = 1.0,
    looks: dict[int, list[tuple[int, Any]]] | None = None,
    rosters: dict[str, set[int]] | None = None,
    roles: dict[int, list[tuple[int, Any]]] | None = None,
) -> tuple[list[TrackPoint], int]:
    """Number per track by vote, then one track per player: fragments of the same team with the
    same number that do not overlap in time are joined (the number is the identity the tracker
    loses on occlusions and camera pans). When two fragments with the same number overlap, the one
    with the weaker vote loses its number. Returns the points and the number of joined fragments.

    `rosters` ("home"/"away" -> shirt numbers) restricts each team's votes to its roster (see
    `vote`); a team without roster is voted freely. `reads`, `looks` and `roles` (per-track
    (frame, role probabilities)) are updated in place to the new track ids (cut at switches,
    joined by number)."""
    framed = [d for d in (looks, roles) if d is not None]
    points, split_reads, moved = _split_at_switches(points, team_out, reads, framed)
    reads.clear()
    reads.update(split_reads)
    for d, m in zip(framed, moved, strict=True):
        d.clear()
        d.update(m)
    span: dict[int, tuple[int, int]] = {}
    for p in points:
        a, b = span.get(p.track_id, (p.frame, p.frame))
        span[p.track_id] = (min(a, p.frame), max(b, p.frame))

    def side(t: int) -> str:
        # a number belongs to one person of a team: a "goalkeeper" fragment with a field player's
        # number is the position heuristic being wrong (they still may not overlap in time)
        return str(team_out[t]["label"]).removesuffix("_gk")

    votes = {
        t: v
        for t, rs in reads.items()
        if t in team_out and (v := vote(rs, (rosters or {}).get(side(t)))) is not None
    }
    for t, v in votes.items():
        team_out[t].update(
            number=v.number, number_confidence=v.confidence, number_readings=v.readings
        )

    groups: dict[tuple[str, int], list[int]] = defaultdict(list)
    for t, v in votes.items():
        if side(t) != "referee":
            groups[(side(t), v.number)].append(t)
    max_overlap = max_overlap_s * fps  # frames
    rename: dict[int, int] = {}
    for tids in groups.values():
        tids.sort(key=lambda t: -votes[t].confidence * votes[t].readings)
        chains: list[list[int]] = []
        for t in tids:
            a, b = span[t]
            for chain in chains:
                clash = any(min(b, span[c][1]) - max(a, span[c][0]) > max_overlap for c in chain)
                if not clash:
                    chain.append(t)
                    break
            else:
                if chains:  # overlaps the stronger fragment: its number is the misreading
                    for k in ("number", "number_confidence", "number_readings"):
                        team_out[t].pop(k, None)
                    continue
                chains.append([t])
        for chain in chains:
            head = min(chain, key=lambda c: span[c][0])
            for c in chain:
                if c != head:
                    rename[c] = head
    if not rename:
        return points, 0
    for old, new in rename.items():
        for d in framed:
            if old in d:
                d.setdefault(new, []).extend(d.pop(old))
        if old in reads:
            reads.setdefault(new, []).extend(reads.pop(old))
        keep, gone = team_out[new], team_out.pop(old)
        if span[old][1] - span[old][0] > span[new][1] - span[new][0]:
            keep["label"] = gone["label"]  # the longer fragment knows the role better
        if int(gone.get("number_readings", 0)) > int(keep.get("number_readings", 0)):
            for k in ("number_confidence", "number_readings"):
                keep[k] = gone[k]
        keep["samples"] = int(keep.get("samples", 0)) + int(gone.get("samples", 0))
        keep["merged_from"] = [*keep.get("merged_from", []), old]
    out = [
        TrackPoint(
            rename.get(p.track_id, p.track_id),
            p.frame,
            p.x,
            p.y,
            p.vx,
            p.vy,
            p.observed,
            p.det_index,
        )
        for p in points
    ]
    # the same frame twice in one track (rounding at the joins): keep the observed point
    seen: dict[tuple[int, int], TrackPoint] = {}
    for p in out:
        key = (p.track_id, p.frame)
        if key not in seen or (p.observed and not seen[key].observed):
            seen[key] = p
    return sorted(seen.values(), key=lambda p: (p.frame, p.track_id)), len(rename)
