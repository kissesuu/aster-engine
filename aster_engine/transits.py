"""Transits to the natal chart (spec COMPUTATION step 6a-f)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .analysis import ChartRuler
from .ephemeris import calc_body
from .houses import Houses
from .points import Point
from .profections import ProfectionYear
from .timeutil import jd_to_utc, julian_day_ut

# Transiting body id -> ephemeris body id.
TRANSITING = {
    "jupiter": "jupiter",
    "saturn": "saturn",
    "uranus": "uranus",
    "neptune": "neptune",
    "pluto": "pluto",
    "north_node": "mean_node",
    "chiron": "chiron",
}
# Upper bound on each body's speed in longitude (degrees/day), used to skip
# quickly through dates far from any aspect without stepping over one.
MAX_SPEED = {
    "jupiter": 0.3,
    "saturn": 0.15,
    "uranus": 0.07,
    "neptune": 0.05,
    "pluto": 0.05,
    "north_node": 0.07,
    "chiron": 0.2,
}
# Aspect -> the angles it can be from the natal point.
ASPECT_ANGLES = {
    "conjunction": (0.0,),
    "opposition": (180.0,),
    "square": (90.0, -90.0),
    "trine": (120.0, -120.0),
}
NATAL_TARGETS = ("sun", "moon", "asc", "mc", "mercury", "venus", "mars", "jupiter", "saturn")

ORB = 1.0
YEARS = 15
MERGE_GAP_DAYS = 365.25
PAST_LIMIT = 15
UPCOMING_LIMIT = 20
_PRECISION = 1 / 1440  # one minute


@dataclass(frozen=True)
class Target:
    id: str
    longitude: float
    roles: tuple[str, ...]  # "chart_ruler", "lord_of_year"


@dataclass(frozen=True)
class TransitWindow:
    body: str
    aspect: str
    angle: float  # transiting minus natal at exact: 0, 180, ±90 or ±120
    target: str
    target_roles: tuple[str, ...]
    start: datetime  # first entry into orb
    end: datetime  # last exit from orb
    exact: tuple[datetime, ...]  # every exact hit, in order
    passes: int
    status: str  # "past", "active", "upcoming"
    in_orb_now: bool
    starts_before_scan: bool  # already in orb when the scan begins
    ends_after_scan: bool  # still in orb when the scan ends
    priority: tuple[int, int, int]  # lower is more important
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class Transits:
    now: datetime
    active: tuple[TransitWindow, ...]
    past: tuple[TransitWindow, ...]
    upcoming: tuple[TransitWindow, ...]


def targets(
    points: tuple[Point, ...], houses: Houses, chart_ruler: ChartRuler, lord: ProfectionYear
) -> tuple[Target, ...]:
    lon = {p.id: p.longitude for p in points}
    lon["asc"] = houses.angle("asc").longitude
    lon["mc"] = houses.angle("mc").longitude
    # Traditional rulers are always among the natal targets already.
    result = []
    for id in NATAL_TARGETS:
        roles = []
        if id == chart_ruler.planet:
            roles.append("chart_ruler")
        if id == lord.lord:
            roles.append("lord_of_year")
        result.append(Target(id, lon[id], tuple(roles)))
    return tuple(result)


def _offset(jd: float, body: str, natal: float, angle: float, ephe: Path | None) -> float:
    """Signed distance of the transiting body from the exact aspect, degrees."""
    lon = calc_body(jd, TRANSITING[body], ephe)[0]
    return (lon - natal - angle + 180) % 360 - 180


def _bisect(f, lo: float, hi: float) -> float:
    """Root of f between lo and hi, where f changes sign."""
    flo = f(lo)
    while hi - lo > _PRECISION:
        mid = (lo + hi) / 2
        fmid = f(mid)
        if (fmid <= 0) == (flo <= 0):
            lo, flo = mid, fmid
        else:
            hi = mid
    return (lo + hi) / 2


@dataclass
class _Pass:
    start: float
    end: float
    exact: list[float]
    open_start: bool
    open_end: bool


def _scan(body, natal, angle, t0, t1, ephe) -> list[_Pass]:
    """Passes through the orb between t0 and t1 (Julian days, UT).

    Within 2 orbs of the aspect the scan steps one day, less than the orb any
    of these bodies can cover, so no entry, exit or exact hit is stepped over.
    Farther out it jumps ahead by as much as the body could not close.
    """

    def off(t):
        return _offset(t, body, natal, angle, ephe)

    def outside(t):
        return abs(off(t)) - ORB  # <= 0 inside the orb

    passes: list[_Pass] = []
    current = _Pass(t0, t1, [], True, False) if abs(off(t0)) <= ORB else None
    t, d = t0, off(t0)
    while t < t1:
        far = abs(d) - 2 * ORB
        t_next = min(t + (max(1.0, far / MAX_SPEED[body]) if far > 0 else 1.0), t1)
        d_next = off(t_next)
        inside, inside_next = abs(d) <= ORB, abs(d_next) <= ORB
        if not inside and inside_next:
            current = _Pass(_bisect(outside, t, t_next), t1, [], False, False)
        if abs(d) <= ORB and abs(d_next) <= ORB and (d <= 0) != (d_next <= 0):
            current.exact.append(_bisect(off, t, t_next))
        if inside and not inside_next:
            current.end = _bisect(outside, t, t_next)
            passes.append(current)
            current = None
        t, d = t_next, d_next
    if current is not None:
        current.open_end = True
        passes.append(current)
    return passes


def _merge(passes: list[_Pass]) -> list[list[_Pass]]:
    groups: list[list[_Pass]] = []
    for p in passes:
        if groups and p.start - groups[-1][-1].end < MERGE_GAP_DAYS:
            groups[-1].append(p)
        else:
            groups.append([p])
    return groups


def _priority(body: str, aspect: str, target: Target) -> tuple[int, int, int]:
    if target.id in ("asc", "mc", "sun", "moon"):
        target_rank = 0
    elif target.roles:
        target_rank = 1
    else:
        target_rank = 2
    aspect_rank = 0 if aspect in ("conjunction", "opposition") else 1
    body_rank = 0 if body in ("saturn", "uranus", "neptune", "pluto") else 1
    return (target_rank, aspect_rank, body_rank)


def transit_windows(
    targets_: tuple[Target, ...], now: datetime, ephe: Path | None = None
) -> tuple[TransitWindow, ...]:
    """Every transit window within 15 years before and after `now` (UTC)."""
    jd_now = julian_day_ut(now)
    t0, t1 = jd_now - YEARS * 365.25, jd_now + YEARS * 365.25
    windows = []
    for body in TRANSITING:
        for target in targets_:
            for aspect, angles in ASPECT_ANGLES.items():
                for angle in angles:
                    for group in _merge(_scan(body, target.longitude, angle, t0, t1, ephe)):
                        windows.append(_window(body, aspect, angle, target, group, jd_now))
    return tuple(windows)


def _window(body, aspect, angle, target: Target, group: list[_Pass], jd_now: float):
    start, end = group[0].start, group[-1].end
    if end < jd_now:
        status = "past"
    elif start > jd_now:
        status = "upcoming"
    else:
        status = "active"
    start_dt = jd_to_utc(start)
    return TransitWindow(
        body=body,
        aspect=aspect,
        angle=angle,
        target=target.id,
        target_roles=target.roles,
        start=start_dt,
        end=jd_to_utc(end),
        exact=tuple(jd_to_utc(e) for p in group for e in p.exact),
        passes=len(group),
        status=status,
        in_orb_now=any(p.start <= jd_now <= p.end for p in group),
        starts_before_scan=group[0].open_start,
        ends_after_scan=group[-1].open_end,
        priority=_priority(body, aspect, target),
        evidence=(f"transit_{body}_{aspect}_{target.id}_{start_dt:%Y_%m}",),
    )


def select(windows: tuple[TransitWindow, ...], now: datetime) -> Transits:
    """All active windows, the most important past and upcoming ones, by date."""

    def chronological(ws):
        return tuple(sorted(ws, key=lambda w: (w.start, w.body, w.target, w.aspect)))

    active = [w for w in windows if w.status == "active"]
    past = sorted(
        (w for w in windows if w.status == "past"),
        key=lambda w: (w.priority, -w.end.timestamp()),  # ties: most recent first
    )[:PAST_LIMIT]
    upcoming = sorted(
        (w for w in windows if w.status == "upcoming"),
        key=lambda w: (w.priority, w.start.timestamp()),  # ties: soonest first
    )[:UPCOMING_LIMIT]
    return Transits(now, chronological(active), chronological(past), chronological(upcoming))


def compute_transits(
    targets_: tuple[Target, ...], now: datetime, ephe: Path | None = None
) -> Transits:
    """Transits around `now` (a UTC datetime), filtered as the spec requires."""
    return select(transit_windows(targets_, now, ephe), now)
