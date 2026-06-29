# Verification against a built project

Layout statistics of CrossMEP were verified against the openly licensed
buildingSMART "Duplex Apartment" IFC model (Ifc2x3_Duplex_MEP.ifc, available via
buildingSMART community sample-file repositories).

Procedure (reproducible with ifcopenshell >= 0.8):
1. Parse all IfcFlowSegment entities; read nominal size from the "Size" property.
2. Mesh each segment (ifcopenshell.geom, world coordinates); derive the long axis
   and center from the bounding box; keep horizontal segments with length > 250 mm.
3. Group parallel runs by axis and elevation band (400 mm); cluster across-axis
   with a 1.2 m break; compute per-cluster: run multiplicity, in-bundle elevation
   spread, and clear gaps between adjacent runs (surface-to-surface).

Measured results used in the paper — MEP model: dominant sizes DN25/DN40/DN15;
run multiplicity 2-4; elevation spread median 79 mm (p75 282); clear gaps median
108 mm, IQR 24-238 (n = 99, < 600 mm), saved as measured_gaps.json. Plumbing
model (same procedure): 231 sized segments; gaps median 54 mm, IQR 19-202
(n = 61), saved as measured_gaps_plumbing.json.

The generator samples gaps from a lognormal FITTED to the MEP-model gaps above
the published 25 mm clearance floor (mu=5.018, sigma=0.848, KS p=0.53, n=73).
Computing the Wasserstein-1 distance on the realized gaps in the released data
(`wasserstein_gaps.py`, gaps < 600 mm) gives 41 mm to the MEP model, 89 mm to
Plumbing, and 59 mm to the pooled sample — versus 50 mm between the two real
discipline models, and 139 mm for the pre-fit fixed-modular (25 mm floor)
baseline. The synthetic-to-real distance is thus comparable to the real-to-real
variation. Run `python verify/wasserstein_gaps.py` to reproduce.

Re-running against a private commercial model requires only replacing the IFC
path; sizes must be exported (property "Size" or equivalent) for step 1.
