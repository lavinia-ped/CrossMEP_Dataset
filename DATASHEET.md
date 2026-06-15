# Datasheet: CrossMEP v3.0

Following Gebru et al., "Datasheets for Datasets," CACM 64(12), 2021.

## Motivation

**Why was the dataset created?** To provide the first public problem distribution for
learning-based synthesis of structural support assemblies (SSAs). The companion paper
(Pedrollo, Graeber & Fischer, ISARC 2026) formalizes SSA synthesis as a constrained
sequential decision process; CrossMEP supplies the inputs that formulation consumes —
the local MEP cross-section and the mounting surface — which no public dataset provided
in any form.

**Who created it / funding?** Lavinia Pedrollo (Stanford University, CIFE), with Torben
Graeber (Hilti AG) and Martin Fischer (Stanford University), within a Stanford–Hilti
research collaboration.

## Composition

**What do instances represent?** Each instance ("context") is a single 2-D cross-section
perpendicular to a coordinated MEP run at one support location: every element crossing
that plane (pipes, cable trays, ducts — rectangular and round — and electrical conduits) with kind, service, trade, shape, bare width and
height (mm), insulation per side (mm), per-support-point operating load (kN), and
continuous coordinates (offset along the mounting surface; standoff out from it), plus
the surface (ceiling/wall, substrate, thickness). A `level` field is generative
metadata (row index of the tiered layout pattern), not a physical invariant.

**How many instances?** 7,000 contexts across four files: train 5,000 (seed 1000),
validation 500 (seed 2000), test 500 (seed 3000), benchmark 1,000 (seed 42; 125 per
difficulty tier C1–C8). Tiers are count-stratified: tier Cn contains exactly n
elements, with composition (kinds, trades, services, surfaces) marginalized
within each tier.

**Labels?** None, by design. Feasible assemblies are non-unique and catalog-dependent;
intended consumers (reinforcement learning, constraint solvers) derive supervision from
downstream environment rules, not annotations.

**Splits?** Canonical train/val/test/benchmark on disjoint seeds; the prior
scene-stratified T1–T4 benchmark (v2.1) remains available as a frozen archived
release; all regenerate
deterministically from the included generator.

**Confidential or personal data?** None. The dataset is fully synthetic and contains no
personal, proprietary, or project-identifying information.

## Collection / generation process

**How was the data produced?** Procedurally, by `mep_context_sampler.py` (single file,
NumPy-only). The generator encodes documented conventions rather than free randomness:
DN-series pipe outer diameters (EN 10220:2002, EN 10255:2004), standard tray widths (150–600 mm; cable tray systems per IEC 61537) and rectangular duct sizes (EN 1505-style, 250×150 to 1000×500 mm); service
banking (domestic hot+cold pairs, heating supply+return, chilled banks, uninsulated
sprinkler mains); a code-grounded insulation schedule by service and size (GEG Anlage 8
for heated lines, verified verbatim; 30/50 mm condensation-control for chilled
water, cf. UNOG 2008; duct thermal insulation excluded — no verified thickness
source);
vertical tiering (ducts nearest the surface, trays and conduits, then pipes) with
half-normal within-row height stagger calibrated to measured in-bundle elevation
spread; clear gaps sampled from a lognormal fitted to gaps measured above the published
25 mm pipe-rack minimum clearance on the Duplex MEP model (mu=5.018, sigma=0.848,
KS p=0.53), with that published minimum as the hard floor;
on walls, electrical containment is kept above wet services (drip-avoidance rule,
verified zero violations on 1,000 contexts and now enforced); surface-aware ceiling/wall geometry; and per-support loads grounded in published
engineering data: pipes as EN 10255:2004 medium-series steel + water × ASME B31.1
Table 121.5 water-service spans; rectangular ducts from the Walraven duct-weight
engineering table (incl. flange/bracing allowance); round ducts from manufacturer
gauge tables; cable trays on a design-for-full-fill basis anchored to the published
50 kg/m full-300-mm-tray datum; conduits as steel tube (BS 4568 / IEC 61386-21 wall
class) plus IEC 40%-of-bore cable fill. Every constant's source and status is
itemized in VERIFICATION_LOG.md.

