# Changelog

Version lineage. The data files carry a **data revision** (directory, file name
and the embedded `version`): 3.0 = the files the CIB W78 2026 paper was released
with (June 2026); 4.0 = the October 2026 geometry fix; 4.1 = this release. The paper refers to a **v3.4** internal
build whose element library was never published (README, "Versions and relation to the paper"). The
package version tracks code and documentation.

## 4.1.0 — 2026-10-06 (not yet tagged)

### Talk
- New slide 3, from the ISARC 2026 talk, drawn as a diagram: one cross-section in (structure and
  services), verified support designs out (a rod trapeze, checked; up to ten, ranked by cost), with
  the two words the talk relies on, *context* (the brief, what CrossMEP contains) and *assembly*
  (the answer, what a method produces). Slide 4 keeps the route-to-section figure, where practice
  stands and the three reasons synthesis resists automation.
- New slide 5: one section in, verified supports out as a flow with the approach as a black box
  (rule table, search or learned policy), a verifier and the three things any such method needs;
  kept generic because the approaches are unpublished.
- New slide 6: the idea behind the dataset. The real designs available sit in one corner of the
  design space; CrossMEP fills it by construction and without limit (a new seed is a new set),
  uniform over the tiers or any mix on request.
- The opening now runs hospital → one cross-section in, verified designs out → why it resists
  automation → what a method would look like → the design space → the dataset. 18 main slides,
  about 8:30; later slide numbers shift by three from 4.0.0.

### Data revision 4.1
- `data/v4.1/`: four splits on the same seeds, regenerated with four composition parameters
  changed after `verify/compare_composition.py` set the 4.0 choices against what hanger
  locations carry in the open clinic and duplex: the number of rows is drawn by element count
  (`P_SECOND_ROW_4_1`, `P_THIRD_ROW_4_1`) instead of two or three rows always above five
  elements; the next group repeats the previous kind with probability 0.5
  (`P_SAME_KIND_4_1`); a supply-and-return pair of equal ducts is an option
  (`OPTIONS_MULTI_4_1`); the DN bands widen at the top (`TRADE_DN_BAND_4_1`). Library and
  layout rules are those of 4.0; `Revision.composition` selects the parameter set, so 3.0
  and 4.0 regenerate byte-for-byte as before (tests).
- Element library: DN125 and DN150 (EN 10255 medium, 139.7 / 165.1 mm, 5.0 mm wall; ASME
  NPS 6 span 5.2 m; GEG insulation cap 100 mm) — drawn only by 4.1 bands.
- Consequences on the benchmark: 2,488 pipes / 968 conduits / 559 trays / 485 ducts; 19 % of
  contexts stacked (4.0: 56 %); clear-gap medians narrow at every tier (130 → 51 mm; the 4.0
  step at C6 is gone); clinic distance 32 mm (4.0: 28 mm; same gap draw, more insulation);
  catalog coverage 14.5 % (4.0: 11.6 %). The composition comparison is in sample for 4.1 and
  reported as a design check; the clinic stays held out for spacing.
- `scripts/make_results.py` assembles `RESULTS.md` from the release tooling; `RESULTS.md`
  regenerated (4.1 benchmark and train, 4.0 and 3.0 benchmark, all verification scripts).
  Checksums, croissant, galleries (`data/v4.0/` keeps the 4.0 gallery), figures, studio,
  deck and talk rebuilt on 4.1; the paper-era numbers stay pinned on the 4.0 files in the
  tests (`benchmark_v40` fixture) next to the 4.1 pins. 227 tests.

## 4.0.0 — 2026-10-05 (not yet tagged)

### Composition compared on the open buildings
- `verify/compare_composition.py` and `measure_ifc.section_bundles`: what each hanger
  location carries in the merged disciplines of the clinic (Plumbing + HVAC) and the duplex
  (MEP), against the benchmark contexts made of the same kinds: bundle sizes, kind shares,
  kind mixing and row stacking conditional on the count, pipe sizes by DN; bootstrap over
  physical bundles. Nothing is fitted. Findings in `RESULTS.md`, the log (section 6) and the
  DATASHEET; 14 tests in `tests/test_composition.py`; runs in CI.
