import pytest

from aster_engine.zodiac import SignPosition, sign_position


@pytest.mark.parametrize(
    "lon,expected",
    [
        (0.0, SignPosition("aries", 0, 0, 0)),
        (330 + 24 + 58 / 60 + 56.5 / 3600, SignPosition("pisces", 24, 58, 56)),
        (360.0, SignPosition("aries", 0, 0, 0)),
        (-30.0, SignPosition("pisces", 0, 0, 0)),
        # Truncated, never rounded across the sign boundary.
        (29.99999, SignPosition("aries", 29, 59, 59)),
    ],
)
def test_sign_position(lon, expected):
    assert sign_position(lon) == expected
