import pytest

from aster_engine import ephemeris


@pytest.fixture(autouse=True)
def _restore_ephe_path():
    yield
    ephemeris._use_path(ephemeris.ephe_path())
