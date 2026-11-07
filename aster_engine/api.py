"""HTTP API."""

import datetime as dt
import os
import secrets
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from . import __version__
from .chart import natal_chart
from .ephemeris import COVERAGE, REQUIRED_FILES, EphemerisFileMissing, ephe_path, missing_files
from .houses import HouseSystem
from .timeutil import TZDATA_VERSION, TimezoneNotFound

app = FastAPI(title="aster-engine", version=__version__)


def require_api_key(x_api_key: str | None = Header(None)) -> None:
    """When ASTER_API_KEY is set, chart endpoints need it in the X-API-Key header.

    Leave it unset for local development. /health stays open for platform
    health checks.
    """
    expected = os.environ.get("ASTER_API_KEY")
    if expected and not (x_api_key and secrets.compare_digest(x_api_key, expected)):
        raise HTTPException(401, "missing or invalid X-API-Key")


class NatalRequest(BaseModel):
    date: dt.date = Field(description="Local birth date")
    time: dt.time = Field(description="Local birth time (clock time at the birth place)")
    lat: float = Field(ge=-90, le=90, description="Birth latitude, north positive")
    lon: float = Field(ge=-180, le=180, description="Birth longitude, east positive")
    house_system: HouseSystem = HouseSystem.PLACIDUS
    fold: int = Field(0, ge=0, le=1, description="Which occurrence of an ambiguous local time")
    now: datetime | None = Field(
        None, description="Moment for transits and profections; defaults to the request time"
    )


@app.get("/health")
def health() -> dict:
    missing = missing_files()
    return {
        "status": "error" if any(f in REQUIRED_FILES for f in missing) else "ok",
        "version": __version__,
        "ephemeris": {"path": str(ephe_path()), "coverage": COVERAGE, "missing": missing},
        "tzdata": TZDATA_VERSION,
    }


@app.post("/natal", dependencies=[Depends(require_api_key)])
def natal(req: NatalRequest) -> dict:
    if req.house_system is HouseSystem.PORPHYRY:
        raise HTTPException(422, "house_system must be placidus or whole_sign")
    now = req.now or datetime.now(UTC)
    if now.tzinfo is None:
        raise HTTPException(422, "now must include a time zone, e.g. 2026-11-06T12:00:00Z")
    try:
        chart = natal_chart(
            datetime.combine(req.date, req.time),
            req.lat,
            req.lon,
            req.house_system,
            now.astimezone(UTC),
            req.fold,
        )
    except EphemerisFileMissing as e:
        # A bundled file that does not cover the date is the caller's problem;
        # a file missing from the server is ours.
        status = 422 if (ephe_path() / e.file).is_file() else 500
        raise HTTPException(status, str(e)) from e
    except (TimezoneNotFound, ValueError) as e:
        raise HTTPException(422, str(e)) from e
    return jsonable_encoder(chart)
