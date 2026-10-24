# Birth Chart Spec (Computation)

The COMPUTATION section is the source of truth for aster-engine.
BIRTH DATA describes the engine's input. Output formatting and interpretation
are out of scope for this repo.

```
BIRTH DATA
- Date:
- Time:
- Place: (gamitin ang local timezone ng lugar at petsa para i-convert sa UT)
- House system: Placidus o Whole Sign (pumili ng isa)
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
   - Mean North/South Node, Chiron
   - Ceres, Pallas, Juno, Vesta, Hygiea
   - Lilith (mean Black Moon), Cupido (Uranian, mula sa seorbel.txt)
   - ASC, MC, Vertex
   - Sect: day chart kapag nasa itaas ng horizon ang Sun, ibig sabihin nasa
     houses 7-12 (norm(Sun − ASC) > 180°). Kung hindi, night chart. I-flag kapag
     nasa loob ng 1° ng ASC o DSC ang Sun, dahil unstable ang sect at pwedeng
     magbago kapag mali ng ilang minuto ang birth time.
   - Lots (iisang sect ang gamit ng lahat; norm = x mod 360):
     * Fortune: day ASC + Moon − Sun; night ASC + Sun − Moon
     * Spirit: day ASC + Sun − Moon; night ASC + Moon − Sun
     * Victory: day ASC + Jupiter − Spirit; night ASC + Spirit − Jupiter
     * Wealth (Substance): ASC + (traditional ruler ng 2nd house) − (2nd house
       cusp), walang day/night reversal. Laging Whole Sign ang 2nd house dito
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
   - I-flag ang out-of-sign aspects.
5. Technical analysis: sect light, benefic at malefic of sect, essential
   dignities, final dispositor(s), dispositor loops, mutual receptions, lunar
   phase, aspect patterns (Grand Trine, T-Square, Grand Cross, Kite, Yod,
   Stellium), at house ruler placements.
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
- Verify the Lot of Wealth direction (ruler − cusp vs cusp − ruler) and the
  Lot of Victory formula against Brennan, *Hellenistic Astrology* (2017).
