# Birth Chart Spec (Computation)

The COMPUTATION section is the source of truth for aster-engine.
BIRTH DATA describes the engine's input. Output formatting and interpretation
are out of scope for this repo.

```
BIRTH DATA
- Date:
- Time:
- Place: (gamitin ang local timezone ng lugar at petsa para i-convert sa UT)
  Bago nagkaroon ng standard time (LMT sa timezone database), gamitin ang
  local mean time ng mismong birthplace: longitude / 15 na oras.
- House system: Placidus o Whole Sign (pumili ng isa). Kapag hindi ma-compute
  ang Placidus (high latitude), i-flag at awtomatikong gamitin ang Porphyry.
- Current date (para sa timing):

COMPUTATION (dapat accurate, huwag mag-estimate mula sa memory)
1. Gamitin ang Swiss Ephemeris (pyswisseph). Kung mag-fail ang install, gumawa ng
   fresh venv at i-upgrade muna ang pip/setuptools/wheel bago i-install.
2. I-download ang ephemeris files mula sa github.com/aloistr/swisseph (ephe folder)
   at i-set ang ephe path:
   - sepl_18.se1, semo_18.se1, seas_18.se1, seorbel.txt
   - ast0/se00010s.se1 (para kay Hygiea)
   Kung hindi ma-download ang isang file, sabihin kung alin at laktawan ang body na
   nakadepende dito. Huwag mag-estimate.
3. I-compute, tropical zodiac, gamit ang napiling house system:
   - Planets: Sun hanggang Pluto (+ retrograde status)
     Stationary: Mercury hanggang Pluto, at Chiron. Hanapin ang eksaktong station (speed
     = 0) na pinakamalapit sa birth. Stationary kapag nasa loob ng: Mercury ±2
     araw, Venus at Mars ±3, Jupiter at Saturn ±5, Uranus, Neptune, Pluto at Chiron ±7.
     Stationary direct kapag retrograde → direct, stationary retrograde kapag
     direct → retrograde. Ibigay ang petsa ng station at layo nito sa birth.
   - Mean North/South Node, Chiron
   - Ceres, Pallas, Juno, Vesta, Hygiea
   - Lilith (mean Black Moon), Cupido (Uranian, mula sa seorbel.txt)
   - ASC, MC, Vertex
   - Sect: day chart kapag nasa itaas ng horizon ang Sun (tunay na altitude > 0°,
     walang refraction). Kung hindi, night chart. Sa karaniwang latitude, pareho
     ito ng norm(Sun − ASC) > 180° (houses 7-12). I-flag kapag nasa loob ng 1° ng
     ASC o DSC ang Sun, dahil unstable ang sect at pwedeng magbago kapag mali ng
     ilang minuto ang birth time. I-flag din kapag hindi magkatugma ang altitude
     at ang norm(Sun − ASC) formula (nangyayari sa polar latitudes, kung saan
     nagkakapalit ang ASC at DSC).
   - Lots (iisang sect ang gamit ng lahat; norm = x mod 360):
     * Fortune: day ASC + Moon − Sun; night ASC + Sun − Moon
     * Spirit: day ASC + Sun − Moon; night ASC + Moon − Sun
     * Victory: day ASC + Jupiter − Spirit; night ASC + Spirit − Jupiter
     * Wealth (Substance): ASC + (2nd house cusp) − (traditional ruler ng 2nd
       house), walang day/night reversal. Laging Whole Sign ang 2nd house dito
       (cusp = 0° ng 2nd sign mula sa ASC sign), kahit ano ang napiling house
       system.
     Traditional rulers lang (Mars sa Scorpio, Saturn sa Aquarius, Jupiter sa
     Pisces). I-print ang formula na ginamit para sa bawat Lot.
4. Aspects: conjunction, sextile, square, trine, opposition, quincunx, may exact
   orbs at kung applying o separating.
   Orbs (gamitin ang mas malaki kapag magkaiba ang dalawang body):
   - Planet to planet: conj/opp 8°, square/trine 7°, sextile 5°, quincunx 3°
   - Kapag kasama ang Sun o Moon: conj/opp 10°, square/trine 8°, sextile 6°,
     quincunx 3°
   - Planet to ASC/MC: majors 5°, sextile 3°, quincunx 1.5°
   - Points/asteroids/Lots/Nodes/Chiron/Lilith/Cupido/Vertex: max 3°
     (quincunx 1.5°)
   - I-flag ang out-of-sign aspects: kapag hindi tugma ang layo ng mga sign sa
     aspect (hal. conjunction ng 29° Aries at 1° Taurus).
   Paglilinaw:
   - Ang "max" ay hangganan. Kapag kasama ang point (Nodes, Chiron, asteroids,
     Lilith, Cupido, Vertex, Lots), point orbs ang gamit. Kapag kasama ang ASC o
     MC (walang point), ASC/MC orbs. Kung hindi, Sun/Moon orbs kapag kasama ang
     Sun o Moon, at planet orbs kapag planeta sa planeta. Majors = conjunction,
     opposition, square, trine.
   - Mga pares: lahat ng pares ng planets, North Node, Chiron, asteroids, Lilith,
     Cupido, Vertex, ASC, MC at Lots. South Node: conjunction lang (ang ibang
     aspect nito ay kapareho ng sa North Node). Walang DSC/IC at walang ASC–MC.
   - Applying kapag lumiliit ang orb, separating kapag lumalaki. Tunay na galaw
     ang gamit para sa planets, points, ASC at MC. Nakapirmi ang Vertex at Lots
     (gaya ng Astro.com).
5. Technical analysis: sect light, benefic at malefic of sect, essential
   dignities, final dispositor(s), dispositor loops, mutual receptions, lunar
   phase, aspect patterns (Grand Trine, T-Square, Grand Cross, Kite, Yod,
   Stellium), at house ruler placements.
   Paglilinaw:
   - Sect light: Sun kapag day, Moon kapag night. Benefic/malefic of sect: day
     Jupiter/Saturn, night Venus/Mars; ang dalawa pa ay contrary to sect.
   - Essential dignities: domicile, exaltation, detriment, fall lang, para sa 7
     tradisyonal na planeta (Sun hanggang Saturn). Walang scoring.
   - Dispositors: lahat ng 10 planeta, gamit ang traditional rulers. Final
     dispositor: planeta sa sariling domicile na dulo ng chain. Loop: chain na
     umiikot sa dalawa o higit pang planeta.
   - Mutual reception: 7 tradisyonal na planeta, by domicile, by exaltation, o
     mixed (may label kung anong uri).
   - Lunar phase: 8 phase, tig-45° ng Moon − Sun: new, crescent, first quarter,
     gibbous, full, disseminating, last quarter, balsamic. Kasama ang degree at
     kung waxing o waning.
   - Aspect patterns: gamit ang aspects at orbs ng step 4, planets lang (Sun
     hanggang Pluto). Stellium: 3+ planeta sa iisang sign, at hiwalay na 3+ sa
     iisang house. Kite: Grand Trine + ikaapat na planeta na opposite sa isa at
     sextile sa dalawa pa.
   - House rulers: traditional ruler ng sign ng bawat cusp at ang house nito,
     sa house system ng chart. Chart ruler: ruler ng sign ng ASC.
6. Timing:
   a. Transit scan ng Jupiter, Saturn, Uranus, Neptune, Pluto, North Node at Chiron,
      mula 15 taon bago hanggang 15 taon pagkatapos ng current date.
   b. Transit aspects: conjunction, square, opposition, trine. Orb ±1°.
   c. Natal targets lang: Sun, Moon, ASC, MC, chart ruler, Mercury, Venus, Mars,
      Jupiter, Saturn, at ang Lord of the Year ng kasalukuyang profection.
   d. Pagsamahin ang retrograde passes sa iisang window: unang pasok sa orb,
      bawat exact date, huling labas sa orb.
   e. Priority: (1) hits sa ASC, MC, Sun, Moon; (2) hits sa chart ruler o Lord of
      the Year; (3) conjunctions at oppositions bago squares at trines;
      (4) Saturn, Uranus, Neptune, Pluto bago Jupiter, Node, Chiron.
   f. Limit: lahat ng kasalukuyang aktibo, hanggang 15 na pinakamahalagang past,
      at hanggang 20 na pinakamahalagang upcoming.
   g. Annual profections: whole sign, edad 0 = 1st house. Ibigay ang activated
      sign at Lord of the Year para sa kasalukuyang taon at sa susunod na 2 taon.
```

## Open items
- Lot of Wealth uses cusp − ruler (measured from the 2nd house ruler to the
  2nd house cusp), per Al-Biruni and Bonatti. Lot of Victory follows Paulus
  (Spirit to Jupiter by day, reversed by night). Both still need a check
  against Brennan, *Hellenistic Astrology* (2017), Lots chapter.
