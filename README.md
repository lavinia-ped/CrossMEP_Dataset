# CrossMEP

[![ci](https://github.com/lavinia-ped/CrossMEP_Dataset/actions/workflows/ci.yml/badge.svg)](https://github.com/lavinia-ped/CrossMEP_Dataset/actions/workflows/ci.yml)
Data: CC BY 4.0 · Code: MIT · Python ≥ 3.9 · generator needs only NumPy; the JSON files need nothing.

A tiered synthetic dataset of multi-trade MEP cross-sections for learning-based
structural support assembly (SSA) synthesis.

**In practitioner terms.** Pick one hanger location on a coordinated corridor
run and cut the section. What the support designer receives is exactly that
section: which services pass (pipes by DN and service, cable trays, ducts,
conduit groups), their bare size and insulation, what each weighs per metre and
at the support spacing it was sized for, how far apart they are, how they stack,
and what they hang from (slab or wall, substrate, thickness). CrossMEP is that
section in numbers — 7,000 of them — with the spacing and stacking drawn to match
measurements on a built project, and **nothing about the support itself**: no
channel, rods, clamps or anchors, because that is the answer the dataset exists
to let a method find.

Paper: *CrossMEP: A Tiered Synthetic Dataset of Multi-Trade MEP Cross-Sections*,
Pedrollo, Gvadzabia, Graeber & Fischer, 43rd CIB W78 Conference, 2026.
Companion formulation: Pedrollo, Graeber & Fischer, ISARC 2026.

> **Release 4.0.0 / data revision 4.0.** The paper's files (revision 3.0) laid
> elements out with a 25 mm routing envelope on each side *in addition to* the
> 25 mm minimum gap, so neighbours sat 50 mm further apart than the sampled,
> measurement-fitted gap. Revision 4.0 removes that double-counting. Every
> element, load, row and standoff is unchanged — only the along-surface
> positions and bundle widths move — and the paper's verification numbers now
> hold for the physical geometry. The 3.0 files stay in `data/v3.0/`,
> byte-reproducible, for anyone citing the paper. Details in
> [Known issues](#known-issues-and-discrepancies).

## Files

| revision | file | contexts | elements | seed | purpose |
|---|---|---|---|---|---|
| 4.0 | `data/v4.0/mep_contexts_v4.0_train.json` | 5,000 | 22,500 | 1000 | training (625 per tier) |
| 4.0 | `data/v4.0/mep_contexts_v4.0_val.json` | 500 | 2,242 | 2000 | validation |
| 4.0 | `data/v4.0/mep_contexts_v4.0_test.json` | 500 | 2,242 | 3000 | held-out test |
| 4.0 | `data/v4.0/mep_contexts_v4.0_benchmark.json` | 1,000 | 4,500 | 42 | stratified benchmark (125 per tier) |
| 3.0 | `data/v3.0/mep_contexts_v3.0_*.json` | same | same | same | the paper release (frozen) |

Tiers are assigned round-robin C1…C8 within each split; seeds are disjoint; the
two revisions contain the same elements in the same rows. SHA-256 digests of all
eight files are in `RELEASE_CHECKSUMS.txt`. `mep_contexts_gallery.html` is an
interactive gallery of the 4.0 benchmark (filter by tier / kind / trade /
surface; `data/v3.0/` holds the 3.0 one); `schema/` the JSON Schemas;
`croissant.json` the ML-metadata card; `DATASHEET.md` the datasheet (Gebru et
al., 2021); `VERIFICATION_LOG.md` the audit of every constant; `RESULTS.md` the
numbers this release produces; `CHANGELOG.md` the version lineage.

## Schema at a glance

Per element: `kind` (pipe | cable_tray | duct | conduit), `service`, `trade`,
`shape` (round | rect), `label`, bare `width_mm` × `height_mm`
(building-horizontal × vertical), `insulation_mm` (per side), `load_kN` (per
support point), `span_m` (the support spacing that load was derived at) and
`load_kN_per_m` (so `load_kN = load_kN_per_m × span_m`), `level` (generative row
index — metadata, not a physical invariant), `along_mm` (offset along the
surface, rows centred on 0) and `out_mm` (standoff out from the surface, positive
away). Per context: `tier`, `surface` {kind ceiling | wall, substrate,
thickness_mm}, `n_elements`, `n_levels`, `total_load_kN`, `bundle_width_mm`.
Units: mm, kN, m. On a wall the section rotates: the extent *along* the surface
is the element's height. Revision 3.0 files carry the same fields without
`span_m` / `load_kN_per_m`.

## Install

```bash
pip install -e ".[test]"          # generator + tests (NumPy, pytest, jsonschema, SciPy)
# or just: pip install numpy
```

Consuming the JSON files needs only the standard library:

```python
import json
data = json.load(open("data/v4.0/mep_contexts_v4.0_benchmark.json"))
ctx = data["contexts"][0]
print(ctx["tier"], ctx["surface"]["kind"], len(ctx["elements"]))
```

```python
import crossmep.tasks as cm                       # stdlib only
data = cm.load("benchmark")                       # revision 4.0; cm.load("benchmark", "3.0") for the paper files
print(cm.per_tier_table(data))                    # medians per tier (RESULTS.md)
cm.filter_contexts(data, pipes=2, trays=1)        # exactly 2 pipes + 1 tray
cm.filter_contexts(data, ducts=(1, None))         # at least one duct
cm.catalog_coverage(data, [(48, 54, 2.5), (108, 114, 4.0)])
cm.min_clear_gap(ctx)                             # minimum pairwise physical clear gap (= congestion_score)
cm.validate(ctx)                                  # full validator on a dict
```

## Reproduce the release

```bash
python -m crossmep generate --split benchmark --out benchmark.json      # revision 4.0
python -m crossmep generate --split benchmark --version 3.0 --out b3.json
sha256sum benchmark.json b3.json; cat RELEASE_CHECKSUMS.txt           # identical digests
python -m crossmep validate                       # validator + JSON Schema over all eight files
python -m crossmep results                        # per-tier tables, kinds, catalog coverage
python verify/compare_gaps.py                     # section 5.2: lognormal fit, KS, Wasserstein-1
python -m pytest                                  # everything above as tests
```

Every CI run regenerates all eight files and compares digests on Python 3.9–3.13
and NumPy 1.26 / 2.0 / latest, so a change in NumPy's `Generator` stream, in
the element library, or in the layout engine fails the build. Three details are
worth knowing if you fork the generator:

* `total_load_kN` is `round(math.fsum(loads), 2)`. Python 3.12 switched `sum()`
  to compensated summation; with plain `sum()` 28 of the 7,000 released values
  flip at a `.xx5` boundary on Python ≤ 3.11. `fsum` is exactly rounded on every
  version.
* Files are compact JSON (`json.dumps(payload)`), ASCII-escaped, no trailing newline.
* The order of every random draw is part of the data format; the two revisions
  differ only in layout arithmetic, never in a draw, and two historical quirks
  are preserved and marked `# stream:` in `crossmep/generate.py`.

## Difficulty tiers (count-stratified)

Tier **Cn** contains exactly *n* elements (C1…C8); composition — kinds, trades,
services, surfaces, stacking — is marginalised within each tier so that element
count is the single controlled difficulty axis. C1 covers every kind (a lone
pipe of any service, a single tray, duct or conduit). Benchmark split, revision
4.0, medians:

| tier | min. clear gap (mm) | total load (kN) | bundle width (mm) |
|---|---|---|---|
| C1 | — | 0.10 | 102 |
| C2 | 120 | 0.23 | 344 |
| C3 | 98 | 0.44 | 613 |
| C4 | 90 | 0.55 | 728 |
| C5 | 73 | 0.78 | 1027 |
| C6 | 76 | 1.21 | 993 |
| C7 | 60 | 1.49 | 1138 |
| C8 | 62 | 1.71 | 1448 |

The clear gap is the physical gap between insulation surfaces; these are the
values of the paper's §5.1 (120 → 61 mm). Load and width medians are monotone in
count; clearance is near-monotone (C5/C6 and C7/C8 swap at 125 contexts per
tier). Difficulty here means scene complexity, not solver hardness. Full tables,
the Table-1-style ranges on the train split and the 3.0 values are in
`RESULTS.md`.

## Generate

```bash
python -m crossmep generate --n 320 --seed 7                      # round-robin C1..C8
python -m crossmep generate --n 200 --seed 7 --tier C5            # one tier
python -m crossmep generate --n 100 --pipes 3 --trays 1 --gallery my.html   # custom composition
```

```python
from crossmep import generate_dataset, generate_custom, validate_context
ctxs = generate_dataset(1000, seed=42)                       # == the 4.0 benchmark split
generate_dataset(1000, seed=42, revision="3.0")              # == the paper's benchmark
generate_custom(100, pipes=3, trays=1)                       # exact composition
generate_custom(50, pipes=(2, 4), conduits=(2, 6), surface="ceiling")
generate_custom(20, pipes=2, trades=["chilled"], seed=7)
```

Custom scenes reuse the verified element library and the same layout rules
(fitted gaps, 25 mm clearance floor, calibrated stagger, wall drip rule), so
they are construction-valid by the same rules; they are tagged `tier: "custom"`
because realism *verification* attaches to the natural distribution. The
canonical splits stay frozen: comparable numbers always come from seed 42. The
v3.x entry points `mep_context_sampler.py` and `crossmep_tasks.py` still work
and forward to the package.

## What is encoded, and where it comes from

Every number has a source and a status (`VERIFICATION_LOG.md`), and every
per-support load is *computed* in `crossmep/library.py` from those sources:

* **Pipes** — EN 10220 / EN 10255 medium-series carbon steel, DN15–100, water
  filled; support spans from ASME B31.1 Table 121.5 water-service points under a
  floor rule (no interpolation); insulation per GEG Anlage 8 (heated lines) and
  a 30/50 mm condensation-control schedule (chilled); grouped as trades run
  (domestic hot + cold pairs, heating flow + return, chilled banks, a sprinkler
  main with an optional branch).
* **Cable trays** — IEC 61537 systems, 150–600 mm wide, loaded on a
  design-for-full basis from the published 50 kg/m full-300-mm-tray datum.
* **Ducts** — EN 1505 preferred rectangular sizes with verbatim manufacturer
  duct-weight cells (flange and bracing included); EN 1506 round spiral sizes.
* **Conduits** — IEC 61386-1 metric sizes in parallel groups of 2–6, steel
  tube plus IEC 40 %-of-bore cable fill.
* **Layout** — bulky services nearest the slab (ducts, then trays and conduits,
  then pipes); clear gaps from a lognormal fitted to gaps measured on the open
  Duplex Apartment MEP model above the 25 mm pipe-rack minimum; half-normal
  within-row stagger calibrated to the measured in-bundle elevation spread; on
  walls, electrical containment kept above wet services.

What is *not* encoded is stated as plainly: duct insulation (no verified
thickness source), gravity drainage (slope cannot be represented in one
section), anchor capacity, and anything about the support. Trade mix, surface
split and size bands are design parameters, not survey results.

## Validation and verification

Every context — released, regenerated or custom — passes `validate_context`:
field domains; pairwise clearance (the insulation surfaces of any two elements
are at least 25 mm apart *along* the surface **or** *out* from it); per-row
centring. Violations raise `ContextValidationError` (not `assert`, so they
survive `python -O`). The validator is physical and is applied to both
revisions.

The verification chain is executable end to end:

1. **Constants.** Loads derive from sourced primitives (EN 10255 wall thickness
   × 7,850 kg/m³ + water fill × B31.1 spans; the tray datum; Walraven cells; IEC
   fill). Tests pin the derived values to the frozen release tables and check
   every element in the released files against the library, including the
   recorded `span_m` and `load_kN_per_m`.
2. **Layout statistics vs. a built project.** Clear gaps, run multiplicity and
   in-bundle elevation spread were measured on two discipline models of the
   openly licensed buildingSMART Duplex Apartment (MEP: 427 segments; Plumbing:
   231) with IfcOpenShell — procedure in `verify/measure_ifc.py`, samples in
   `verify/measured_gaps*.json`. `verify/compare_gaps.py` refits the gap
   lognormal (n = 73, μ = 5.018, σ = 0.848, KS p = 0.53 — equal to the
   generator's constants) and computes Wasserstein-1 distances for each gap
   definition. Revision 4.0 benchmark:

   | generated gap | median (mm) | min | W1 → MEP | W1 → Plumbing | W1 → pooled |
   |---|---|---|---|---|---|
   | insulation surface to surface (the sampled gap) | 150 | 25 | **40.7** | 89.3 | 58.9 |
   | bare surface to surface (what an uninsulated IFC model yields) | 186 | 25 | 67.7 | 117.4 | 86.3 |

   Baselines: a fixed 25 mm modular gap scores 138.5 mm; the two real discipline
   models are 49.9 mm apart. The bare-surface row is the strictly like-for-like
   one (the Duplex model carries no insulation geometry); the difference between
   the rows is the insulation the generator adds to 58 % of adjacent pairs.
3. **Conventions.** Tiering order, service banking, insulation schedules and
   the wall drip rule (0 violations in 2,913 wet/electrical pairs on the
   benchmark) are tested over hundreds of unseen seeds.

## Known issues and discrepancies

Both are pinned by tests so that they stay visible.

**1. Revision 3.0 double-counted the clearance (fixed in 4.0).** The 3.0
generator sampled a gap between *routing envelopes* (bare size + insulation +
25 mm per side) and floored that draw at 25 mm, so the physical gap between
neighbours was the draw **plus 50 mm**: no two generated neighbours were closer
than 75 mm, while 42 % of the measured MEP gaps are. The paper's Table 2 / §5.2
figure of 41 mm (Wasserstein-1) was computed on the envelope draw; measured
like-for-like on the 3.0 files it is 88.5 mm (insulation surface) / 110 mm
(bare surface). Revision 4.0 makes the draw the physical gap: 40.7 mm at the
insulation surface, 67.7 mm bare, and the §5.1 clearance medians (120 → 61 mm)
become physical clear gaps instead of envelope clearances. `python
verify/compare_gaps.py --version 3.0` prints the 3.0 numbers.

**2. Several paper numbers come from an unpublished v3.4 build.** The paper
describes pipes modelled as function × material (carbon steel, copper,
stainless, plastic up to 125 mm), steel-deck / masonry / drywall substrates and
per-element span and kN/m fields. The public release is the v3.0 element library
(carbon steel DN15–100, concrete substrates; 4.0 adds the span and kN/m fields).
The layout engine is the same, so §5.1 (clearance ordering), all of §5.2 and the
split sizes reproduce exactly; the composition-dependent numbers do not: the
released benchmark has 2,529 pipes / 1,141 conduits / 569 trays / 261 ducts
(paper Fig. 3a: 2,668 / 962 / 576 / 294), catalog coverage 11.6 % overall,
9.2–13.6 % by tier (paper: 11.5 %, 8.4–13.2 %), and Table 1 / Fig. 4b differ in
the same way. `RESULTS.md` is the authoritative set of values for the public
files.

**Modelling simplifications worth knowing.** Stagger is drawn per element, so
two pipes of one bank can sit at different standoffs, whereas a bank on a shared
trapeze would be co-planar; row spacing is a fixed 120 mm clear plus stagger
rather than a trapeze depth; pipe sizes stop at DN100 and substrates at
concrete. Each is a deliberate scope boundary of this revision, listed in
`DATASHEET.md`.

## Presenting the dataset

`docs/TALK.md` is a ten-minute talk for a construction audience (slide by
slide, with speaker notes and the questions practitioners ask), and
`docs/figures/` holds its figures, regenerated from the released data by
`python scripts/make_figures.py` (`pip install matplotlib`).

## Repository layout

```
crossmep/            package: model · library · layout · generate · io · tasks · render · cli
data/v4.0/           current data revision (four splits)
data/v3.0/           the paper release (four splits + its gallery), frozen
schema/              JSON Schemas (draft 2020-12) for revisions 3.x and 4.x
verify/              IFC measurement procedure, measured samples, distribution comparison
scripts/             figure generation
docs/                talk narrative and figures
tests/               119 checks: derivations, geometry, generation over seeds, byte-exact
                     regeneration of both revisions, schema, paper numbers, metrics, CLI, shims
```

## License

Data: CC BY 4.0 (`LICENSE-DATA`). Code: MIT (`LICENSE-CODE`). The dataset is
synthetic, contains no personal or project-identifying information, and **must
not be used for the structural design of real installations**.

## Citation

See `CITATION.cff`. Please cite the dataset paper (CIB W78 2026) and the
companion formulation paper (ISARC 2026).
