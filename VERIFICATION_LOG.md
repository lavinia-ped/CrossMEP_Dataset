# CrossMEP Verification Log (release 4.1.0; data revisions 4.1, 4.0 and 3.0)

Every numeric constant in the generator, with value, source and status, keyed to
its name in `crossmep/library.py` (physical constants) and `crossmep/layout.py`
(layout). Loads are **derived in code** from the primitives listed in sections
2, 4 and 5; `tests/test_library.py` pins every derived value to the frozen table
of the data release, so a change to a primitive cannot alter the data unnoticed.
The element library is identical in revisions 3.0 and 4.0, which differ only in
layout arithmetic (section 6, "Gap semantics"); revision 4.1 adds DN125 and
DN150 and changes four composition parameters (section 6, "Composition 4.1").

Statuses: **VERIFIED** (checked against a primary or authoritative source,
June 2026 audit), **PRACTICE-CITED** (grounded in practice documents, not a
normative standard), **DEFAULT** (author choice, disclosed; plausible magnitude,
not source-traceable to a single document).

## 1. Pipe geometry

| Constant | Value | Source | Status |
|---|---|---|---|
| `DN_OD_MM` | 21.3, 26.9, 33.7, 42.4, 48.3, 60.3, 76.1, 88.9, 114.3 mm (DN15–100); 139.7, 165.1 mm (DN125, DN150; revision 4.1) | EN 10255:2004 (OD range 21.3–165.1 mm confirmed); EN 10220:2002 dimension series; cross-checked vs ANSI sch40 chart (½″ = 21.3 mm) | VERIFIED |
| EN 10220 / EN 10255 editions | 2002 / 2004 | current editions listed by national standards bodies; BS EN 10255:2004 replaced BS 1387:1985 | VERIFIED |

## 2. Pipe loads (`pipe_load_kN` = load per metre × span, rounded to 0.01 kN)

| Constant | Value | Source | Status |
|---|---|---|---|
| `EN10255_MEDIUM_WALL_MM` | DN15/20: 2.6; DN25–40: 3.2; DN50/65: 3.6; DN80: 4.0; DN100: 4.5; DN125/150: 5.0 mm | EN 10255:2004 medium series; DN125 / DN150 walls as republished in merchant and mill tables, whose published empty masses (16.6 / 19.8 kg/m) the derivation reproduces (16.6 / 19.7) | VERIFIED |
| `STEEL_DENSITY_KG_M3`, `WATER_DENSITY_KG_M3`, `G_M_S2` | 7,850 kg/m³; 1,000 kg/m³; 9.81 m/s² | standard values; loads are insensitive to 9.81 vs 9.80665 at the released precision | VERIFIED |
| `pipe_mass_kg_m` | 1.40 (DN15) … 20.89 (DN100) kg/m water-filled; DN50 = 7.25 | steel annulus π(OD−t)·t·ρ + water at the bore; DN50 7.25 vs 7.6 kg/m from ANSI sch40 charts (different wall series, consistent) | VERIFIED (derived) |
| `ASME_B311_WATER_SPAN_M` | NPS 1 / 2 / 3 / 4 / 6 = 2.1 / 3.0 / 3.7 / 4.3 / 5.2 m (7 / 10 / 12 / 14 / 17 ft) | ASME B31.1 Table 121.5 water-service points; the same four values appear in the ASHRAE Handbook, *HVAC Systems and Equipment*, "Pipes, Tubes, and Fittings", table of suggested hanger spacing for standard steel pipe (water), and in MSS SP-69/SP-58. Two independent normative republications agree; the ASME table itself is paywalled (verbatim check outstanding). B31.1-2022 superseded by B31.1-2024, MSS SP-58-2018 by SP-58-2025; values stable across editions | VERIFIED (two concordant sources) |
| `support_span_m` floor rule | DN15–40 → 2.1; DN50/65 → 3.0; DN80 → 3.7; DN100/125 → 4.3; DN150 → 5.2 m | each DN takes the span of the largest published size not exceeding it; sizes below NPS 1 take 2.1 m. **No interpolated values** (an earlier log entry mentioning interpolated DN32/40/65 spans described a v1 rule and was wrong for the released data). Recorded per element as `span_m` in revision 4.0 | VERIFIED (rule stated) |
| `pipe_load_kN_per_m` | 0.0137 (DN15) … 0.2049 (DN100) kN/m | mass × g; recorded per element as `load_kN_per_m` (4 decimals) in revision 4.0; `round(load_kN_per_m × span_m, 2) == load_kN` for every library element (tested) | VERIFIED (derived) |
| `DN_LOAD_KN` | 0.03, 0.04, 0.06, 0.08, 0.10, 0.21, 0.30, 0.49, 0.88 kN; DN125 1.26, DN150 1.97 kN (4.1) | derived; e.g. DN50: 7.25 kg/m × 3.0 m × 9.81 = 0.213 kN | VERIFIED (derived, test-pinned) |

