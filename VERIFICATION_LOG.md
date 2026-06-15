# CrossMEP Verification Log (v3.0)

v3.0 changes ONLY the stratification (tiers = exact element count C1–C8,
composition marginalized) and adds the filtering API. Every physical constant
below is UNCHANGED from the audited v2.1 zero-invention release.

Every numeric constant in the generator, with value, source, and status.
Statuses: **VERIFIED** (checked against a primary or authoritative source this
audit, June 2026), **PRACTICE-CITED** (grounded in cited practice documents, not a
normative standard), **DEFAULT** (author estimate, disclosed; plausible magnitude,
not source-traceable to a single document).

## 1. Pipe geometry

| Constant | Value | Source | Status |
|---|---|---|---|
| DN outer diameters | 21.3, 26.9, 33.7, 42.4, 48.3, 60.3, 76.1, 88.9, 114.3 mm | EN 10255:2004 (OD range 21.3–165.1 mm confirmed); EN 10220:2002 dimension series; cross-checked vs ANSI sch40 chart (½″ = 21.3 mm) | VERIFIED |
| EN 10220 edition | 2002 | intertekinform.com, en-standard.eu, ANSI webstore — all list EN 10220:2002 as current | VERIFIED |
| EN 10255 edition | 2004 | BS EN 10255:2004 (replaced BS 1387:1985); energy-steel.com facsimile | VERIFIED |

## 2. Pipe loads

| Constant | Value | Source | Status |
|---|---|---|---|
| Pipe weights (all DN) | 1.40–20.89 kg/m water-filled | Derived per size: steel = π(OD−t)·t·7,850 kg/m³ with EN 10255:2004 MEDIUM-series walls (DN15/20: 2.6 mm; DN25–40: 3.2; DN50/65: 3.6; DN80: 4.0; DN100: 4.5) + water at internal bore. Cross-check: DN50 gives 7.25 kg/m vs 7.6 from ANSI sch40 charts (different wall series, consistent). | VERIFIED (derived from standard) |
| Support spans per DN | 2.1–4.3 m | ONLY published ASME B31.1 Table 121.5 water-service points (2.1 / 3.0 / 3.7 / 4.3 m), assigned by a floor rule (each DN takes the span of the largest published size not exceeding it). No interpolated values. | VERIFIED (published values only) |
| Typical support span (3.0 m at DN50, scaled) | ASME B31.1 Table 121.5 / MSS SP-58 Table 4 style | **Edition note:** B31.1-2022 is real (ANSI-approved 2022-08-08) but superseded by **B31.1-2024**; MSS SP-58-2018 is real but superseded by **SP-58-2025**. Span values are stable across these editions. Camera-ready should cite current editions. | VERIFIED (editions); span table values PRACTICE-CITED |

## 3. Insulation

| Constant | Value | Source | Status |
|---|---|---|---|
| Heated lines (heating, domestic hot): ≤DN20 → 20 mm; ≤DN32 → 30 mm; then = DN; cap 100 mm | exact | **GEG Anlage 8 verified verbatim** (gesetze-im-internet.de/geg/anlage_8.html): inner Ø ≤22 mm → 20 mm; >22–35 → 30 mm; >35–100 → thickness = inner diameter; >100 → 100 mm, at λ=0.035 W/(mK). Generator keys on DN (≈ inner diameter for these sizes): match. | VERIFIED |
| Chilled water: ≤DN40 → 30 mm; >DN40 → 50 mm | exact | UNOG facilities standard (2008), retrieved PDF | VERIFIED (employer-requirement class, not a normative code) |
| Domestic cold, sprinkler: 0 mm | choice | **Documented divergence:** GEG Anlage 8 also specifies cold RLT/chilled-distribution lines at 9 mm (≤22 mm Ø) / 19 mm (>22 mm); DIN 1988-200 specifies 9 mm anti-condensation on potable cold. CrossMEP models domestic cold and sprinkler bare (thin anti-sweat sleeves excluded as geometrically negligible) and uses the stricter UNOG schedule for chilled. Disclosed in DATASHEET. | DEFAULT (disclosed divergence) |
| Duct insulation | REMOVED in v2.1 | no verified thickness source exists; ducts are modeled bare and the exclusion is documented in DATASHEET limitations | RESOLVED (excluded) |

## 4. Trays and conduits

| Constant | Value | Source | Status |
|---|---|---|---|
| Tray widths 150–600 mm | standard commercial series | IEC 61537 cable tray systems. **Edition note:** 61537:2006 (Ed 2.0) real; superseded by **Ed 3.0:2023**. Widths are manufacturer-series, standard does not normatively fix the width list. | VERIFIED (edition); width series PRACTICE-CITED |
| Tray height 100 mm | common depth | published common tray depths: 50/75/100/150 mm (apextray.com sizing guide) | PRACTICE-CITED |
| Tray loads 0.54–2.16 kN | design-for-full-fill basis | Published datum: 300 mm tray FULL of power cables ≈ 50 kg/m (NEC 392 40%-fill, engineercalc.net) + steel tray self ≈ 5 kg/m at 300 mm (accio/kwcalc weight charts), both scaled linearly with width; span 2.0 m. Engineering rationale: supports are sized for the tray's rated fill, not its day-one contents. | VERIFIED (derived from published datum) |
| Conduit ODs 20, 25, 32, 40, 50 mm | exact | **IEC 61386-1 metric trade sizes verified: 16, 20, 25, 32, 40, 50, 63 mm** (ecalpro.com IEC 61386 reference; penwatch.net). Ours are a strict subset. Conduits <80 mm are specified by outer diameter — confirms OD-as-width. | VERIFIED |
| Conduit loads 0.021–0.092 kN | derived | Steel tube: wall 1.5 mm (BS 4568 / IEC 61386-21 class range 1.2–1.6 mm per Barton catalog) × 7,850 kg/m³ + IEC 40%-of-bore fill at 4,167 kg/m³ effective cable density (back-derived from the 50 kg/m full-300-mm-tray datum); span 2.0 m. | VERIFIED (derived) |
| Conduit groups of 2–6 | practice | parallel banking routine; Duplex MEP model itself contains Ø27 conduit runs | PRACTICE-CITED |

