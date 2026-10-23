# aster-engine

Computation engine for a birth chart app. Facts only, no interpretation.
Spec: docs/spec.md (the COMPUTATION section is the source of truth).

## Stack
- Python 3.12, FastAPI, pyswisseph, pytest
- Package name: `aster_engine`
- Tropical zodiac

## Rules
- Never estimate positions. If an ephemeris file is missing, raise a clear error
  that names the file. Never fall back to approximations.
- Ephemeris files live in ephe/ and are committed to the repo.
- Birth time → UTC with zoneinfo + timezonefinder. Historical offsets matter,
  especially old Philippine dates.
- House system is a user input: Placidus or Whole Sign. Flag when Placidus
  cannot be computed (high latitude).
- Orbs, Lot formulas, sect rule, and transit filters must match docs/spec.md
  exactly. If the spec is ambiguous, ask instead of guessing.
- Lots use traditional rulers only. Lot of Wealth always uses the Whole Sign
  2nd house, regardless of the chosen house system.
- Every computed factor gets a stable evidence ID, e.g. `mars_sign_cancer`,
  `sun_house_10`, `mars_jupiter_square`, `lot_fortune_sign_leo`.
- Every Lot in the output includes the formula string used.
- Keep functions pure: input → output, no global state except the ephe path.

## Testing
- Every feature ships with pytest tests.
- Reference values live in tests/fixtures/ (from Astro.com).
- Tolerance: 1 arcminute for planets, 2 arcminutes for angles and house cusps.
- Run the full test suite before finishing a task.

## Licensing
- This repo is AGPL-3.0 (required by Swiss Ephemeris / pyswisseph).
- No interpretation, scoring, or prompts here. Those live in a separate private
  repo that talks to this engine over HTTP only.