## 3. Insulation (`insulation_mm`, per side)

| Constant | Value | Source | Status |
|---|---|---|---|
| Heated lines (heating, domestic hot) | ≤ DN20 → 20 mm; ≤ DN32 → 30 mm; then = DN; cap 100 mm | **GEG Anlage 8 verified verbatim** (gesetze-im-internet.de/geg/anlage_8.html): inner Ø ≤ 22 mm → 20 mm; > 22–35 → 30 mm; > 35–100 → thickness = inner diameter; > 100 → 100 mm, at λ = 0.035 W/(m·K). Keying on DN (≈ inner diameter at these sizes) matches | VERIFIED |
| Chilled water | ≤ DN40 → 30 mm; > DN40 → 50 mm | UNOG facilities standard (2008), retrieved PDF | VERIFIED (employer-requirement class, not a normative code) |
| Domestic cold, sprinkler | 0 mm | **Documented divergence:** GEG Anlage 8 specifies 9/19 mm for cold RLT/chilled-distribution lines; DIN 1988-200 9 mm anti-condensation on potable cold. CrossMEP models these bare (thin anti-sweat sleeves geometrically negligible) and uses the stricter UNOG schedule for chilled | DEFAULT (disclosed) |
| Duct insulation | excluded | no verified thickness source; ducts modelled bare (DATASHEET) | RESOLVED (excluded) |

## 4. Cable trays and conduits

| Constant | Value | Source | Status |
|---|---|---|---|
| `TRAY_WIDTHS_MM` | 150, 225, 300, 450, 600 mm | **NEMA VE 1** standard tray widths 6 / 9 / 12 / 18 / 24 in (152 / 229 / 305 / 457 / 610 mm), as sold in the metric market at these roundings; IEC 61537 (Ed 3.0:2023) itself does not fix a width list | VERIFIED (NEMA VE 1 series, metric rounding) |
| `TRAY_HEIGHT_MM` | **60 mm** | common commercial side height (published depth series 50/60/75/100/150 mm); NEMA VE 1 depths start at 3 in, so the European 60 mm is kept as the metric-market value. *Correction:* the v3.0 log said 100 mm; the released data and code use 60 mm | PRACTICE-CITED |
| `TRAY_FULL_CABLE_KG_M_AT_300`, `TRAY_SELF_KG_M_AT_300`, `TRAY_SPAN_M` | 50 kg/m; 5 kg/m; 2.0 m | 300 mm tray full of power cable ≈ 50 kg/m on the NEC 392 40 %-fill basis (published datum); steel tray self-weight ≈ 5 kg/m at 300 mm (published weight charts); 2.0 m is below the shortest **NEMA VE 1** load-class span (8 ft = 2.44 m; classes 8/10/12/16/20 ft at 50/75/100 lb/ft), i.e. conservative for any class-rated tray, and is the common European support spacing | VERIFIED (datum) / PRACTICE-CITED (span, bracketed by NEMA VE 1) |
| `TRAY_LOAD_KN` | 0.54, 0.81, 1.08, 1.62, 2.16 kN (0.2698–1.0791 kN/m × 2.0 m) | design-for-full basis, both masses scaled linearly with width: supports are sized for the tray's rated fill, not its day-one contents | VERIFIED (derived, test-pinned) |
| `CONDUIT_OD_MM` | 20, 25, 32, 40, 50 mm | **IEC 61386-1 metric sizes 16, 20, 25, 32, 40, 50, 63 mm**; strict subset. Conduits < 80 mm are specified by outer diameter (confirms OD-as-width) | VERIFIED |
| `CONDUIT_WALL_MM`, `CABLE_FILL_FRACTION`, `CABLE_BULK_DENSITY_KG_M3` | 1.5 mm; 0.40; 4,167 kg/m³ | wall per BS 4568 / IEC 61386-21 class range 1.2–1.6 mm; IEC/NEC 40 %-of-bore fill; bulk density back-derived from the tray datum: 50 kg/m ÷ (0.40 × 0.300 m × 0.100 m) | VERIFIED (derived) |
| `CONDUIT_SPAN_M` | 2.0 m | **IET On-Site Guide** (BS 7671) table of maximum support spacing for conduits: rigid metal 16–25 mm, 1.75 m horizontal / 2.0 m vertical (larger bands longer). 2.0 m is the table's vertical value for the smallest band used and within 0.25 m of its horizontal value; one span is used for all five sizes (20–50 mm) for simplicity. NEC 344.30 allows 10 ft for the same sizes and is not used (US-specific, longer) | VERIFIED (IET table; single value, see section 10) |
| `CONDUIT_LOAD_KN` | 0.021, 0.029, 0.044, 0.063, 0.092 kN | derived | VERIFIED (derived, test-pinned) |
| `CONDUIT_GROUP_SIZES` | parallel groups of 2–6 | banking practice; the Duplex MEP model itself contains parallel Ø27 conduit runs | PRACTICE-CITED |

