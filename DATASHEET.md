# Datasheet: CrossMEP (release 4.0.0; data revisions 4.0 and 3.0)

Following Gebru et al., "Datasheets for Datasets," CACM 64(12), 2021.

## Motivation

**Why was the dataset created?** To provide the first public problem distribution
for learning-based synthesis of structural support assemblies (SSAs). The companion
paper (Pedrollo, Graeber & Fischer, ISARC 2026) formalizes SSA synthesis as a
constrained sequential decision process; CrossMEP supplies the inputs that
formulation consumes — the local MEP cross-section and the mounting surface —
which no public dataset provided in any form.

**Who created it / funding?** Lavinia Pedrollo (Stanford University, CIFE), with
David Gvadzabia (Lafayette College), Torben Graeber (Hilti AG) and Martin Fischer
(Stanford University). The first author's doctoral research is supported by
Hilti AG (see the paper's acknowledgements). No proprietary data enters the
generator: every constant traces to a standard, a manufacturer engineering table,
a published datum or a measurement on the open Duplex Apartment IFC model
(`VERIFICATION_LOG.md`).

## Composition

**What do instances represent?** Each instance ("context") is a single 2-D
cross-section perpendicular to a coordinated MEP run at one support location:
every element crossing that plane (pipes, cable trays, ducts — rectangular and
round — and electrical conduits) with kind, service, trade, shape, bare width and
height (mm), insulation per side (mm), per-support-point operating load (kN) with
the support span it was derived at (m) and the load per metre (kN/m), and
continuous coordinates (offset along the mounting surface; standoff out from it),
plus the surface (ceiling/wall, substrate, thickness). A `level` field is
generative metadata (row index of the tiered layout pattern), not a physical
invariant.

**How many instances?** 7,000 contexts in four files per data revision: train
5,000 (seed 1000), validation 500 (seed 2000), test 500 (seed 3000), benchmark
1,000 (seed 42; 125 per difficulty tier). Tiers are count-stratified: tier Cn
contains exactly n elements (C1–C8), with composition (kinds, trades, services,
surfaces, stacking) marginalized within each tier. Element totals: 22,500 /
2,242 / 2,242 / 4,500. Benchmark composition: 2,529 pipes, 1,141 conduits, 569
trays, 261 ducts. Revision 4.0 (current) and 3.0 (the paper release) contain
the same elements in the same rows; they differ in along-surface positions
(4.0 removed a double-counted clearance) and in the two recorded load fields.

**Labels?** None, by design. Feasible assemblies are non-unique and
catalog-dependent; intended consumers (reinforcement learning, constraint solvers)
derive supervision from downstream environment rules, not annotations.

**Splits?** Canonical train/val/test/benchmark on disjoint seeds; all regenerate
byte-for-byte from the included generator for both revisions
(`RELEASE_CHECKSUMS.txt`).

**Confidential or personal data?** None. The dataset is fully synthetic and
contains no personal, proprietary, or project-identifying information.

## Collection / generation process

**How was the data produced?** Procedurally, by the `crossmep` package
(NumPy-only generator). The generator encodes documented conventions rather than
free randomness: DN-series pipe outer diameters (EN 10220:2002, EN 10255:2004);
standard tray widths (150–600 mm; IEC 61537 systems) and rectangular duct sizes
(EN 1505 preferred dimensions, 250×200 to 1000×500 mm) plus round spiral ducts
(EN 1506 series) and IEC 61386-1 conduit sizes; service banking (domestic
hot+cold pairs, heating supply+return, chilled banks, uninsulated sprinkler
mains, parallel conduit groups); a code-grounded insulation schedule by service
and size (GEG Anlage 8 for heated lines, verified verbatim; 30/50 mm
condensation control for chilled water, cf. UNOG 2008; duct insulation excluded);
vertical tiering (ducts nearest the surface, then trays and conduits, then
pipes) with half-normal within-row stagger calibrated to measured in-bundle
elevation spread; clear gaps between insulation surfaces sampled from a lognormal
fitted to gaps measured above the published 25 mm pipe-rack minimum clearance on
the Duplex MEP model (μ = 5.018, σ = 0.848, KS p = 0.53), with that minimum as
the hard floor; on walls, electrical containment kept above wet services
(drip-avoidance rule); surface-aware ceiling/wall geometry; and per-support
loads **derived in code** from published engineering data: pipes as EN 10255
medium-series steel + water × ASME B31.1 Table 121.5 water-service spans (floor
rule, published points only); rectangular ducts from the Walraven duct-weight
table (incl. flange/bracing allowance); round ducts from manufacturer gauge
tables; cable trays on a design-for-full-fill basis anchored to the published
50 kg/m full-300-mm-tray datum; conduits as steel tube (BS 4568 / IEC 61386-21
wall class) plus IEC 40 %-of-bore cable fill. Every constant's source and status
is itemized in `VERIFICATION_LOG.md`, and the derivations are pinned by tests.

**Validation?** Every released context passes a programmatic validator (field
domains; the insulation surfaces of any two elements at least 25 mm apart along
the surface or out from it; per-row centering) and the test suite: JSON Schema
conformance of all splits, geometric invariants over unseen seeds, byte-exact
regeneration of all eight files, distribution drift, and convention compliance.
Layout statistics were verified against two discipline models of the openly
licensed buildingSMART Duplex Apartment project (MEP: 427 segments; Plumbing:
231, meshed with IfcOpenShell): pipe-size mix, run multiplicity and elevation
spread matched; gaps are sampled from a distribution fitted to measurement, and
the generated gap distribution of revision 4.0 is 40.7 mm (Wasserstein-1) from
the MEP model at the insulation surface and 67.7 mm at the bare surface, against
49.9 mm between the two real discipline models and 138.5 mm for a fixed modular
gap. Measured samples, the measurement procedure and the comparison script are
under `verify/`.

**Known verification limits.** (1) Revision 3.0 — the paper release — padded
every element with a 25 mm routing envelope on top of the 25 mm gap floor, so
its physical gaps are 50 mm wider than the sampled ones; the paper's 41 mm
figure holds for the sampled gap only (physically 88.5 mm at the insulation
surface). Resolved in revision 4.0; the 3.0 files remain as released. (2) The
measurement meshes flow segments, i.e. bare pipe surfaces, so the strictly like-for-like
comparison is the bare-surface one (67.7 mm). (3) Both measured models belong
to one residential project, which directly validates small-bore, low-count
statistics; congested high-count scenes are grounded in coordination practice
and standards rather than measurement. (4) Trade-mix frequencies are plausible,
not surveyed. (5) The IFC measurement was not re-run for this release; the
shipped samples are the original June 2026 measurements.

## Preprocessing

None. Files are generator output with embedded metadata (dataset, data revision,
split, seed, count, units). Units: millimetres, kilonewtons, metres (span).

## Uses

**Intended.** Input distribution for SSA synthesis research: curriculum training
over element counts C1→C8, stratified evaluation (per-tier success and
feasibility-collapse rates), held-out testing on unseen seeds,
constraint-programming baselines, human benchmarking.

**Custom generation.** `generate_custom()` builds scenes to user-specified
compositions from the same element library and layout rules; output is tagged
`custom` because realism verification attaches to the natural distribution, not
to arbitrary compositions.

**Design parameters vs. empirical claims.** Surface split, trade-mix
frequencies, option weights and size bands are benchmark design parameters
defining the curriculum — deliberate choices, not measurements of building stock
(`crossmep/generate.py`).

**Documented exclusions and simplifications.** Duct thermal insulation (no
verified thickness source). Gravity drainage: governed by slope along the run,
which a single perpendicular cross-section cannot represent. Cable-pulling access
above trays is subsumed in the clearance floor and gap distribution rather than
modelled as a separate rule. Stagger is drawn per element, so pipes of one bank
may sit at different standoffs although a bank on a shared trapeze is co-planar.
Row spacing is a fixed 120 mm clear plus stagger, not a trapeze depth. Pipe sizes
stop at DN100; substrates are concrete only; no anchor capacity is encoded.

**Relation to the paper.** The CIB W78 2026 paper describes an internal v3.4
build with a function × material pipe library and additional substrates; this
public release is the v3.0 element library (revision 4.0 adds the span and kN/m
fields the paper mentions). Section 5.1 clearance ordering, all of section 5.2
and the split sizes reproduce exactly from these files; composition-dependent
values (Table 1, Figures 3 and 4b, catalog coverage) differ and are restated for
the public files in `RESULTS.md`.

**Out of scope / cautions.** The dataset must NOT be used for the structural
design of real installations. Loads embed a typical-span assumption (recorded
per element); insulation follows code schedules, not project specifications.
Single cross-sections only: routing, branches, elevation changes and support
spacing are out of scope.

## Distribution

Plain JSON, one file per split and revision, on GitHub
(https://github.com/lavinia-ped/CrossMEP_Dataset). Data: CC BY 4.0. Code
(generator, validator, scripts): MIT. Croissant metadata in `croissant.json`.

## Maintenance

Maintained by the first author (laviniap@stanford.edu). Versioned releases: the
data revision (directory, file names, embedded `version`) changes only when
contexts change; the package version tracks code and documentation
(`CHANGELOG.md`). Issues and corrections via the GitHub tracker.
