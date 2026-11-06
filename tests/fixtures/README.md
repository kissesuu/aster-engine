# Reference fixtures

Reference charts from Astro.com ("Natal Chart (Data Sheet)", Web Style),
retrieved 6 Nov 2026. Only the values are stored here, not the PDFs.

| File | Birth | Notes |
|---|---|---|
| `manila_2000-03-15.json` | 15 Mar 2000, 2:30 p.m., Manila | Day chart; Mercury and Pluto stationary |
| `manila_1990-03-15.json` | 15 Mar 1990, 11:00 p.m., Manila | Night chart |
| `manila_1978-06-15.json` | 15 Jun 1978, 10:00 a.m., Manila | |
| `manila_1943-05-10.json` | 10 May 1943, 8:00 a.m., Manila | JST (UTC+9); UT is the previous day |
| `tromso_1990-12-01.json` | 1 Dec 1990, 12:00 p.m., Tromsø | Placidus impossible; Astro.com fell back to Porphyry |

Tolerance (see CLAUDE.md): 1 arcminute for planets, 2 arcminutes for angles
and house cusps.

## Format

- `birth.lat` / `birth.lon` are the coordinates Astro.com used, which it shows
  rounded to the arcminute (`coords_as_shown`). Tests must use these, not more
  precise coordinates for the city.
- `bodies.<id>.longitude` is the tropical longitude in degrees, from the
  sign/degree/minute/second shown.
- `bodies.<id>.marker` is the symbol Astro.com prints after the position:
  `#` retrograde, `(` stationary turning direct, `)` stationary turning
  retrograde, `D` direct (True Node only). Retrograde status in tests comes
  from the sign of `speed`.
- `cusps."1"` to `cusps."12"`: house cusps in the chart's `house_system`
  (cusp 1 = ASC, 4 = IC, 7 = DSC, 10 = MC).
- `julian_day_tt` and `delta_t_sec` are as printed by Astro.com.