- The Clinic and Duplex Electrical models were opened and contain no flow segments
  (recorded with SHA-256 in `verify/measured/README.md`), so the electrical share stays
  declared; the Duplex Plumbing model duplicates most MEP pipes and is not merged.

### Verification log
- Sources upgraded without changing any value (data byte-identical): tray widths are the
  NEMA VE 1 series (VERIFIED); the pipe spans are confirmed by the ASHRAE Handbook hanger
  table (VERIFIED, two concordant sources); the conduit span follows the IET On-Site Guide
  table under BS 7671 (VERIFIED); the wall rule follows BS 7671 Reg. 528.3.2 (VERIFIED);
  the tray span is bracketed by the NEMA VE 1 class spans and the duct span by the SMACNA
  Table 5-1 maximum (PRACTICE-CITED); the tiering criteria cite Korman, Fischer & Tatum (2003).
- New section 10, "Why these standards": the four selection rules, the preference order
  of sources and the alternatives not used (BS EN 806-4, NEC, DIN 4140, DW/144); section 11
  lists the public texts used for the checks; section 9 lists the value changes deferred to
  a data revision 4.1.

### Talk
- `docs/CrossMEP_CIBW78_talk.pptx` and its PDF (16 slides + 5 appendix, speaker notes on
  every slide) and `docs/TALK.md` (the same talk as a script, with a pre-talk checklist and
  questions and answers). Figures and every printed number regenerate from the released
  data (`scripts/make_figures.py`, `scripts/screenshot_gallery.js`,
  `scripts/screenshot_studio.js`, `docs/deck/build_deck.js`).
- Speech rewritten in a natural spoken style for recording (about 1,300 words, marks at 145 words a minute); `docs/TALK_to_record.md` is the read-aloud text only, with recording tips.
- Every slide title is a sentence that carries its message (for example "Spacing holds up on a clinic the generator never saw") instead of a topic label; numbers in titles are computed from the data.
- Experiments framed by what they show: Experiment 1 (slide 10) is a design check, since the
  tier fixes the count and load and congestion follow from the rules; Experiment 2 (slide
  11) is the independent test (gap distribution fitted on the duplex, clinic held out),
  stated with its noise floor; Experiment 3 (slide 12) is a use of the dataset.
- Slides 2 and 3 adapted from the ISARC 2026 talk (the support assemblies of a hospital; the synthesis problem and why it resists automation), without product names, logos or tool screenshots; all text in Calibri.
- New slide 13, a live demo of the Generator Studio (parameters, section and 3D, QR code);
  slides 14 (train / evaluate / report) and 15 (scope, next) rebuilt; appendix slides 17
  (two more studio sections) and 19 (the realism check in detail).
- "Every number traced" replaced by "every constant sourced or declared a design choice",
  and "checked against two open buildings" narrowed to the pipe gaps that were checked.
- Docs: the IFC measurement is described as recording gaps between flow-segment (bare pipe)
  surfaces, replacing an unverified statement that the model carries no insulation geometry.

### Generator Studio
- `docs/studio/index.html` (built by `scripts/build_studio.py`): set the generator's
  parameters (tier or exact composition, surface, seed) and browse its real outputs
  with drawings, element tables, closest-pair dimensions, the spacing drawn and the
  reproducing Python call. `tests/test_studio.py` checks the embedded data against
  fresh runs.
- Simplified for demonstrations: one bar of parameters and *Generate another*; the
  section drawn as an A4 support detail (standard scale, callouts with size, trade,
  level or wall offset and load, overall and clear-gap dimensions, notes, title
  block) beside the 3D model; schedule, Python call, rules and spacing under
  *Details*. Callout leaders are placed to cross no other service: over all 2,936
  stored sections, 3 leaders cross a service, 6 pairs of leaders cross and 2
  clear-gap figures touch a service (checked in a headless browser).

### Verification on sections of two open buildings
- `verify/measure_ifc.py` rewritten: the models are cut into sections every 250 mm
  (the definition of a context) and the clear gap between side-by-side runs is
  measured; the geometry core needs no IfcOpenShell and is unit-tested. Measured
  the buildingSMART Duplex Apartment (MEP, Plumbing) and Medical-Dental Clinic
  (Plumbing, HVAC) models, CC BY 4.0; records, meshed segment tables, SHA-256 of
  the sources and attribution in `verify/measured/`.
