# CrossMEP Verification Log (release 4.0.0; data revisions 4.0 and 3.0)

Every numeric constant in the generator, with value, source and status, keyed to
its name in `crossmep/library.py` (physical constants) and `crossmep/layout.py`
(layout). Loads are **derived in code** from the primitives listed in sections
2, 4 and 5; `tests/test_library.py` pins every derived value to the frozen table
of the data release, so a change to a primitive cannot alter the data unnoticed.
The element library is identical in revisions 3.0 and 4.0; they differ only in
layout arithmetic (section 6, "Gap semantics").

Statuses: **VERIFIED** (checked against a primary or authoritative source,
June 2026 audit), **PRACTICE-CITED** (grounded in practice documents, not a
normative standard), **DEFAULT** (author choice, disclosed; plausible magnitude,
not source-traceable to a single document).

## 1. Pipe geometry

| Constant | Value | Source | Status |
|---|---|---|---|
| `DN_OD_MM` | 21.3, 26.9, 33.7, 42.4, 48.3, 60.3, 76.1, 88.9, 114.3 mm (DN15–100) | EN 10255:2004 (OD range 21.3–165.1 mm confirmed); EN 10220:2002 dimension series; cross-checked vs ANSI sch40 chart (½″ = 21.3 mm) | VERIFIED |
| EN 10220 / EN 10255 editions | 2002 / 2004 | current editions listed by national standards bodies; BS EN 10255:2004 replaced BS 1387:1985 | VERIFIED |

## 2. Pipe loads (`pipe_load_kN` = load per metre × span, rounded to 0.01 kN)

| Constant | Value | Source | Status |
|---|---|---|---|
| `EN10255_MEDIUM_WALL_MM` | DN15/20: 2.6; DN25–40: 3.2; DN50/65: 3.6; DN80: 4.0; DN100: 4.5 mm | EN 10255:2004 medium series | VERIFIED |
| `STEEL_DENSITY_KG_M3`, `WATER_DENSITY_KG_M3`, `G_M_S2` | 7,850 kg/m³; 1,000 kg/m³; 9.81 m/s² | standard values; loads are insensitive to 9.81 vs 9.80665 at the released precision | VERIFIED |
| `pipe_mass_kg_m` | 1.40 (DN15) … 20.89 (DN100) kg/m water-filled; DN50 = 7.25 | steel annulus π(OD−t)·t·ρ + water at the bore; DN50 7.25 vs 7.6 kg/m from ANSI sch40 charts (different wall series, consistent) | VERIFIED (derived) |
| `ASME_B311_WATER_SPAN_M` | NPS 1 / 2 / 3 / 4 = 2.1 / 3.0 / 3.7 / 4.3 m | ASME B31.1 Table 121.5 water-service points as widely republished; the table is paywalled (library check outstanding). B31.1-2022 superseded by B31.1-2024, MSS SP-58-2018 by SP-58-2025; values stable across editions | PRACTICE-CITED |
| `support_span_m` floor rule | DN15–40 → 2.1; DN50/65 → 3.0; DN80 → 3.7; DN100 → 4.3 m | each DN takes the span of the largest published size not exceeding it; sizes below NPS 1 take 2.1 m. **No interpolated values** (an earlier log entry mentioning interpolated DN32/40/65 spans described a v1 rule and was wrong for the released data). Recorded per element as `span_m` in revision 4.0 | VERIFIED (rule stated) |
| `pipe_load_kN_per_m` | 0.0137 (DN15) … 0.2049 (DN100) kN/m | mass × g; recorded per element as `load_kN_per_m` (4 decimals) in revision 4.0; `round(load_kN_per_m × span_m, 2) == load_kN` for every library element (tested) | VERIFIED (derived) |
| `DN_LOAD_KN` | 0.03, 0.04, 0.06, 0.08, 0.10, 0.21, 0.30, 0.49, 0.88 kN | derived; e.g. DN50: 7.25 kg/m × 3.0 m × 9.81 = 0.213 kN | VERIFIED (derived, test-pinned) |

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
| `TRAY_WIDTHS_MM` | 150, 225, 300, 450, 600 mm | manufacturer series for IEC 61537 systems (Ed 3.0:2023 current; the standard does not fix the width list) | PRACTICE-CITED |
| `TRAY_HEIGHT_MM` | **60 mm** | common commercial side height (published depth series 50/60/75/100/150 mm). *Correction:* the v3.0 log said 100 mm; the released data and code use 60 mm | PRACTICE-CITED |
| `TRAY_FULL_CABLE_KG_M_AT_300`, `TRAY_SELF_KG_M_AT_300`, `TRAY_SPAN_M` | 50 kg/m; 5 kg/m; 2.0 m | 300 mm tray full of power cable ≈ 50 kg/m on the NEC 392 40 %-fill basis (published datum); steel tray self-weight ≈ 5 kg/m at 300 mm (published weight charts); typical tray support spacing | VERIFIED (datum) / PRACTICE-CITED (span) |
| `TRAY_LOAD_KN` | 0.54, 0.81, 1.08, 1.62, 2.16 kN (0.2698–1.0791 kN/m × 2.0 m) | design-for-full basis, both masses scaled linearly with width: supports are sized for the tray's rated fill, not its day-one contents | VERIFIED (derived, test-pinned) |
| `CONDUIT_OD_MM` | 20, 25, 32, 40, 50 mm | **IEC 61386-1 metric sizes 16, 20, 25, 32, 40, 50, 63 mm**; strict subset. Conduits < 80 mm are specified by outer diameter (confirms OD-as-width) | VERIFIED |
| `CONDUIT_WALL_MM`, `CABLE_FILL_FRACTION`, `CABLE_BULK_DENSITY_KG_M3`, `CONDUIT_SPAN_M` | 1.5 mm; 0.40; 4,167 kg/m³; 2.0 m | wall per BS 4568 / IEC 61386-21 class range 1.2–1.6 mm; IEC/NEC 40 %-of-bore fill; bulk density back-derived from the tray datum: 50 kg/m ÷ (0.40 × 0.300 m × 0.100 m) | VERIFIED (derived) |
| `CONDUIT_LOAD_KN` | 0.021, 0.029, 0.044, 0.063, 0.092 kN | derived | VERIFIED (derived, test-pinned) |
| `CONDUIT_GROUP_SIZES` | parallel groups of 2–6 | banking practice; the Duplex MEP model itself contains parallel Ø27 conduit runs | PRACTICE-CITED |

