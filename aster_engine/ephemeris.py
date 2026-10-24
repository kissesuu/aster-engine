"""Swiss Ephemeris access with a hard no-approximation guarantee.

pyswisseph silently falls back to the Moshier approximation when a file is
missing. Every body calculation in this package goes through `calc_body`,
which rejects any result not computed from the Swiss Ephemeris files and
raises an error that names the missing file instead.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import swisseph as swe

DEFAULT_EPHE_PATH = Path(__file__).resolve().parent.parent / "ephe"

# The bundled files cover 1800-01-01 to 2399-12-31.
COVERAGE = "1800-2399"

# Without these no chart can be computed at all.
REQUIRED_FILES = ("sepl_18.se1", "semo_18.se1")
# Without these, only the bodies that depend on them are skipped.
OPTIONAL_FILES = ("seas_18.se1", "seorbel.txt", "ast0/se00010s.se1")


@dataclass(frozen=True)
class Body:
    id: str
    swe_id: int
    file: str | None  # None: computed analytically, no file needed


BODIES: dict[str, Body] = {
    b.id: b
    for b in (
        Body("sun", swe.SUN, "sepl_18.se1"),
        Body("moon", swe.MOON, "semo_18.se1"),
        Body("mercury", swe.MERCURY, "sepl_18.se1"),
        Body("venus", swe.VENUS, "sepl_18.se1"),
        Body("mars", swe.MARS, "sepl_18.se1"),
        Body("jupiter", swe.JUPITER, "sepl_18.se1"),
        Body("saturn", swe.SATURN, "sepl_18.se1"),
        Body("uranus", swe.URANUS, "sepl_18.se1"),
        Body("neptune", swe.NEPTUNE, "sepl_18.se1"),
        Body("pluto", swe.PLUTO, "sepl_18.se1"),
        Body("mean_node", swe.MEAN_NODE, None),
        Body("lilith", swe.MEAN_APOG, None),
        Body("chiron", swe.CHIRON, "seas_18.se1"),
        Body("ceres", swe.CERES, "seas_18.se1"),
        Body("pallas", swe.PALLAS, "seas_18.se1"),
        Body("juno", swe.JUNO, "seas_18.se1"),
        Body("vesta", swe.VESTA, "seas_18.se1"),
        Body("hygiea", swe.AST_OFFSET + 10, "ast0/se00010s.se1"),
        Body("cupido", swe.CUPIDO, "seorbel.txt"),
    )
}


class EphemerisFileMissing(RuntimeError):
    """A Swiss Ephemeris file needed for a calculation is not available."""

    def __init__(self, file: str, body: str | None = None, detail: str | None = None):
        self.file = file
        self.body = body
        msg = f"Ephemeris file '{file}' is missing"
        if body:
            msg += f" (needed for {body})"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


def ephe_path() -> Path:
    """The ephemeris directory: $ASTER_EPHE_PATH if set, else the bundled ephe/."""
    env = os.environ.get("ASTER_EPHE_PATH")
    return Path(env) if env else DEFAULT_EPHE_PATH


def missing_files(path: Path | None = None) -> list[str]:
    """Required and optional files that are not present in the ephemeris directory."""
    path = path or ephe_path()
    return [f for f in REQUIRED_FILES + OPTIONAL_FILES if not (path / f).is_file()]


def check_required(path: Path | None = None) -> None:
    """Raise if a file that every chart needs is missing."""
    path = path or ephe_path()
    for f in REQUIRED_FILES:
        if not (path / f).is_file():
            raise EphemerisFileMissing(f, detail=f"not found in {path}")


_active_path: str | None = None


def _use_path(path: Path) -> None:
    # swe keeps the path as process-wide state; only reset it when it changes.
    global _active_path
    p = str(path)
    if p != _active_path:
        swe.set_ephe_path(p)
        _active_path = p


def calc_body(jd_ut: float, body: str, path: Path | None = None) -> tuple[float, ...]:
    """Tropical ecliptic position and speed of `body` at `jd_ut`.

    Returns (longitude, latitude, distance, lon_speed, lat_speed, dist_speed).
    Raises EphemerisFileMissing rather than return an approximated position.
    """
    b = BODIES[body]
    path = path or ephe_path()
    if b.file and not (path / b.file).is_file():
        raise EphemerisFileMissing(b.file, body, f"not found in {path}")
    _use_path(path)
    try:
        xx, retflag = swe.calc_ut(jd_ut, b.swe_id, swe.FLG_SWIEPH | swe.FLG_SPEED)
    except swe.Error as e:
        # Raised e.g. for dates outside the bundled files' coverage.
        raise EphemerisFileMissing(b.file or "unknown", body, str(e)) from e
    if not retflag & swe.FLG_SWIEPH:
        raise EphemerisFileMissing(
            b.file or "unknown",
            body,
            f"Swiss Ephemeris data unavailable for this date (bundled coverage {COVERAGE})",
        )
    return tuple(xx)
