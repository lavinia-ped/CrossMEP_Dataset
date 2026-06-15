# CrossMEP

A tiered synthetic dataset of multi-trade MEP cross-sections for learning-based
structural support assembly (SSA) synthesis. Each context is a single 2-D
cross-section at one support location: the elements a support must carry and the
surface it mounts to — deliberately **no assembly information** and **no labels**
(supervision comes from downstream environment rules; see the papers below).

## Files

| file | contexts | seed | purpose |
|---|---|---|---|
| `mep_contexts_v3.0_train.json` | 5,000 | 1000 | training (625/tier) |
| `mep_contexts_v3.0_val.json` | 500 | 2000 | validation |
| `mep_contexts_v3.0_test.json` | 500 | 3000 | held-out test |
| `mep_contexts_v3.0_benchmark.json` | 1,000 | 42 | stratified benchmark (125/tier) |

Plus: `mep_context_sampler.py` (generator + validator + renderers),
`crossmep_tasks.py` (loader + benchmark tasks: catalog coverage, congestion score,
per-tier reporting), `tests/` (quality gates: schema, invariants, determinism, drift),
`schema/` (JSON Schema), `croissant.json` (ML metadata),
`mep_contexts_gallery.html` (interactive inspection: filter by tier/kind/trade/surface),
`DATASHEET.md`, `verify/` (IFC verification notes + measured gap sample).

## Schema (per element)

`kind` (pipe | cable_tray | duct | conduit), `service`, `trade`, `shape`, `width_mm`,
`height_mm`, `insulation_mm` (per side), `load_kN` (per support point at typical
spacing), `along_mm` (offset along the surface), `out_mm` (standoff from it),
`level` (generative row index — metadata, not a physical invariant).
Surface: `kind` (ceiling | wall), `substrate`, `thickness_mm`. Units: mm, kN.

## Quickstart

```python
import json
data = json.load(open("mep_contexts_v3.0_benchmark.json"))
ctx = data["contexts"][0]
print(ctx["tier"], ctx["surface"]["kind"], len(ctx["elements"]))
```

Regenerate any split deterministically:

```bash
python mep_context_sampler.py --n 1000 --seed 42 --json out.json
```

(Requires only NumPy. `--tier T1..T4` fixes a single tier.)

## Difficulty tiers (v3: count-stratified)

Tier = EXACT element count: **C1 (single element) through C8 (eight elements)**.
Composition — kinds, trades, services, surfaces, stacking — is marginalized within
each tier, making element count the single difficulty axis. C1 covers every kind
(lone pipe of any service, single tray, duct, or conduit): the most common support
in any building, and the atomic floor for curriculum training and per-kind
diagnostics. Verified strictly monotone in load and bundle width; clearance falls
120 → ~62 mm across C2–C8.

## Custom generation (constructive API)

Build scenes to YOUR composition spec — same verified element library, same
physics (fitted gaps, published clearance floor, wall drip rule):

```python
from mep_context_sampler import generate_custom
generate_custom(100, pipes=3, trays=1)                      # exact composition
generate_custom(50, pipes=(2, 4), conduits=(2, 6))          # ranges, per-context
generate_custom(20, pipes=2, trades=["chilled"], surface="wall", seed=7)
```

Or from the command line:

```bash
python mep_context_sampler.py --n 100 --pipes 3 --trays 1 --json my_set.json
```

Custom scenes are tagged `tier: "custom"`: they are construction-valid by the
same rules as the canonical tiers, but realism *verification* attaches to the
natural distribution, not to arbitrary compositions. Canonical benchmark splits
stay frozen — comparable numbers always come from seed 42.

## Filtering

```python
import crossmep_tasks as cm
data = cm.load("benchmark")
cm.filter_contexts(data, pipes=2, trays=1)            # exactly 2 pipes + 1 tray
cm.filter_contexts(data, ducts=(1, None))             # at least one duct
cm.filter_contexts(data, pipes=(3, 5), conduits=0)    # 3-5 pipes, no conduits
cm.filter_contexts(data, tier="C1", surface="wall")
cm.filter_contexts(data, trades=["chilled", "electrical"])
```
Count specs accept an exact int or a `(lo, hi)` tuple (either bound may be None).

## License

Data: CC BY 4.0 (`LICENSE-DATA`). Code: MIT (`LICENSE-CODE`).
Synthetic data — **not for the structural design of real installations.**

## Tests

```bash
pytest tests/ -q     # 41 checks: schema, invariants over 200 seeds, determinism, drift
```

## Changelog v3.0 — zero-invention release
- No invented physical numbers remain: spans restricted to verbatim ASME B31.1
  published points (floor rule); duct sizes restricted to verbatim Walraven table
  cells (all EN 1505 preferred dims); clearance floor set to the published 25 mm
  pipe-rack minimum everywhere; gap lognormal refit on the >25 mm measured
  population (n=73, KS p=0.53); duct insulation removed (no verified source).
- Realism IMPROVED by the stricter grounding: W1 to the measured MEP model
  58 → 40 mm (the two real discipline models are 50 mm apart); tier clearance
  ordering strictly monotone again (132/82/70/62 mm).
- Tier load medians: 0.14 / 0.43 / 1.78 / 2.88 kN.

## Changelog v2.0 (vs v1.2)

- ALL load constants re-grounded in published engineering data (strict audit):
  pipes = EN 10255:2004 medium walls + water × B31.1 spans; rect ducts = Walraven
  engineering table (previous estimates were up to 58% light); round ducts =
  manufacturer gauge tables; trays = design-for-full-fill on the published
  50 kg/m@300 mm datum; conduits = BS 4568-class steel + IEC 40% fill.
  Tier median total loads now 0.17 / 0.48 / 1.58 / 2.75 kN (T1–T4).

- NEW kinds: electrical conduits (Ø20–50, parallel groups of 2–6) and round
  spiral ducts (Ø160–500, EN 1506-style).
- Gaps now sampled from a lognormal FITTED to measured Duplex gaps (above-floor
  population, KS p=0.76): W1 to the measured MEP model 88 → 58 mm; the two real
  discipline models are 50 mm apart from each other.
- Stagger now half-normal, calibrated: T2–T4 in-bundle spread median 84 mm vs
  measured 79 mm.
- Verification widened to a second discipline model (Duplex Plumbing, 231 segments).
- Wall scenes now enforce electrical-above-wet (drip avoidance); verified 0
  violations on the benchmark.
- Tier element minimums now enforced (T2≥3, T3≥4, T4≥5) — fixes a v1.x bug
  where Table-1 lower bounds could be undershot.
- Quality gates: JSON Schema, 41-test suite, byte-determinism, drift checks.
- Benchmark tasks + loader + Croissant metadata for third-party comparability.

## Citation

See `CITATION.cff`. Please cite the dataset paper (CIB W78 2026) and the companion
formulation paper (Pedrollo, Graeber & Fischer, ISARC 2026).
