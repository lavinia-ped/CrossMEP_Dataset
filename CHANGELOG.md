# Changelog

Version lineage: the four data files carry data revision **3.0** (file names and
the embedded `version`), unchanged since June 2026. The v3.1 label in the old
generator CLI and `CITATION.cff` referred to code only. The CIB W78 2026 paper
refers to a **v3.4** internal build whose element library was never published
(see README, "Known issues"). **3.5.0** is this repository release: code,
verification and documentation; data byte-identical.

## 3.5.0 — 2026-10-03

Scientific rigor and reproducibility release. No change to the released data.

### Reproducibility
- All four splits regenerate **byte-for-byte** from the generator; `RELEASE_CHECKSUMS.txt`
  lists the SHA-256 digests and CI compares them on Python 3.9–3.13 and NumPy 1.26/2.0/latest.
- Fixed `total_load_kN` to `round(math.fsum(...), 2)`. Python 3.12 changed `sum()` to
  compensated summation; with plain `sum()` 28 of the 7,000 released values differ on
  Python ≤ 3.11. The release was built on 3.12; it now reproduces on every version.
- Fixed the writer: released files are compact JSON; the v3.1 CLI wrote `indent=2`
  (and omitted the `split` key, so its output never validated against the schema).
- `crossmep_tasks.py` failed to import on Python < 3.12 (backslash inside an f-string).

### Code
- Single 847-line module replaced by the `crossmep` package: `model` (data model,
  validator), `library` (every constant with its source; loads **derived** from
  primitives), `layout` (rows, fitted gaps, stagger), `generate` (tiers, custom API),
  `io` (release format), `tasks` (stdlib-only loader and metrics), `render`, `cli`.
- Validator raises `ContextValidationError` instead of `assert`; now also enforces the
  clearance floor in the out direction and field domains. Generation validates every
  context by construction.
- `python -m crossmep generate | validate | results | gallery | checksums`.
  `mep_context_sampler.py` and `crossmep_tasks.py` remain as compatibility shims.
- Removed duplicated and contradictory comments (e.g. "no interpolated spans" next
  to "DN32/40 interpolated"), the stale T1–T4 docstring, a reference to a private
  code base, tracked `.pyc` / `.DS_Store` files, and an internal publishing note.

### Verification
- `verify/compare_gaps.py` reproduces section 5.2 from the shipped measurements
  (lognormal fit n = 73, μ = 5.018, σ = 0.848, KS p = 0.53; W1 40.7 / 89.3 / 58.9 mm;
  fixed-gap baseline 138.5; real-to-real 49.9) and adds the like-for-like
  surface-to-surface comparison (88.5 / 137.6 / 106.9 mm) — see README "Known issues".
- `verify/measure_ifc.py`: the IfcOpenShell measurement procedure with explicit
  parameters and a `--self-check` against the shipped samples.
- New metric `tasks.min_clear_gap` (physical) alongside the released
  `congestion_score` (envelope); `neighbour_gaps(kind=...)` exposes both definitions.

### Tests (41 → 159)
- Derived constants pinned to the frozen tables; every released element checked
  against the library; validator unit tests; generation invariants over 29 seeds;
  byte-exact regeneration of all four splits; schema conformance of released and
  CLI-generated files; paper numbers that reproduce (and the released values of
  those that do not); metric unit tests on hand-built contexts; CLI and shims.

### Documentation
- README, DATASHEET and VERIFICATION_LOG rewritten to match the code: tray height is
  60 mm (log said 100), stagger scales are 0/75/120 mm (log said 55/75/120), W1 figures
  unified (log mixed v2.0 and v3.0 values), measured IQRs restated, test counts and
  tier names (T1–T4) corrected, placeholders (`<USER>`, `<ZENODO-DOI>`) removed.
- `CITATION.cff`: valid `cff-version` (was 3.1.0), all four paper authors.
- `RESULTS.md`: generated tables for the public files.
- JSON Schema tightened (`additionalProperties: false`, service and substrate enums).

## 3.0 — June 2026 (data revision 3.0; "zero-invention" release)
- Stratification by exact element count (C1–C8), composition marginalised; filtering
  and custom-generation API.
- No invented physical numbers: spans restricted to verbatim ASME B31.1 published points
  (floor rule); duct sizes restricted to verbatim Walraven table cells (all EN 1505
  preferred dimensions); clearance floor set to the published 25 mm pipe-rack minimum
  everywhere; gap lognormal refit on the > 25 mm measured population (n = 73, KS p = 0.53);
  duct insulation removed (no verified source).

## 2.0
- All load constants re-grounded in published engineering data; conduits and round
  spiral ducts added; gaps sampled from a lognormal fitted to measured Duplex gaps;
  half-normal stagger calibrated to measured elevation spread; verification widened to
  the Duplex Plumbing model; wall drip-avoidance rule enforced; JSON Schema, tests,
  Croissant metadata. (Scene-stratified tiers T1–T4; superseded by 3.0.)