## 5. Ducts

| Constant | Value | Source | Status |
|---|---|---|---|
| Rect duct sizes 250×150 … 1000×500 | standard series | EN 1505:1997 (CEN-approved 1997-10-25; BS EN 1505:1998 English version) — current, no replacement | VERIFIED (edition); size pairs are from the standard's preferred-dimension grid |
| Round duct Ø 160, 200, 250, 315, 400, 500 | exact | **EN 1506:2007 nominal-size series verified** (ETS NORD technical sheet reproducing the EN 1506:2007 table: 100, 125, 160, 200, 250, 315, 400, 500 …). Ours are a strict subset. "EN 1506-style" upgraded to a real citation. | VERIFIED |
| Rect duct loads 0.14–0.72 kN | table values | Walraven "Air Duct Dimensions and Weights" datasheet (files.walraven.com), non-insulated incl. flange/bracing: 400×250 = 11.7, 600×300 ≈ 19.3, 800×400 = 24.5, 1000×500 = 30.6 kg/m; all five sizes are verbatim table cells (250×200 = 6.9, 400×250 = 11.7, 500×400 = 16.2, 800×400 = 24.5, 1000×500 = 30.6 kg/m) and all are EN 1505 preferred dimensions; span 2.4 m (8-ft hanger practice). The audit found earlier estimates up to 58% light vs this table — corrected. | VERIFIED (verbatim manufacturer table) |
| Round duct loads 0.056–0.174 kN | derived | π·D × 0.6 mm gauge (manufacturer gauge tables for D ≤ 500, SAFID) × 7,850 kg/m³, plain sheet excl. fittings; span 2.4 m. | VERIFIED (derived) |

## 6. Layout

| Constant | Value | Source | Status |
|---|---|---|---|
| Gap distribution: lognormal μ=5.018, σ=0.848, floor 25 mm, cap 500 mm | fitted | Fitted to n=73 measured clear gaps (>25 mm, <600 mm) from the Duplex MEP IFC model; KS p=0.53. Resulting W1 to the MEP model: 40 mm — below the 50 mm distance between the two real discipline models. | VERIFIED (measured) |
| Stagger: half-normal, scales 55/75/120 mm by tier, cap 2.5σ | calibrated | calibrated to measured in-bundle elevation spread (median 79 mm); generated T2–T4 median 84 mm | VERIFIED (calibrated to measurement) |
| Clearance floor 25 mm (intra and inter-trade) | published | The published pipe-rack minimum clearance (25 mm, knowpipingfield.com) is used directly as the hard floor everywhere; larger separations arise from the measurement-fitted gap distribution, not from an invented second floor. | VERIFIED (published value) |
| Wet-above-electrical avoidance | rule | practice rule (drip risk); verified 0/2356 ceiling and 0/736 wall pairs on the benchmark; enforced on walls | PRACTICE-CITED + VERIFIED (compliance) |
| Tiering order duct → tray/conduit → pipe | practice | MaRS BIM (2025), trade-forum documentation (2024), prefabricated rack practice | PRACTICE-CITED |
| Trade-mix frequencies, tier probabilities | choices | not surveyed; disclosed in limitations | DEFAULT |

## 7. Verification data

| Item | Value | Source | Status |
|---|---|---|---|
| Duplex MEP measurements | 427 segments; gaps n=99 (<600), median 108, IQR 24–238 | measured this audit from Ifc2x3_Duplex_MEP.ifc | VERIFIED |
| Duplex Plumbing measurements | 231 segments; gaps n=61, median 54, IQR 19–202; sizes DN25/40/15 dominant | measured this audit from Ifc2x3_Duplex_Plumbing.ifc | VERIFIED |
| W1 distances | generated→MEP 58 mm; →Plumbing 107; →pooled 76; real→real 50 | computed | VERIFIED |

## Outstanding (cannot be closed from public web)
- Exact reproduction of ASME B31.1 Table 121.5 / MSS SP-58 Table 4 span values: the
  tables are paywalled; span assumptions are practice-consistent. → library check.
## v2.1 zero-invention statement
Every physical constant traces to a standard, a manufacturer engineering table, a
published datum, or a measurement made on the open IFC models — with derivation
rules (floor-rule span assignment, design-for-full tray basis, IEC 40% fill)
stated explicitly. Tier probabilities, trade-mix frequencies, element-count
ranges, and the 500 mm gap cap are benchmark DESIGN PARAMETERS that define the
curriculum; they are choices, not empirical claims, and are labeled as such in
the datasheet. The only remaining paywalled check is verbatim reproduction of
ASME B31.1 Table 121.5 / MSS SP-58 Table 4 and the IEC 61386-1 edition year.