## 5. Ducts

| Constant | Value | Source | Status |
|---|---|---|---|
| `RECT_DUCT_SIZES_MM` | 250×200, 400×250, 500×400, 800×400, 1000×500 | EN 1505:1997 preferred-dimension grid (CEN-approved 1997-10-25; current) | VERIFIED |
| `WALRAVEN_RECT_DUCT_KG_M` | 6.9, 11.7, 16.2, 24.5, 30.6 kg/m | verbatim cells of the Walraven "Air Duct Dimensions and Weights" datasheet, non-insulated, incl. flange/bracing allowance; no extrapolated cells | VERIFIED (manufacturer table) |
| `DUCT_SPAN_M` | 2.4 m | 8-ft hanger-spacing practice | PRACTICE-CITED |
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
| `VPRIORITY` tiering order | duct → tray/conduit → pipe (bulky nearest the surface) | coordination practice (MaRS BIM 2025; trade-forum documentation 2024); prefabricated rack practice | PRACTICE-CITED |
| Wall drip rule | electrical containment above wet services within a row | practice rule (drip risk); enforced on walls; **0 violations in 2,096 ceiling and 817 wall wet/electrical pairs** on the benchmark, and over 600 unseen contexts in tests | PRACTICE-CITED + VERIFIED (compliance) |
| Surface mix, trade mix, option weights, DN bands, thickness choices | `generate.py` design parameters | not surveyed; disclosed in DATASHEET | DEFAULT |

## 7. Verification data (`verify/`)

| Item | Value | Source | Status |
|---|---|---|---|
| Duplex MEP measurements | 427 segments; 103 clear gaps (99 < 600 mm): median 108, IQR 24–238 mm (< 600); 28–271 (all) | measured June 2026 from the Duplex MEP IFC with IfcOpenShell; procedure `verify/measure_ifc.py`; sample `measured_gaps.json` | VERIFIED |
| Duplex Plumbing measurements | 231 sized segments; 61 gaps (59 < 600): median 53, IQR 18–183 (< 600); 19–202 (all); sizes DN25/40/15 dominant | `measured_gaps_plumbing.json` | VERIFIED |
| Wasserstein-1, revision 4.0 (gaps < 600 mm) | insulation surface: → MEP **40.7**, → Plumbing 89.3, → pooled 58.9 mm; bare surface: 67.7 / 117.4 / 86.3 mm | `python verify/compare_gaps.py`, test-pinned | VERIFIED (computed) |
| Wasserstein-1, revision 3.0 | envelope draw (the paper's definition): 40.7 / 89.3 / 58.9; insulation surface: 88.5 / 137.6 / 106.9; bare: 109.9 / 159.6 / 128.4 mm | `python verify/compare_gaps.py --version 3.0`, test-pinned | VERIFIED (computed) |
| Baselines | fixed 25 mm gap → MEP 138.5 mm; MEP ↔ Plumbing (real-to-real) 49.9 mm | same | VERIFIED (computed) |
| Re-execution of the IFC measurement | not re-run for 4.0.0 | the Duplex files are not redistributed here and buildingSMART's sample repository has been reorganised; `measure_ifc.py --self-check` compares any re-run with the shipped sample | OUTSTANDING |

## 8. Reproducibility

| Item | Value | Status |
|---|---|---|
| Byte-exact regeneration of all eight files (both revisions) | SHA-256 in `RELEASE_CHECKSUMS.txt`; `tests/test_release.py`; CI on Python 3.9–3.13 × NumPy 1.26 / 2.0 / latest | VERIFIED |
| `total_load_kN` | `round(math.fsum(loads), 2)` — exactly rounded; plain `sum()` differs on Python ≤ 3.11 for 28 contexts | VERIFIED (fixed 3.5.0) |
| File format | compact JSON, ASCII-escaped, no trailing newline | VERIFIED |
| Random stream | NumPy `Generator` (PCG64) from the split seed; draw order frozen and identical across revisions (two quirks marked `# stream:`) | VERIFIED |

## 9. Outstanding
- Verbatim reproduction of ASME B31.1 Table 121.5 / MSS SP-58 Table 4 (paywalled; library check).
- Re-running `verify/measure_ifc.py` on the Duplex models and committing the report.
- Per-group (co-planar bank) stagger with re-calibration against the measured elevation spread.
