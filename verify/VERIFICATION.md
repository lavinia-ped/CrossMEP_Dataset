# Verification against open buildings

The layout statistics of CrossMEP are checked against open IFC models of two
buildings from buildingSMART's community sample files (CC BY 4.0): the **Duplex
Apartment** (a small residential model; MEP and Plumbing discipline models) and
the **Medical-Dental Clinic** (a real building, redacted; Plumbing and HVAC
models). The IFC files are not redistributed; `verify/measured/README.md` gives
their SHA-256 digests, the source and the attribution.

## Section-cut measurement (current; `measure_ifc.py`, `compare_sections.py`)

A context is the section across a run at one support, so the models are measured
the same way (October 2026, IfcOpenShell 0.9):

1. Mesh every `IfcFlowSegment`; record its kind (pipe, duct, cable carrier, from
   its type), its `Size` property, its bounding box and the plan direction of its
   long axis (principal component of the mesh vertices).
2. Keep horizontal runs aligned with the x or y axis (within 2°), at least 250 mm
   long and longer than tall.
3. Cut sections perpendicular to each axis every 250 mm. Runs whose centres lie
   within 400 mm of the lowest run of a band form one row (the generator's row,
   whose stagger reaches 120 mm).
4. Along each row, consecutive runs are neighbours if their clear gap between
   bare surfaces is positive and below 1,200 mm. Each neighbour pair is recorded
   once, with its gap and the number of sections it appears in (its shared
   length / 250 mm).

```bash
pip install ifcopenshell
python verify/measure_ifc.py Clinic_Plumbing.ifc --name clinic_plumbing \
    --out verify/measured/clinic_plumbing.json --segments-out verify/measured/segments/clinic_plumbing.json
python verify/compare_sections.py --sensitivity
```

`verify/measured/segments/` keeps the meshed segment tables, so every record is
recomputed without IfcOpenShell (`tests/test_sections.py`).

### Measured pipe gaps (bare surfaces, < 600 mm)

| model | pipe pairs | sections | median, mm (length-weighted) | IQR, mm | below 25 mm |
|---|---|---|---|---|---|
| Clinic, Plumbing | 797 | 3,833 | 203 (189) | 117–322 | 2 % |
| Duplex, MEP | 74 | 204 | 177 (94) | 36–470 | 23 % |
| Duplex, Plumbing | 41 | 112 | 114 (105) | 25–470 | 32 % |
| generated (benchmark, 4.0) | 1,543 | — | 207 | 136–317 | 0 % |

### Distances (Wasserstein-1, mm; 95 % bootstrap intervals)

Primary: measured pairs weighted by shared length (the gap met at a random
support location). Intervals resample contexts (generated) and pipe pairs
(measured). Noise floor: median (95th percentile) distance a perfect generator
would show at that sample size and weighting.

| comparison | by length | each pair once | noise floor |
|---|---|---|---|
| generated ↔ Clinic, Plumbing | 28.3 (16.0–43.7) | 14.9 (11.3–23.5) | 8.2 (17.0) |
| generated ↔ Duplex, MEP | 70.4 (56.9–98.7) | 94.1 (73.8–119.3) | 24.5 (46.1) |
| generated ↔ Duplex, Plumbing | 85.3 (59.4–131.5) | 100.1 (84.6–125.2) | 33.7 (67.9) |
| Clinic, Plumbing ↔ Duplex, MEP | 71.0 (54.0–100.5) | 88.0 (70.0–117.9) | — |
| Clinic, Plumbing ↔ Duplex, Plumbing | 85.0 (54.6–137.3) | 94.1 (77.4–121.3) | — |
| Duplex, MEP ↔ Duplex, Plumbing | 25.6 (24.5–124.0) | 24.9 (21.4–107.6) | — |

A fixed 25 mm gap is 189 mm from the clinic. The clinic's 90 duct-duct
pairs (HVAC model; median 350 mm) are not compared: the benchmark has only
13 duct-duct neighbour pairs.

Reading: the generator is 28 mm from the clinic, a building it was not
fitted to, above that sample's noise floor but about as close as the duplex's
two discipline models are to each other; the duplex is as far from the generator
as from the clinic. The revision 3.0 files (the paper release) are farther from
the clinic (65 mm by length): removing the double-counted clearance in 4.0 brought
the generated spacing closer to a real building.

### Sensitivity to the cut (W1 by length, mm)

| variation | generated ↔ Clinic | generated ↔ Duplex MEP | generated ↔ Duplex Plumbing | Clinic ↔ Duplex MEP |
|---|---|---|---|---|
| as measured | 28.3 | 70.4 | 85.3 | 71.0 |
| sections every 125 mm | 28.9 | 67.8 | 88.1 | 67.8 |
| sections every 500 mm | 29.6 | 65.4 | 86.2 | 66.3 |
| row band 200 mm | 36.0 | 79.7 | 110.6 | 68.9 |
| row band 800 mm | 26.6 | 69.3 | 85.3 | 64.2 |
| bundle break 600 mm | 28.3 | 70.4 | 85.3 | 71.0 |
| bundle break 2,400 mm | 28.3 | 70.4 | 85.3 | 71.0 |
| axis tolerance 1 deg | 28.6 | 70.4 | 85.3 | 71.2 |
| axis tolerance 5 deg | 28.3 | 70.4 | 85.3 | 71.0 |
| min. run length 100 mm | 30.0 | 72.1 | 86.7 | 73.7 |
| min. run length 500 mm | 28.1 | 62.8 | 88.4 | 59.4 |

## The June 2026 measurement (paper section 5.2)