- `verify/compare_sections.py`: generated vs measured pipe gaps with Wasserstein-1,
  95 % bootstrap intervals (contexts / pipe pairs), the noise floor of each sample,
  real-to-real distances, a fixed-gap baseline and a sensitivity analysis over 11
  cut settings. Generated ↔ clinic (held out) 28 mm (16–44); duplex MEP ↔
  Plumbing 26; generated ↔ duplex 70 / 85; clinic ↔ duplex 71 / 85; revision 3.0
  ↔ clinic 65.
- The June 2026 duplex samples (`measured_gaps*.json`, the source of the
  generator's gap fit and of the paper's §5.2 numbers) do not regenerate with the
  procedure documented at the time (re-run: 131 gaps, median −24 mm, against 103,
  median 108). Kept and documented; the old procedure remains as
  `measure_ifc.py --legacy`.

### Experiment 1 with intervals
- `verify/tier_trends.py`: benchmark medians with bootstrap intervals, the median
  of 2,000 generated contexts per tier, steps between tiers and Spearman's ρ.
  Load rises at every tier; the clear gap shrinks overall (ρ −0.36) but widens at
  C6, where the generator starts stacking in two or three rows (5 → 3 elements per
  row), and bundle width dips there too. The README's earlier statement that width
  medians are monotone was wrong and is corrected.

### Evaluation harness
- `crossmep/evaluate.py` (stdlib) and `python -m crossmep evaluate`: per-tier
  results with Wilson (binary) or bootstrap (continuous) intervals, tier-balanced
  and weighted means, the first tier whose interval lies below a threshold, and
  paired comparisons (stratified paired bootstrap, exact McNemar). Missing or
  unknown context ids are errors.

### Data revision 4.0
- **Removed the double-counted clearance.** Revision 3.0 laid elements out with a
  25 mm routing envelope on each side *and* a 25 mm floor on the sampled gap, so
  neighbours sat sampled gap + 50 mm apart (never closer than 75 mm). In 4.0 the
  sampled, measurement-fitted gap is the physical gap between insulation surfaces,
  floored at 25 mm. The random stream is untouched: every element, load, row and
  standoff is identical to 3.0; along-positions and bundle widths change.
  Consequences on the benchmark: minimum pairwise clear gap medians 120 → 61.7 mm
  (C2 → C8) are now physical; Wasserstein-1 to the measured Duplex MEP gaps is
  40.7 mm at the insulation surface (3.0: 88.5) and 67.7 mm bare (3.0: 110).
- **Per-element `span_m` and `load_kN_per_m`** recorded, so `load_kN =
  load_kN_per_m × span_m` can be checked by hand and the span exposed as a
  variable downstream.
- `bundle_width_mm` is the physical extent (3.0 included 50 mm of empty envelope).
- Files moved to `data/v4.0/`; the 3.0 files kept under `data/v3.0/`, byte-reproducible
  (`python -m crossmep generate --split <s> --version 3.0`); `schema/context-v4.schema.json`.
- Validator is physical and shared by both revisions: insulation surfaces of any
  two elements at least 25 mm apart along the surface or out from it.
- Metrics: `tasks.min_clear_gap` (= `congestion_score`) is the physical definition;
  `tasks.envelope_clearance` keeps the 3.0 definition for the paper's files.

### Catalog stress test (paper section 5.3)
- `crossmep/catalog.py` (stdlib): the question stated precisely: attach-diameter rules
  (`service`, `bare`, `insulated`), size bins with capacity, bin-edge tolerance, and a
  single reason for every miss (`not_pipe`, `size`, `load`). `tasks.catalog_coverage`
  delegates to it and returns the same numbers as before.
- `verify/catalog_stress.py` (NumPy): the paper's single number with cluster-bootstrap
  95 % intervals over contexts (overall, per tier, per split), a Monte Carlo population
  estimate from the generator, the sizes that are attached, sensitivity to the diameter
  rule and bin tolerance, and an exact catalog-independent demand curve (best share of
  pipes that k clamp sizes of a given window width could attach). Any catalog can be
  passed with `--bins`.
