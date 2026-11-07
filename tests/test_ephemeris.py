import pytest
import swisseph as swe

from aster_engine.ephemeris import (
    BODIES,
    REQUIRED_FILES,
    EphemerisFileMissing,
    calc_body,
    check_required,
    ephe_path,
    missing_files,
)

J2000 = 2451545.0


def test_required_files_are_bundled():
    check_required()
    assert not any(f in REQUIRED_FILES for f in missing_files())


def test_check_required_names_the_file(tmp_path):
    with pytest.raises(EphemerisFileMissing, match="sepl_18.se1"):
        check_required(tmp_path)


def test_missing_files_lists_everything_in_empty_dir(tmp_path):
    assert set(missing_files(tmp_path)) >= set(REQUIRED_FILES)


@pytest.mark.parametrize(
    "body", [b for b, v in BODIES.items() if v.file and (ephe_path() / v.file).is_file()]
)
def test_bundled_bodies_compute_from_swiss_ephemeris(body):
    lon, lat, dist, speed, *_ = calc_body(J2000, body)
    assert 0 <= lon < 360


@pytest.mark.parametrize(
    "body,file",
    [
        ("mars", "sepl_18.se1"),
        ("moon", "semo_18.se1"),
        ("chiron", "seas_18.se1"),
        ("cupido", "seorbel.txt"),
    ],
)
def test_missing_file_raises_instead_of_approximating(tmp_path, body, file):
    # swe on its own would silently fall back to Moshier here.
    with pytest.raises(EphemerisFileMissing, match=file) as exc:
        calc_body(J2000, body, tmp_path)
    assert exc.value.file == file
    assert exc.value.body == body


def test_hygiea_after_its_file_coverage_raises():
    # ast0/se00010s.se1 ends in 2102, earlier than the planet files.
    with pytest.raises(EphemerisFileMissing, match="se00010s.se1"):
        calc_body(swe.julday(2150, 1, 1, 12.0), "hygiea")


@pytest.mark.parametrize("year", [1700, 2450])
def test_dates_outside_bundled_coverage_raise(year):
    with pytest.raises(EphemerisFileMissing):
        calc_body(swe.julday(year, 6, 1, 12.0), "mars")


def test_calc_body_works_on_a_new_thread():
    # swe's ephemeris path is per thread; a thread that never set it must not
    # end up without files (and so raise) after another thread set it.
    from concurrent.futures import ThreadPoolExecutor

    calc_body(J2000, "sun")
    with ThreadPoolExecutor(max_workers=1) as pool:
        lon = pool.submit(calc_body, J2000, "sun").result()[0]
    assert lon == pytest.approx(calc_body(J2000, "sun")[0])