The generator's gap lognormal was fitted to gaps measured on the Duplex models in
June 2026 (`measured_gaps.json`, 103 gaps; `measured_gaps_plumbing.json`, 61) by
the procedure then documented: group parallel runs by axis and a 400 mm elevation
band, cluster across the axis with a 1.2 m break, and take the gaps between
across-sorted neighbours. `compare_gaps.py` reproduces the paper's section 5.2
numbers from these shipped samples (below), and `tests/test_verify.py` pins them.

That procedure, run on the same Duplex MEP file (`measure_ifc.py --legacy`),
does **not** reproduce the shipped sample: it returns 131 gaps with a median of
−24 mm against 103 gaps with a median of 108 mm. As documented it does not
require two runs to pass through a common section and it pairs the collinear
pieces of one run, which gives overlaps rather than gaps. The shipped samples
were therefore produced by a variant that is not recorded. They remain in the
repository because the generator constants and the paper's numbers derive from
them; the section-cut measurement above is the verification of record.

### June 2026 samples

| statistic | MEP model | Plumbing model |
|---|---|---|
| dominant sizes | DN25, DN40, DN15 | DN25, DN40, DN15 |
| parallel runs per bundle | 2–4 (typical) | — |
| in-bundle elevation spread | median 79 mm, p75 282 | — |
| clear gaps < 600 mm | n = 99, median 108, IQR 24–238 | n = 59, median 53, IQR 18–183 |
| clear gaps, all | n = 103, median 111, IQR 28–271 | n = 61, median 54, IQR 19–202 |

### Comparison with the June 2026 samples (`compare_gaps.py`)

The generator samples clear gaps from a lognormal fitted to the MEP gaps above
the 25 mm clearance floor and below 600 mm (n = 73): μ = 5.018, σ = 0.848,
Kolmogorov–Smirnov D = 0.092, p = 0.53. `compare_gaps.py` refits these from the
shipped sample and checks them against the generator constants, then computes
Wasserstein-1 distances (gaps < 600 mm) for each definition of the generated gap.

Revision 4.0 (current; the sampled gap is the physical gap between insulation surfaces):

| generated gap | median | min | W1 → MEP | W1 → Plumbing | W1 → pooled |
|---|---|---|---|---|---|
| insulation surface to surface | 150 | 25 | **40.7** | 89.3 | 58.9 |
| bare surface to surface (= the measured quantity) | 186 | 25 | 67.7 | 117.4 | 86.3 |

Revision 3.0 (the paper release; the sampled gap sat between 25 mm routing
envelopes, so physical gaps were the draw + 50 mm):

| generated gap | median | min | W1 → MEP | W1 → Plumbing | W1 → pooled |
|---|---|---|---|---|---|
| envelope draw (the paper's definition) | 150 | 25 | 40.7 | 89.3 | 58.9 |
| insulation surface to surface | 200 | 75 | 88.5 | 137.6 | 106.9 |
| bare surface to surface | 236 | 75 | 109.9 | 159.6 | 128.4 |

Baselines: a fixed 25 mm gap scores 138.5 mm against the MEP model; the two
real discipline models are 49.9 mm apart. The bare-surface rows are the strictly
like-for-like comparison; the gap between the insulation and bare rows is the
insulation the generator adds to 58 % of adjacent pairs, which the measurement
(flow segments only) does not include.

Measuring another model (a private commercial one, for instance) needs only its
IFC file: `measure_ifc.py` writes the record, and adding its name to
`PIPE_MODELS` in `compare_sections.py` puts it into the comparison.

## Catalog stress test (`catalog_stress.py`, paper section 5.3)

Not a comparison with a built project but the same discipline applied to the
paper's third experiment: a number with its error bars, its sensitivity and its
decomposition, reproducible from the shipped files (`crossmep/catalog.py` defines
the question; the module docstring states what is and is not tested).

```bash
python verify/catalog_stress.py                                    # the paper's two-size catalog
python verify/catalog_stress.py --bins 40:60:2.0,100:120:3.0       # your catalog: lo:hi:capacity_kN,...
python verify/catalog_stress.py --json > catalog_stress.json
```

* **Attachable** means: a pipe, whose attach diameter (insulated outer diameter for
  cold lines, bare otherwise; `--rule bare|insulated` for the alternatives) lies in a
  bin widened by `--tol` mm, and whose load does not exceed that bin's capacity. Every
  miss has exactly one reason: not a pipe, no size fits, or too heavy.
* **Error bars** are 95 % percentile cluster-bootstrap intervals, resampling whole
  contexts (the elements of one context are correlated). A separate Monte Carlo
  estimate generates 2,000 contexts per tier with the released generator, which
  separates sampling noise in the 125-context benchmark tiers from real differences
  between tiers.
* **Demand curve**: the largest share of pipes that k clamp sizes, each fitting a
  diameter window of `--width` mm (default 6), could attach, computed exactly by
  dynamic programming. It states what the dataset asks of *any* catalog.

Results for the released benchmark (`RESULTS.md` has the full output):

| | |
|---|---|
| attachable pipes | 293 of 2,529 = **11.6 %** (95 % CI 10.1–13.0) |
| population estimate | 10.8 % (10.5–11.2); per tier 10.4–11.4 % |
| sizes attached | DN40 only (all 293 DN40 pipes); DN100 (114.3 mm) lies 0.3 mm above the 108–114 mm bin |
| misses | 2,236 pipes: no size fits; 0 too heavy (heaviest pipe 0.88 kN vs 2.5 kN); 1,971 trays, ducts and conduits |
| sensitivity | 12.9 % with bins widened by 0.5 mm; 16.4 % with the bare diameter for every line; 6.2 % with the insulated one |
| best possible | two well-placed 6 mm sizes 43.0 %, six 80.1 %, twelve 100 % |

Only size and capacity are tested, so coverage is an upper bound on what can be
installed: clearance to neighbours, the rigid insert on cold lines and anchors are
not modelled.