- Findings on the released benchmark: the paper's two bins attach 11.6 % of pipes
  (95 % CI 10.1–13.0), all of them DN40; load never binds (0.88 kN vs 2.5 kN); DN100
  sits 0.3 mm above the 108–114 mm bin, so the headline moves to 12.9 % with 0.5 mm
  tolerance; two best-placed 6 mm sizes would attach 43 %, six 80 %.
- 36 tests (`tests/test_catalog.py`), including the DP against brute force and the
  bootstrap's coverage on synthetic clustered data. Edge case fixed: a bootstrap
  resample with no pipe is left out instead of turning the interval into NaN.

### Code, verification and documentation (from the 3.5.0 overhaul, same branch, never tagged)
- All splits of both revisions regenerate **byte-for-byte**; `RELEASE_CHECKSUMS.txt`
  lists the SHA-256 digests and CI compares them on Python 3.9–3.13 and NumPy 1.26/2.0/latest.
- Fixed `total_load_kN` to `round(math.fsum(...), 2)`: Python 3.12 changed `sum()` to
  compensated summation; with plain `sum()` 28 of the 7,000 released values differ on
  Python ≤ 3.11. The release was built on 3.12; it now reproduces on every version.
- Fixed the writer: released files are compact JSON; the v3.1 CLI wrote `indent=2`
  and omitted the schema-required `split` key. `crossmep_tasks.py` failed to import
  on Python < 3.12 (backslash inside an f-string).
- Single 847-line module replaced by the `crossmep` package: `model`, `library`
  (every constant with its source; loads **derived** from primitives), `layout`,
  `generate`, `io`, `tasks` (stdlib-only), `render`, `cli`
  (`python -m crossmep generate | validate | results | gallery | checksums`).
  `mep_context_sampler.py` and `crossmep_tasks.py` remain as shims.
- Validator raises `ContextValidationError` instead of `assert`; generation validates
  every context by construction.
- `verify/compare_gaps.py` reproduces section 5.2 from the shipped measurements
  (lognormal fit n = 73, μ = 5.018, σ = 0.848, KS p = 0.53; baselines 138.5 / 49.9 mm)
  for every gap definition; `verify/measure_ifc.py` makes the IfcOpenShell procedure
  executable with a `--self-check`.
- Tests 41 → 189: derived constants pinned; every released element checked against
  the library; validator unit tests; invariants over 29 seeds; byte-exact regeneration
  of eight files; schema conformance; paper numbers that reproduce and the released
  values of those that do not; metric unit tests; CLI and shims.
- README, DATASHEET, VERIFICATION_LOG rewritten to match the code (tray height 60 mm,
  not 100; stagger 0/75/120, not 55/75/120; unified W1 figures; test counts and tier
  names corrected; placeholders removed); `CITATION.cff` valid with all four authors;
  Croissant metadata with checksums; `RESULTS.md` generated by the CLI; schemas tightened.
- Removed tracked `.pyc` / `.DS_Store` files, duplicated and contradictory comments,
  a reference to a private code base and an internal publishing note.

## 3.0 — June 2026 (data revision 3.0; "zero-invention" release)
- Stratification by exact element count (C1–C8), composition marginalised; filtering
  and custom-generation API.
- No invented physical numbers: spans restricted to verbatim ASME B31.1 published points
  (floor rule); duct sizes restricted to verbatim Walraven table cells (all EN 1505
  preferred dimensions); clearance floor set to the published 25 mm pipe-rack minimum;
  gap lognormal refit on the > 25 mm measured population (n = 73, KS p = 0.53); duct
  insulation removed (no verified source).

## 2.0
- All load constants re-grounded in published engineering data; conduits and round
  spiral ducts added; gaps sampled from a lognormal fitted to measured Duplex gaps;
  half-normal stagger calibrated to measured elevation spread; verification widened to
  the Duplex Plumbing model; wall drip-avoidance rule enforced; JSON Schema, tests,
  Croissant metadata. (Scene-stratified tiers T1–T4; superseded by 3.0.)