## 5. Ducts

| Constant | Value | Source | Status |
|---|---|---|---|
| `RECT_DUCT_SIZES_MM` | 250×200, 400×250, 500×400, 800×400, 1000×500 | EN 1505:1997 preferred-dimension grid (CEN-approved 1997-10-25; current) | VERIFIED |
| `WALRAVEN_RECT_DUCT_KG_M` | 6.9, 11.7, 16.2, 24.5, 30.6 kg/m | verbatim cells of the Walraven "Air Duct Dimensions and Weights" datasheet, non-insulated, incl. flange/bracing allowance; no extrapolated cells | VERIFIED (manufacturer table) |
| `DUCT_SPAN_M` | 2.4 m (8 ft) | **SMACNA HVAC Duct Construction Standards, Metal and Flexible**, Table 5-1 / 5-1M: maximum rectangular-duct hanger spacing 10 ft (3.0 m); 8 ft is the value most project specifications adopt under that table and the spacing of the manufacturer weight table used here. EN 12236:2002 (duct hangers and supports) sets strength tests, not a spacing. A general rule of 2.0 m for ducts over 0.4 m² would shorten the span of the 1000 × 500 duct only | PRACTICE-CITED (within the SMACNA maximum) |
| `RECT_DUCT_LOAD_KN` | 0.16, 0.28, 0.38, 0.58, 0.72 kN | derived | VERIFIED (derived, test-pinned) |
| `ROUND_DUCT_D_MM` | 160, 200, 250, 315, 400, 500 mm | **EN 1506:2007 nominal-size series** (manufacturer sheet reproducing the table); strict subset | VERIFIED |
| `SPIRAL_DUCT_SHEET_MM` | 0.6 mm | manufacturer gauge tables for D ≤ 500 | VERIFIED |
| `ROUND_DUCT_LOAD_KN` | 0.056, 0.070, 0.087, 0.110, 0.139, 0.174 kN | π·D × gauge × 7,850 kg/m³ × 2.4 m × g, plain sheet excl. fittings | VERIFIED (derived, test-pinned) |

## 6. Layout (`crossmep/layout.py`, `crossmep/model.py`)