**Validation?** Every released context passes a programmatic validator (pairwise
clearance robust to stagger; per-row centering) and a test suite (`tests/`): JSON Schema
conformance of all splits, geometric invariants over 200 seeds, byte-determinism of the
released benchmark, distribution-drift checks, and convention compliance. Layout
statistics were verified against TWO discipline models of the openly licensed
buildingSMART Duplex Apartment project (MEP: 427 segments; Plumbing: 231 segments, all
meshed with IfcOpenShell): pipe-size mix, run multiplicity, and elevation spread
matched; gaps are sampled from a distribution fitted to measurement, putting the
generated gap distribution 40 mm (Wasserstein-1) from the MEP model — below the
50 mm distance between the two real discipline models themselves. Measured samples
and the measurement script are under `verify/`.

**Known verification limits.** Both measured models belong to one residential project
(different discipline exports), which
directly validates small-bore, low-tier statistics; congested-rack tiers (T3/T4) are
grounded in coordination practice and standards rather than measurement. Trade-mix
frequencies are plausible, not surveyed.

## Preprocessing

None. Files are generator output with embedded metadata (dataset name, version, split,
seed, units, schema notes). Units: millimetres and kilonewtons.

## Uses

**Intended.** Input distribution for SSA synthesis research: curriculum training over
tiers, stratified evaluation (per-tier success and feasibility-collapse rates), held-out
testing on unseen seeds, constraint-programming baselines, human benchmarking.

**Custom generation.** `generate_custom()` builds scenes to user-specified
compositions from the same verified element library and layout rules; output is
tagged `custom` because realism verification attaches to the natural
distribution, not to arbitrary compositions.

**Design parameters vs. empirical claims.** Tier probabilities, trade-mix
frequencies, and element-count ranges are benchmark design parameters defining
the curriculum — deliberate choices, not measurements of building stock.

**Documented exclusions.** Duct thermal insulation is excluded (no verified
thickness source). Gravity drainage is excluded: drainage layout is governed by
slope along the run, which a single perpendicular cross-section cannot represent; this is
an explicit scope boundary, not an oversight. Cable-pulling access above trays is
subsumed in the inter-trade clearance floor and gap distribution rather than modeled as
a separate rule.

**Out of scope / cautions.** The dataset must NOT be used for the structural design of
real installations. Loads embed a typical-span assumption; insulation follows code
schedules, not project specifications. Single cross-sections only: routing, branches,
elevation changes, and support spacing are out of scope.

## Distribution

Plain JSON, one file per split. Data: CC BY 4.0. Code (generator, validator, scripts):
MIT. Hosted on GitHub with an archived Zenodo DOI (see README for URLs).

## Verification of constants

Every numeric constant is audited in `VERIFICATION_LOG.md` with value, source, and
status (VERIFIED / PRACTICE-CITED / DEFAULT). Highlights: the GEG Anlage 8 heated-line
schedule is verified verbatim against the official legal text; conduit sizes are a
strict subset of IEC 61386-1 metric trade sizes; round-duct diameters are a strict
subset of the EN 1506:2007 series. One documented divergence: GEG also specifies
9/19 mm insulation for cold RLT/chilled-distribution lines, and DIN 1988-200 specifies
9 mm anti-condensation for potable cold; CrossMEP instead models chilled water with the
stricter UNOG 30/50 mm employer schedule and domestic cold/sprinkler lines bare.

## Maintenance

Maintained by the first author (laviniap@stanford.edu). Versioned releases; v1.x schema
is stable, and any breaking change increments the major version with a changelog. Issues
and corrections via the GitHub tracker.
