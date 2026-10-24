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
uvicorn aster_engine.api:app --reload # API (needs `pip install uvicorn`)
```

## Ephemeris

Ephemeris files are committed in [ephe/](ephe/). Set `ASTER_EPHE_PATH` to use
another directory. The engine never falls back to approximated positions: a
missing file raises an error that names it.

## License

AGPL-3.0, as required by the Swiss Ephemeris.