| Constant | Value | Source | Status |
|---|---|---|---|
| `MIN_CLEAR_GAP_MM` / `GAP_FLOOR_MM` | 25 mm clear between insulation surfaces, along or out; floor on the sampled gap, inside and between trades | the published pipe-rack minimum clearance; larger separations arise from the fitted distribution, not from an invented second floor | VERIFIED (published value) |
| `GAP_LOGNORMAL_MU`, `GAP_LOGNORMAL_SIGMA` | 5.018, 0.848 | fitted (log-moments, population σ) to n = 73 measured Duplex MEP clear gaps > 25 mm and < 600 mm; KS D = 0.092, p = 0.53. `verify/compare_gaps.py` refits and matches to 3 decimals | VERIFIED (measured) |
| `GAP_CAP_MM` | 500 mm | design parameter | DEFAULT |
| **Gap semantics** | **4.0:** the sampled gap is the physical clear gap between insulation surfaces (min 25 mm). **3.0:** every element also carried a 25 mm routing envelope per side, so the physical gap was the draw + 50 mm (min 75 mm) and `bundle_width_mm` included 50 mm of empty envelope | double-counting found in the 3.5.0 audit and removed in revision 4.0 without touching the random stream; the 3.0 files remain as released | RESOLVED (4.0) / DISCLOSED (3.0) |
| `ROW_VGAP_MM`, `TOP_OFFSET_MM` | 120 mm clear between rows; 90 mm first-row standoff | design parameters | DEFAULT |
| Stagger (`generate.stagger_for`) | half-normal, scale **0 / 75 / 120 mm** for 1 / ≤ 5 / > 5 elements, cap 2.5 σ, drawn per element | calibrated to measured in-bundle elevation spread (Duplex MEP median 79 mm, p75 282); generated in-row spread on the benchmark: median 93 mm, p75 149. *Correction:* the v3.0 log listed 55/75/120. Per-element draw is a simplification (a bank on one trapeze is co-planar) | VERIFIED (calibrated) / DEFAULT (per-element) |
| `VPRIORITY` tiering order | duct → tray/conduit → pipe (bulky nearest the surface) | coordination practice (MaRS BIM 2025; trade-forum documentation 2024); prefabricated rack practice. The criteria behind it (spatial clearance, functional constraints such as gravity flow, installation access) are the MEP-coordination design criteria of Korman, Fischer & Tatum (2003), *J. Constr. Eng. Manage.* 129(6), 627–634, which does not prescribe this order | PRACTICE-CITED (criteria peer-reviewed) |
| Wall drip rule | electrical containment above wet services within a row | **BS 7671 Reg. 528.3.2**: a wiring system routed below services liable to cause condensation (water, steam, gas) shall be protected from their effects; placing containment above the wet services is the layout that satisfies the regulation without added protection. Enforced on walls; **0 violations in 2,096 ceiling and 817 wall wet/electrical pairs** on the benchmark, and over 600 unseen contexts in tests | VERIFIED (BS 7671 rule) + VERIFIED (compliance) |
| **Composition 4.1** (`P_SECOND_ROW_4_1`, `P_THIRD_ROW_4_1`, `P_SAME_KIND_4_1`, `OPTIONS_MULTI_4_1` / `WEIGHTS_MULTI_4_1`, `TRADE_DN_BAND_4_1`) | second row with probability 0.12 / 0.12 / 0.20 / 0.35 / 0.40 / 0.40 / 0.30 for 2–8 elements, third row 0.05 above five; next group repeats the previous kind with probability 0.5; option weights pipe bank 0.44, tray group 0.16, duct 0.08, duct pair 0.08, conduit group 0.16, single pipe 0.08; DN bands domestic 15–50, heating 20–100, chilled and sprinkler 25–150 | design parameters chosen after the composition comparison on revision 4.0 (next row): the clinic's stacked share by count (10–40 %), its mixed-kind share (3–27 %), its duct share in pairs (27 %) and its DN100+ mains. Not fitted: round values, one pass; the 4.1 comparison is in sample (TV ≤ 0.13 by count, mixing and stacking within about ten points, `RESULTS.md`) | DEFAULT (informed by measurement, disclosed) |
| Surface mix, trade mix, option weights, DN bands, thickness choices (3.0 / 4.0) | `generate.py` design parameters | not surveyed; disclosed in DATASHEET. **Compared, not fitted** (`verify/compare_composition.py`, October 2026): on the clinic (Plumbing + HVAC merged), conditional on the element count, the generated pipe/duct split is within TV 0.10 of the measured one for 3–8 elements (0.20 for pairs: ducts pair with pipes more often than drawn); the generator mixes kinds in one bundle and stacks rows more often than the clinic (e.g. 6 elements: mixed 47 % vs 24 %, stacked 100 % vs 38 %); 70 % of clinic hanger locations carry one element, 96 % three or fewer. DN mix differs by building (clinic 30 % ≥ DN100, duplex 87 % DN25; real-to-real TV 0.87 > generated-to-either 0.41 / 0.67). Electrical share and surface mix not testable (the open electrical models hold fixtures only; no architecture model used) | DEFAULT (composition compared on two open buildings) |

## 7. Verification data (`verify/`)

