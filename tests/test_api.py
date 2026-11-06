from fastapi.testclient import TestClient

from aster_engine.api import app


def test_health():
    body = TestClient(app).get("/health").json()
    assert body["status"] == "ok"
    assert body["ephemeris"]["coverage"] == "1800-2399"
