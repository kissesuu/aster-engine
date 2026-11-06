"""HTTP API. Chart endpoints are added as features land."""

from fastapi import FastAPI

from . import __version__
from .ephemeris import COVERAGE, REQUIRED_FILES, ephe_path, missing_files
from .timeutil import TZDATA_VERSION

app = FastAPI(title="aster-engine", version=__version__)


@app.get("/health")
def health() -> dict:
    missing = missing_files()
    return {
        "status": "error" if any(f in REQUIRED_FILES for f in missing) else "ok",
        "version": __version__,
        "ephemeris": {"path": str(ephe_path()), "coverage": COVERAGE, "missing": missing},
        "tzdata": TZDATA_VERSION,
    }
