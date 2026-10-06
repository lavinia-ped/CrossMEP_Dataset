# Section-cut measurements of open IFC models

Derived data used by `verify/compare_sections.py`. Each record was produced by
`verify/measure_ifc.py` (procedure "section-cut 1.0", default parameters) from
the IFC files listed below; `segments/` holds the meshed flow-segment tables
(bounding boxes to 0.1 mm) from which `measure_ifc.measure_segments` recomputes
every record without IfcOpenShell (`tests/test_sections.py` checks this).

| record | source file | SHA-256 of the source | bytes |
|---|---|---|---|
| `duplex_mep.json` | `Duplex_MEP_20110907.ifc` | `13976a8e223f177a6d7123679e4b02e750cd90c13f7bb20c593be125d9407119` | 17,871,432 |
| `duplex_plumbing.json` | `Duplex_Plumbing_20121113.ifc` | `abfaf5c0979b6b4b05182aec7ada8945374bdb414db76c763724d549b41b212b` | 31,556,138 |
| `clinic_plumbing.json` | `Clinic_Plumbing.ifc` | `e662a8d0273694b745a313fc18ee8d4916db03453caa8f9d00d4d80b62bb6e23` | 55,834,520 |
| `clinic_hvac.json` | `Clinic_HVAC.ifc` | `39c88a79f48fbe56da86afb0fb3ebd188f8930df3df7dbfbd9ecaa535aaeab9b` | 26,914,597 |

Two further discipline models were opened and found to contain no `IfcFlowSegment`
(fixtures, terminals and equipment only), so they carry no conduit or tray runs
to measure: `Clinic_Electrical.ifc`
(`70c436de1f1e8a860acfba61b68da1c9243d18dcbbddb98b88b550a642d95d32`, 6,800,204
bytes) and `Duplex_Electrical_20121207.ifc`
(`d47b014ed5b3428496683ee75e4664013f6df8237ea571b8d13f877cea0b7a94`, 1,602,758
bytes). `Duplex_Plumbing_20121113.ifc` re-exports most of the MEP model's pipes
(161 of its 231 segments have the same bounding box as an MEP segment), so the
composition comparison (`verify/compare_composition.py`) uses the MEP model alone
for the duplex and merges Plumbing + HVAC for the clinic.

The files were downloaded on 5 October 2026 from
<https://github.com/buildingsmart-community/Community-Sample-Test-Files>
(`IFC 2.3.0.1 (IFC 2x3)/Duplex Apartment/` and `.../Medical-Dental Clinic/`);
the digests equal the Git LFS object ids in that repository. The IFC files are not
redistributed here.

## Attribution and licence

* BSI (2020) "Duplex Apartment Test Files," buildingSMART International,
  <https://github.com/buildingsmart-community/Community-Sample-Test-Files>.
  Licensed CC BY 4.0.
* BSI (2020) "Medical-Dental Test Files," buildingSMART International,
  <https://github.com/buildingsmart-community/Community-Sample-Test-Files>.
  Licensed CC BY 4.0. (A real building whose information has been redacted.)

Changes made: the models were not modified. Flow-segment geometry was meshed with
IfcOpenShell and reduced to bounding boxes, kinds, sizes and plan directions
(`segments/`), from which clear gaps between side-by-side runs were measured on
sections (records). These derived tables are shared under CC BY 4.0 with the
attribution above.

## Record format

```
name, source {file, sha256, bytes, ifcopenshell}, procedure {version, parameters},
counts {flow_segments, horizontal_runs, runs_by_kind, sections, crossing_pairs, row_bundle_sizes},
summary {all, pipe-pipe, pairs_by_kind},
pairs [{a, b (GlobalIds), kinds, gap_mm (median over sections), gap_min_mm, gap_max_mm, n_sections}]
```

Gaps are between bare element surfaces (the models carry flow segments, not
insulation), in millimetres. `n_sections` is the number of 250 mm-spaced sections
in which the two runs are neighbours, i.e. their shared length / 250 mm.
