# Verification against a built project

Layout statistics of CrossMEP were verified against the openly licensed
buildingSMART "Duplex Apartment" IFC project — its MEP discipline export
(427 flow segments) and its Plumbing export (231 sized segments). The models are
not redistributed here; they are available from buildingSMART community sample
collections (the file names used in June 2026 were `Ifc2x3_Duplex_MEP.ifc` and
`Ifc2x3_Duplex_Plumbing.ifc`).

## Procedure (`measure_ifc.py`, IfcOpenShell ≥ 0.7)

1. Take every `IfcFlowSegment`; read the nominal size from the `Size` property.
2. Mesh each segment in world coordinates; derive the long axis and centre from
   the bounding box; keep horizontal segments longer than 250 mm.
3. Group parallel runs by axis and elevation band (400 mm); cluster across the
   axis with a 1.2 m break; per cluster compute run multiplicity, in-bundle
   elevation spread, and clear gaps between adjacent runs (surface to surface;
   the procedure meshes flow segments only, so these are gaps between bare pipe surfaces).

```bash
pip install ifcopenshell
python verify/measure_ifc.py Ifc2x3_Duplex_MEP.ifc --gaps-out gaps.json --self-check verify/measured_gaps.json
```

The shipped `measured_gaps.json` (103 gaps) and `measured_gaps_plumbing.json`
(61 gaps) are the original June 2026 outputs. The script was not re-run for
release 4.0.0 (models not at hand); `--self-check` reports the agreement of any
re-run with the shipped samples.

## Measured results

| statistic | MEP model | Plumbing model |
|---|---|---|
| dominant sizes | DN25, DN40, DN15 | DN25, DN40, DN15 |
| parallel runs per bundle | 2–4 (typical) | — |
| in-bundle elevation spread | median 79 mm, p75 282 | — |
| clear gaps < 600 mm | n = 99, median 108, IQR 24–238 | n = 59, median 53, IQR 18–183 |
| clear gaps, all | n = 103, median 111, IQR 28–271 | n = 61, median 54, IQR 19–202 |

## Comparison (`compare_gaps.py`)

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

Re-running against a private commercial model requires only replacing the IFC
path; sizes must be exported (property `Size` or equivalent) for step 1.

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