| Item | Value | Source | Status |
|---|---|---|---|
| Duplex MEP measurements (June 2026) | 427 segments; 103 clear gaps (99 < 600 mm): median 108, IQR 24–238 mm (< 600); 28–271 (all) | shipped sample `measured_gaps.json`; the generator's gap lognormal is fitted to it | SHIPPED; NOT REPRODUCIBLE with the documented June procedure (re-run October 2026: 131 gaps, median −24 mm; `measure_ifc.py --legacy`) |
| Duplex Plumbing measurements (June 2026) | 231 sized segments; 61 gaps (59 < 600): median 53, IQR 18–183 (< 600); 19–202 (all) | `measured_gaps_plumbing.json` | SHIPPED |
| Wasserstein-1 against the June samples, revision 4.1 | insulation surface: → MEP 42.3, → Plumbing 90.9, → pooled 60.4 mm; bare surface: 71.8 / 121.4 / 90.3 mm | `python verify/compare_gaps.py`, test-pinned; same gap draw as 4.0, wider DN bands add insulation | VERIFIED (computed) |
| Wasserstein-1 against the June samples, revision 4.0 | insulation surface: → MEP **40.7**, → Plumbing 89.3, → pooled 58.9 mm; bare surface: 67.7 / 117.4 / 86.3 mm | `python verify/compare_gaps.py --version 4.0`, test-pinned (the paper's §5.2) | VERIFIED (computed) |
| Wasserstein-1 against the June samples, revision 3.0 | envelope draw (the paper's definition): 40.7 / 89.3 / 58.9; insulation surface: 88.5 / 137.6 / 106.9; bare: 109.9 / 159.6 / 128.4 mm | `python verify/compare_gaps.py --version 3.0`, test-pinned | VERIFIED (computed) |
| Baselines against the June samples | fixed 25 mm gap → MEP 138.5 mm; MEP ↔ Plumbing (real-to-real) 49.9 mm | same | VERIFIED (computed) |
| Section-cut measurement (October 2026) | sections every 250 mm, rows within 400 mm of height, bare surfaces; Duplex MEP 74 pipe pairs, Duplex Plumbing 41, Medical-Dental Clinic Plumbing 797 | `verify/measure_ifc.py` on the CC BY 4.0 buildingSMART files (SHA-256 in `verify/measured/README.md`); records recomputed from the shipped segment tables in `tests/test_sections.py` | VERIFIED (measured) |
| Composition on sections (October 2026) | Clinic Plumbing + HVAC merged: 12,529 hanger locations, 2,430 physical bundles; Duplex MEP: 393 / 121. Bundles with another row within 1.5 m count as stacked (the other storey does not) | `python verify/compare_composition.py`, test-pinned (`tests/test_composition.py`); the Clinic and Duplex Electrical models contain no `IfcFlowSegment` (SHA-256 in `verify/measured/README.md`); the Duplex Plumbing model re-exports 161 of the MEP model's pipe boxes and is not merged | VERIFIED (measured) |
| Wasserstein-1 on sections, revision 4.1 (pipe-pipe, by length) | → Clinic **32.5** (16.9–47.5); → Duplex MEP 75.7; → Duplex Plumbing 88.1; 1,690 generated pairs in 575 contexts | `python verify/compare_sections.py --sensitivity`, test-pinned; 31–41 mm across 11 cut settings; the clinic stays held out for spacing (composition, not the gap draw, changed in 4.1) | VERIFIED (computed) |
| Wasserstein-1 on sections, revision 4.0 (pipe-pipe, by length) | → Clinic **28.3** (16.0–43.7); → Duplex MEP 70.4; → Duplex Plumbing 85.3; Clinic ↔ Duplex 71.0 / 85.0; Duplex MEP ↔ Plumbing 25.6; revision 3.0 → Clinic 65.1 mm | `python verify/compare_sections.py --sensitivity --version 4.0`, test-pinned; stable across 11 cut settings (27–36 mm) | VERIFIED (computed) |

## 8. Reproducibility

| Item | Value | Status |
|---|---|---|
| Byte-exact regeneration of all twelve files (three revisions) | SHA-256 in `RELEASE_CHECKSUMS.txt`; `tests/test_release.py`; CI on Python 3.9–3.13 × NumPy 1.26 / 2.0 / latest | VERIFIED |
| `total_load_kN` | `round(math.fsum(loads), 2)` — exactly rounded; plain `sum()` differs on Python ≤ 3.11 for 28 contexts | VERIFIED (fixed 3.5.0) |
| File format | compact JSON, ASCII-escaped, no trailing newline | VERIFIED |
| Random stream | NumPy `Generator` (PCG64) from the split seed; draw order frozen and identical across revisions (two quirks marked `# stream:`) | VERIFIED |

## 9. Outstanding
- Verbatim reproduction of ASME B31.1 Table 121.5 / MSS SP-58 Table 4 (paywalled; library check). The four values are already confirmed by the ASHRAE Handbook table (section 2).
- Refitting the gap distribution to the section-cut measurements (a data revision; the released files keep the June 2026 fit).
- Per-group (co-planar bank) stagger with re-calibration against the measured elevation spread.
- Candidates for a later revision (each changes released numbers): per-DN pipe spans from the BS EN 806-4:2010 support-spacing table instead of the five ASME points (finer, but not yet checked against the primary text); tray span 2.44 m (the NEMA VE 1 8-ft class); first-row standoff and gap floor from the DIN 4140 minimum clearances between insulated pipes and to building parts (the table values are not yet verified).
- Composition was compared on the open models on revision 4.0 and four parameters were adjusted in 4.1 (section 6); that comparison is now in sample. An out-of-sample composition check needs a third open building with pipes and ducts modelled. The electrical share and the surface mix remain untestable on these models (their electrical models carry fixtures only; no architecture model is used).

## 10. Why these standards

Many documents give a value for each constant. The choice follows four rules,
applied in order; each row above records the highest rung its source reaches.

1. **Metric, DN-keyed geometry follows the European normative series.** The
   dataset is in millimetres and DN, so sizes come from the standards an
   EU contractor orders against: EN 10220 / EN 10255 (pipe), EN 1505 / EN 1506
   (duct), IEC 61386-1 (conduit), IEC 61537 (tray systems). ANSI / ASTM sizes
   are used only as cross-checks (DN50 vs sch 40).
2. **Where the European standard fixes no value, take the de-facto
   international reference whose values are openly republished.** IEC 61537
   leaves tray widths to the manufacturer and EN 12236 tests hanger strength
   without a spacing, so tray widths and class spans follow NEMA VE 1, pipe
   spans ASME B31.1 (confirmed by the ASHRAE Handbook), duct hanger spacing
   SMACNA, and conduit support spacing the IET On-Site Guide table under
   BS 7671. US-only values that are longer than European practice (NEC 344.30
   conduit spacing, 10 ft) are not used.
3. **Prefer the source whose text can be checked in full.** Insulation follows
   the German GEG because it is a statute with public full text (Anlage 8 was
   checked verbatim) and its thickness-equals-diameter rule is the strictest
   common European schedule; the chilled-water schedule comes from a published
   facilities standard because the GEG cold-line values address condensation,
   not thermal loss. A paywalled standard is accepted only when two independent
   republications agree (ASME B31.1 via ASHRAE and MSS).
4. **Prefer values stable across editions**, so that an edition change cannot
   move the data (B31.1-2022 → 2024, MSS SP-58-2018 → 2025, EN 10255:2004,
   EN 1505:1997).

Preference order of sources: statute or normative standard with public text →
normative standard with concordant republications → manufacturer engineering
table → practice guidance (SMACNA / IET / trade documentation) → author default,
disclosed. Where the chosen value is not the standard's exact figure, the row
says how the standard brackets it (tray span below the shortest NEMA class;
duct span under the SMACNA maximum; one conduit span for all sizes).

Alternatives considered and not used: BS EN 806-4 and IPC / UPC hanger tables
(potable-water specific; EN 806-4 not yet verified from the primary text, listed
in section 9); NEC 344 / 358 (US spacing, longer than European); DIN 4140
clearances (candidate for the standoff, section 9); DW/144 (BESA, UK duct
specification, consistent with SMACNA but less widely republished).

## 11. Sources (public texts and republications used for the checks)

- GEG Anlage 8: https://www.gesetze-im-internet.de/geg/anlage_8.html
- ASHRAE hanger-spacing table (standard steel pipe, water), as republished: https://www.engineersedge.com/fluid_flow/pipe_support_hanger_spacing_15713.htm
- NEMA VE 1 standard widths and load classes, as republished: https://www.goagilix.com/blog/understanding-nema-standards-for-cable-tray-systems/
- IET On-Site Guide conduit support spacing, as republished: https://www.voltimum.co.uk/news/scolmore-group/what-distances-are-required-between
- BS 7671 Reg. 528.3.2, as quoted: https://engx.theiet.org/f/wiring-and-regulations/29646/water-pipes-passing-over-electrical-sub-distribution-panels
- SMACNA HVAC-DCS Table 5-1 maximum spacing, as cited in public specifications: https://suppliers.usask.ca/documents/master-specifications/23-31-13.01-metal-ducts-low-pressure-to-500pa.pdf
- Korman, Fischer & Tatum (2003): https://doi.org/10.1061/(ASCE)0733-9364(2003)129:6(627)
- DIN 4140 clearances (overview): https://www.baunetzwissen.de/daemmstoffe/fachwissen/wand/rohrleitungen-daemmen-152260
