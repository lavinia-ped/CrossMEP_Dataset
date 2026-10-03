# CrossMEP

[![ci](https://github.com/lavinia-ped/CrossMEP_Dataset/actions/workflows/ci.yml/badge.svg)](https://github.com/lavinia-ped/CrossMEP_Dataset/actions/workflows/ci.yml)
Data: CC BY 4.0 · Code: MIT · Python ≥ 3.9 · generator needs only NumPy; the JSON files need nothing.

A tiered synthetic dataset of multi-trade MEP cross-sections for learning-based
structural support assembly (SSA) synthesis. Each **context** is one 2-D
cross-section perpendicular to a coordinated MEP run at a support location: the
pipes, cable trays, ducts and conduits a support must carry — geometry, service,
insulation, per-support load, position — and the surface it mounts to.
Deliberately **no assembly information** and **no labels**: feasible assemblies
are non-unique and catalog-dependent, so supervision comes from downstream
environment rules.

Paper: *CrossMEP: A Tiered Synthetic Dataset of Multi-Trade MEP Cross-Sections*,
Pedrollo, Gvadzabia, Graeber & Fischer, 43rd CIB W78 Conference, 2026.
Companion formulation: Pedrollo, Graeber & Fischer, ISARC 2026.

> **Release 3.5.0** — code, verification and documentation overhaul. The four data
> files are byte-identical to the June 2026 release (checksums in
> `RELEASE_CHECKSUMS.txt`) and regenerate byte-for-byte from the generator on
> every CI run. Two discrepancies between the paper and this public release are
> documented in [Known issues](#known-issues-and-discrepancies) — read them
> before citing numbers.

## Files

| file | contexts | elements | seed | purpose |
|---|---|---|---|---|
| `mep_contexts_v3.0_train.json` | 5,000 | 22,500 | 1000 | training (625 per tier) |
| `mep_contexts_v3.0_val.json` | 500 | 2,242 | 2000 | validation |
| `mep_contexts_v3.0_test.json` | 500 | 2,242 | 3000 | held-out test |
| `mep_contexts_v3.0_benchmark.json` | 1,000 | 4,500 | 42 | stratified benchmark (125 per tier) |

Tiers are assigned round-robin C1…C8 within each split; seeds are disjoint.
`mep_contexts_gallery.html` is an interactive gallery of the benchmark (filter
by tier / kind / trade / surface); `schema/context-v3.schema.json` is the JSON
Schema; `croissant.json` the ML-metadata card; `DATASHEET.md` the datasheet
(Gebru et al., 2021); `VERIFICATION_LOG.md` the audit of every constant;
`RESULTS.md` the numbers this release produces; `CHANGELOG.md` the version
lineage.

## Schema at a glance

Per element: `kind` (pipe | cable_tray | duct | conduit), `service`, `trade`,
`shape` (round | rect), `label`, bare `width_mm` × `height_mm`
(building-horizontal × vertical), `insulation_mm` (per side), `load_kN` (per
support point at the typical span), `level` (generative row index — metadata,
not a physical invariant), `along_mm` (offset along the surface, rows centred
on 0) and `out_mm` (standoff out from the surface, positive away). Per context:
`tier`, `surface` {kind ceiling | wall, substrate, thickness_mm}, `n_elements`,
`n_levels`, `total_load_kN`, `bundle_width_mm`. Units: mm, kN. On a wall the
section rotates: the extent *along* the surface is the element's height.

## Install

```bash
pip install -e ".[test]"          # generator + tests (NumPy, pytest, jsonschema, SciPy)
# or just: pip install numpy
```

Consuming the JSON files needs only the standard library:

```python
import json
data = json.load(open("mep_contexts_v3.0_benchmark.json"))
ctx = data["contexts"][0]
print(ctx["tier"], ctx["surface"]["kind"], len(ctx["elements"]))
```

```python
import crossmep.tasks as cm                       # stdlib only
data = cm.load("benchmark")
print(cm.per_tier_table(data))                    # medians per tier (RESULTS.md)
cm.filter_contexts(data, pipes=2, trays=1)        # exactly 2 pipes + 1 tray
cm.filter_contexts(data, ducts=(1, None))         # at least one duct
cm.catalog_coverage(data, [(48, 54, 2.5), (108, 114, 4.0)])
cm.congestion_score(ctx), cm.min_clear_gap(ctx)   # the two clearance metrics
cm.validate(ctx)                                  # full validator on a dict
```

## Reproduce the release

```bash
python -m crossmep generate --split benchmark --out benchmark.json
sha256sum benchmark.json RELEASE_CHECKSUMS.txt     # identical to the released file
python -m crossmep validate                       # validator + JSON Schema over all four files
python -m crossmep results                        # per-tier tables, kinds, catalog coverage
python verify/compare_gaps.py                     # section 5.2: lognormal fit, KS, Wasserstein-1
python -m pytest                                  # everything above as tests
```

Every CI run regenerates all four files and compares digests on Python 3.9–3.13
and NumPy 1.26 / 2.0 / latest, so a change in NumPy's `Generator` stream, in
the element library, or in the layout engine fails the build. Two details made
this possible and are worth knowing if you fork the generator:

* `total_load_kN` is `round(math.fsum(loads), 2)`. Python 3.12 switched `sum()`
  to compensated summation; with plain `sum()` 28 of the 7,000 released values
  flip at a `.xx5` boundary on Python ≤ 3.11. `fsum` is exactly rounded on every
  version.
* Files are compact JSON (`json.dumps(payload)`), ASCII-escaped, no trailing newline.
* The order of every random draw is part of the data format; two historical
  quirks are preserved and marked `# stream:` in `crossmep/generate.py`.

## Difficulty tiers (count-stratified)

Tier **Cn** contains exactly *n* elements (C1…C8); composition — kinds, trades,
services, surfaces, stacking — is marginalised within each tier so that element
count is the single controlled difficulty axis. C1 covers every kind (a lone
pipe of any service, a single tray, duct or conduit). Benchmark split, medians:

| tier | envelope clearance (mm) | total load (kN) | bundle width (mm) |
|---|---|---|---|
| C1 | — | 0.10 | 152 |
| C2 | 120 | 0.23 | 444 |
| C3 | 98 | 0.44 | 738 |
| C4 | 90 | 0.55 | 910 |
| C5 | 73 | 0.78 | 1266 |
| C6 | 76 | 1.21 | 1193 |
| C7 | 60 | 1.49 | 1411 |
| C8 | 62 | 1.71 | 1733 |

Load and width medians are monotone in count; the clearance medians are
near-monotone (C5/C6 and C7/C8 swap at 125 contexts per tier). Difficulty here
means scene complexity, not solver hardness. Full tables, including the
physical clear-gap column and the Table-1-style ranges on the train split, are
in `RESULTS.md` (`python -m crossmep results --split train`).

## Generate

```bash
python -m crossmep generate --n 320 --seed 7                      # round-robin C1..C8
python -m crossmep generate --n 200 --seed 7 --tier C5            # one tier
python -m crossmep generate --n 100 --pipes 3 --trays 1 --gallery my.html   # custom composition
```

```python
from crossmep import generate_dataset, generate_custom, validate_context
ctxs = generate_dataset(1000, seed=42)                       # == the benchmark split
generate_custom(100, pipes=3, trays=1)                       # exact composition
generate_custom(50, pipes=(2, 4), conduits=(2, 6), surface="ceiling")
generate_custom(20, pipes=2, trades=["chilled"], seed=7)
```

Custom scenes reuse the verified element library and the same layout rules
(fitted gaps, published clearance floor, calibrated stagger, wall drip rule), so
they are construction-valid by the same rules; they are tagged `tier: "custom"`
because realism *verification* attaches to the natural distribution.
The canonical splits stay frozen: comparable numbers always come from seed 42.
The v3.1 entry points `mep_context_sampler.py` and `crossmep_tasks.py` still
work and forward to the package.

## Validation and verification

Every context — released, regenerated or custom — passes `validate_context`:
field domains; pairwise clearance (any two elements separated *along* the
surface by their combined half-spans, insulation and 25 mm routing clearance per
side included, **or** *out* from it by their combined half-depths plus the same
clearance); per-row centring. Violations raise `ContextValidationError` (not
`assert`, so they survive `python -O`).

The verification chain is executable end to end:

1. **Constants.** Every per-support load is *computed* in `crossmep/library.py`
   from sourced primitives (EN 10255 wall thickness × 7,850 kg/m³ + water fill ×
   ASME B31.1 water-service spans under a floor rule; the 50 kg/m full-300-mm-tray
   datum; verbatim Walraven duct-weight cells; IEC 40 %-of-bore fill). The tests
   pin the derived values to the frozen tables of the release, and check that
   every element in the released files carries exactly the library's values.
   Sources and statuses: `VERIFICATION_LOG.md`.
2. **Layout statistics vs. a built project.** Clear gaps, run multiplicity and
   in-bundle elevation spread were measured on two discipline models of the
   openly licensed buildingSMART Duplex Apartment (MEP: 427 segments; Plumbing:
   231) with IfcOpenShell — procedure in `verify/measure_ifc.py`, samples in
   `verify/measured_gaps*.json`. `verify/compare_gaps.py` refits the gap
   lognormal (n = 73, μ = 5.018, σ = 0.848, KS p = 0.53 — equal to the
   generator's constants) and computes Wasserstein-1 distances under three gap
   definitions (next section).
3. **Conventions.** Tiering order, service banking, insulation schedules and
   the wall drip rule (0 violations in 2,913 wet/electrical pairs on the
   benchmark) are tested over hundreds of unseen seeds.

## Known issues and discrepancies

Both items are pinned by tests (`tests/test_verify.py`, `tests/test_release.py`)
so that they stay visible.

**1. The gap comparison in the paper (§5.2, Table 2) is not like-for-like.**
The generator samples a gap between *routing envelopes* (bare size + insulation
+ 25 mm per side). Because the 25 mm clearance floor is applied to that draw
*and* each element's span already carries 25 mm on both sides, the physical
surface-to-surface gap between neighbours is the draw **plus 50 mm**: no two
generated neighbours are ever closer than 75 mm, while 42 % of the measured MEP
gaps are. The paper's 41 mm Wasserstein-1 distance uses the envelope draw; the
like-for-like numbers from the released benchmark are:

| generated gap definition | median (mm) | min | W1 → MEP | W1 → Plumbing | W1 → pooled |
|---|---|---|---|---|---|
| envelope draw (paper) | 150 | 25 | **40.7** | 89.3 | 58.9 |
| insulation surface to surface | 200 | 75 | 88.5 | 137.6 | 106.9 |
| bare surface to surface (what the IFC measurement is) | 236 | 75 | 109.9 | 159.6 | 128.4 |

(fixed 25 mm gap: 138.5; the two real discipline models: 49.9 apart.) The
clearance medians of §5.1 (120 → 61 mm) are envelope clearances; physical clear
gaps are 50 mm larger. Removing the double-counted clearance is a one-line
geometry change that leaves the random stream untouched and brings the physical
gap distribution to exactly the 40.7 mm the paper reports — but it moves every
position in the files, so it is deferred to a data revision 4.0 rather than
applied silently to the published artifact.

**2. Several paper numbers come from an unpublished v3.4 build.** The paper
describes pipes modelled as function × material (carbon steel, copper,
stainless, plastic up to 125 mm), steel-deck / masonry / drywall substrates and
per-element span and kN/m fields. The public release is the v3.0 element library
(carbon steel DN15–100, concrete substrates). The layout engine is the same, so
§5.1 (clearance ordering), all of §5.2 and the split sizes reproduce exactly;
the composition-dependent numbers do not: the released benchmark has
2,529 pipes / 1,141 conduits / 569 trays / 261 ducts (paper Fig. 3a: 2,668 / 962
/ 576 / 294), catalog coverage 11.6 % overall, 9.2–13.6 % by tier (paper: 11.5 %,
8.4–13.2 %), and Table 1 / Fig. 4b differ in the same way. `RESULTS.md` is the
authoritative set of values for the public files.

## Repository layout

```
crossmep/            package: model · library · layout · generate · io · tasks · render · cli
mep_contexts_v3.0_*.json   the four released splits (frozen; see RELEASE_CHECKSUMS.txt)
schema/              JSON Schema (draft 2020-12)
verify/              IFC measurement procedure, measured samples, distribution comparison
tests/               159 checks: derivations, geometry, generation over seeds, byte-exact
                     regeneration, schema, paper numbers, metrics, CLI, legacy shims
```

## License

Data: CC BY 4.0 (`LICENSE-DATA`). Code: MIT (`LICENSE-CODE`). The dataset is
synthetic, contains no personal or project-identifying information, and **must
not be used for the structural design of real installations**.

## Citation

See `CITATION.cff`. Please cite the dataset paper (CIB W78 2026) and the
companion formulation paper (ISARC 2026).
