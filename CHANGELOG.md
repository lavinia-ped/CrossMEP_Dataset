# Changelog

Version lineage. The data files carry a **data revision** (directory, file name
and the embedded `version`): 3.0 = the files the CIB W78 2026 paper was released
with (June 2026); 4.0 = this release. The paper refers to a **v3.4** internal
build whose element library was never published (README, "Versions and relation to the paper"). The
package version tracks code and documentation.

## 4.0.0 — 2026-10-05 (not yet tagged)

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

### Talk
- Slides 9, 10, 12 and 13 rebuilt on the new evidence (population medians, the
  held-out building, train / evaluate / report, next steps); a new appendix slide
  with the realism check in detail. 189 tests.

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

### Talk material
- `docs/CrossMEP_CIBW78_talk.pptx` (14 slides + 3 appendix, speaker notes) and `docs/TALK.md`:
  a ten-minute talk on the dataset; figures and every printed number regenerate from the
  released data (`scripts/make_figures.py`, `scripts/screenshot_gallery.js`, `docs/deck/build_deck.js`).
- Docs: the IFC measurement is described as recording gaps between flow-segment (bare pipe)
  surfaces, replacing an unverified statement that the model carries no insulation geometry.

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
