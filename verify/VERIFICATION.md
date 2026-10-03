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
   the model carries no insulation geometry, so these are bare-surface gaps).

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
insulation the generator adds to 58 % of adjacent pairs, which the Duplex model
does not carry.

Re-running against a private commercial model requires only replacing the IFC
path; sizes must be exported (property `Size` or equivalent) for step 1.
