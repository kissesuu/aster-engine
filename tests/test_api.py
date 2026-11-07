from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from aster_engine.api import app

client = TestClient(app)
MANILA_2000 = {"date": "2000-03-15", "time": "14:30", "lat": 14.583333, "lon": 121.0}
NOW = "2026-11-06T12:00:00Z"


def test_health():
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["ephemeris"]["coverage"] == "1800-2399"


@pytest.fixture(scope="module")
def chart():
    r = client.post("/natal", json={**MANILA_2000, "now": NOW})
    assert r.status_code == 200
    return r.json()


def test_natal_sections(chart):
    assert list(chart) == [
        "birth",
        "latitude",
        "longitude",
        "points",
        "houses",
        "point_houses",
        "sect",
        "lots",
        "aspects",
        "analysis",
        "profections",
        "transits",
        "flags",
        "evidence",
        "computation",
    ]


def test_natal_values(chart):
    assert chart["birth"]["utc"] == "2000-03-15T06:30:00+00:00"
    sun = chart["points"]["points"][0]
    assert (sun["id"], sun["position"]["sign"], sun["position"]["degree"]) == ("sun", "pisces", 24)
    assert chart["houses"]["system"] == "placidus"
    assert chart["sect"]["kind"] == "day"
    assert chart["lots"][0]["formula"] == "day: ASC + Moon − Sun"
    assert chart["analysis"]["chart_ruler"]["planet"] == "sun"
    assert chart["profections"][0]["lord"] == "venus"
    assert chart["transits"]["now"] == "2026-11-06T12:00:00+00:00"
    assert len(chart["transits"]["past"]) == 15


def test_evidence_collects_every_section(chart):
    evidence = set(chart["evidence"])
    for id in (
        "sun_sign_pisces",
        "sun_house_8",
        "asc_sign_leo",
        "sect_day",
        "lot_fortune_sign_sagittarius",
        "jupiter_neptune_square",
        "venus_jupiter_mutual_reception_domicile",
        "lunar_phase_first_quarter",
        "stellium_sign_pisces",
        "lord_of_year_age_26_venus",
        "transit_saturn_conjunction_sun_2025_03",
    ):
        assert id in evidence, id
    assert len(chart["evidence"]) == len(evidence)


def test_computation_notes(chart):
    notes = chart["computation"]
    assert notes["house_system_used"] == "placidus"
    assert notes["lots"]["lot_wealth"].startswith("ASC + 2nd cusp")
    assert notes["skipped_points"] == []


def test_now_defaults_to_the_request_time():
    before = datetime.now(UTC)
    body = client.post("/natal", json=MANILA_2000).json()
    now = datetime.fromisoformat(body["transits"]["now"])
    assert before - timedelta(seconds=1) <= now <= datetime.now(UTC)


def test_whole_sign_and_polar_flags():
    body = client.post(
        "/natal",
        json={"date": "1990-12-01", "time": "12:00", "lat": 69.6667, "lon": 18.9667, "now": NOW},
    ).json()
    assert body["houses"]["system"] == "porphyry"
    assert "placidus_unavailable_high_latitude" in body["flags"]
    assert "sect_formula_disagrees_high_latitude" in body["flags"]
    ws = client.post("/natal", json={**MANILA_2000, "house_system": "whole_sign", "now": NOW})
    assert ws.json()["houses"]["system"] == "whole_sign"


@pytest.mark.parametrize(
    "body,message",
    [
        ({**MANILA_2000, "date": "1700-01-01"}, "does not cover this date"),
        ({**MANILA_2000, "house_system": "porphyry"}, "placidus or whole_sign"),
        ({**MANILA_2000, "now": "2026-01-01T00:00:00"}, "time zone"),
        ({**MANILA_2000, "now": "1999-01-01T00:00:00Z"}, "before the birth date"),
        ({**MANILA_2000, "lat": 99}, "less than or equal to 90"),
    ],
)
def test_bad_requests(body, message):
    r = client.post("/natal", json=body)
    assert r.status_code == 422
    assert message in str(r.json()["detail"])


def test_api_key_required_when_configured(monkeypatch):
    monkeypatch.setenv("ASTER_API_KEY", "s3cret")
    body = {**MANILA_2000, "now": NOW}
    assert client.post("/natal", json=body).status_code == 401
    assert client.post("/natal", json=body, headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.post("/natal", json=body, headers={"X-API-Key": "s3cret"}).status_code == 200
    assert client.get("/health").status_code == 200  # stays open


def test_no_api_key_needed_when_not_configured(monkeypatch):
    monkeypatch.delenv("ASTER_API_KEY", raising=False)
    assert client.post("/natal", json={**MANILA_2000, "now": NOW}).status_code == 200
