"""Tropical zodiac signs and longitude formatting."""

from __future__ import annotations

from dataclasses import dataclass

SIGNS = (
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
)


def norm(x: float) -> float:
    """Angle in [0, 360)."""
    return x % 360.0


@dataclass(frozen=True)
class SignPosition:
    sign: str
    degree: int  # 0-29, within the sign
    minute: int
    second: int  # truncated, so the shown position never crosses into the next sign


def sign_position(longitude: float) -> SignPosition:
    lon = norm(longitude)
    sign_index = int(lon // 30)
    total = int((lon - sign_index * 30) * 3600)
    return SignPosition(SIGNS[sign_index], total // 3600, total // 60 % 60, total % 60)
