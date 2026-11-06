"""Load Astro.com reference charts from tests/fixtures/."""

import json
from datetime import datetime
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"

PLANET_TOLERANCE = 1 / 60  # 1 arcminute, in degrees
ANGLE_TOLERANCE = 2 / 60  # 2 arcminutes, for angles and house cusps


def load_charts() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(FIXTURES.glob("*.json"))]


def chart_id(chart: dict) -> str:
    return f"{chart['birth']['place'].split(',')[0]} {chart['birth']['date']}"


def local_datetime(chart: dict) -> datetime:
    b = chart["birth"]
    return datetime.strptime(f"{b['date']} {b['time'].replace('.', '')}", "%d %B %Y %I:%M %p")


def angle_diff(a: float, b: float) -> float:
    """Signed smallest difference a - b, in degrees."""
    return (a - b + 180) % 360 - 180
