# aster-engine

Birth chart computation engine built on the Swiss Ephemeris. Facts only, no
interpretation. The computation rules are in [docs/spec.md](docs/spec.md).

## Setup

Requires Python 3.12.

```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e '.[dev]'
```

## Run

```sh
pytest                                # tests
uvicorn aster_engine.api:app --reload # API on http://localhost:8000 (docs at /docs)
```

## API

`POST /natal` computes the whole chart: points, houses, sect, Lots, aspects,
technical analysis, profections and transits, plus every flag and evidence
ID in flat lists.

```sh
curl -s localhost:8000/natal -H 'Content-Type: application/json' -d '{
  "date": "2000-03-15", "time": "14:30",
  "lat": 14.5833, "lon": 121.0,
  "house_system": "placidus",
  "now": "2026-11-06T12:00:00Z"
}'
```

- `date` and `time` are the local clock time at the birth place; the engine
  finds the historical UTC offset from the coordinates.
- `house_system` is `placidus` (default) or `whole_sign`.
- `now` anchors transits and profections. Leave it out to use the time of the
  request; send any other moment to look at another date.
- `fold` (0 or 1) picks the occurrence of a local time that happened twice
  (daylight saving ending).

`GET /health` reports the ephemeris files and versions.

## Deploy

The `Dockerfile` builds a self-contained image with the ephemeris files:

```sh
docker build -t aster-engine .
docker run -p 8000:8000 -e ASTER_API_KEY=change-me aster-engine
```

- `PORT` (default 8000) is the port to listen on; platforms such as Cloud Run
  and Fly.io set it.
- `ASTER_API_KEY`: when set, `POST /natal` requires it in the `X-API-Key`
  header. Leave it unset for local development. `/health` stays open for
  health checks. Prefer running the engine on a private network as well, so
  only the app's backend can reach it.
- As AGPL-3.0 software served over a network, a deployment must offer its
  users the source it runs. Deploy only code that is in this public repo.

## Ephemeris

Ephemeris files are committed in [ephe/](ephe/). Set `ASTER_EPHE_PATH` to use
another directory. The engine never falls back to approximated positions: a
missing file raises an error that names it.

## License

AGPL-3.0, as required by the Swiss Ephemeris.
