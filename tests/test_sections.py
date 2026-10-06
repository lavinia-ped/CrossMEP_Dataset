"""Section-cut measurement of open IFC models and the generated-vs-measured comparison
(verify/measure_ifc.py, verify/compare_sections.py).  No IfcOpenShell needed: the
geometry core is tested on hand-built segments and the shipped records are
recomputed from the shipped segment tables."""
import importlib.util
import json
import os

import numpy as np
import pytest

MODELS = ("duplex_mep", "duplex_plumbing", "clinic_plumbing", "clinic_hvac")
SHA256 = {  # Git LFS object ids of the CC BY 4.0 source files (verify/measured/README.md)
    "duplex_mep": "13976a8e223f177a6d7123679e4b02e750cd90c13f7bb20c593be125d9407119",
    "duplex_plumbing": "abfaf5c0979b6b4b05182aec7ada8945374bdb414db76c763724d549b41b212b",
    "clinic_plumbing": "e662a8d0273694b745a313fc18ee8d4916db03453caa8f9d00d4d80b62bb6e23",
    "clinic_hvac": "39c88a79f48fbe56da86afb0fb3ebd188f8930df3df7dbfbd9ecaa535aaeab9b",
}


def _module(root, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(root, "verify", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mi(root):
    return _module(root, "measure_ifc")


@pytest.fixture(scope="module")
def cs(root):
    return _module(root, "compare_sections")


@pytest.fixture(scope="module")
def report(cs, benchmark_v40):
    """Revision 4.0: the geometry whose numbers the talk and README report."""
    return cs.compare(benchmark_v40, n_boot=200, seed=0, n_floor=200)


@pytest.fixture(scope="module")
def report_41(cs, benchmark):
    return cs.compare(benchmark, n_boot=200, seed=0, n_floor=200)


def _seg(gid, x0, x1, y, z, d=50.0, kind="pipe", axis=0):
    """A straight horizontal run of diameter d from x0 to x1 (axis 0) at across y, elevation z."""
    if axis == 0:
        lo, hi, ang = [x0, y - d / 2, z - d / 2], [x1, y + d / 2, z + d / 2], 0.0
    else:
        lo, hi, ang = [y - d / 2, x0, z - d / 2], [y + d / 2, x1, z + d / 2], 90.0
    return {"gid": gid, "kind": kind, "size": None, "lo": lo, "hi": hi, "angle_deg": ang}


# --------------------------------------------------------------------------- geometry core

def test_runs_keep_horizontal_axis_aligned_segments(mi):
    segs = [_seg("x", 0, 3000, 0, 0), _seg("y", 0, 3000, 0, 0, axis=1),
            {**_seg("diag", 0, 3000, 0, 0), "angle_deg": 30.0},
            _seg("stub", 0, 200, 0, 0),
            {"gid": "riser", "kind": "pipe", "size": None, "lo": [0, 0, 0], "hi": [50, 50, 3000], "angle_deg": 0.0}]
    runs = mi.horizontal_runs(segs)
    assert {r["gid"]: r["axis"] for r in runs} == {"x": 0, "y": 1}
    assert {r["gid"] for r in mi.horizontal_runs([{**_seg("near", 0, 3000, 0, 0), "angle_deg": 178.5}])} == {"near"}


def test_two_parallel_pipes_give_one_pair(mi):
    runs = mi.horizontal_runs([_seg("a", 0, 3000, 0, 0), _seg("b", 1000, 4000, 150, 0)])
    recs, counts = mi.section_gaps(runs, step_mm=250.0)
    pairs = mi.pair_table(recs)
    assert len(pairs) == 1 and pairs[0]["gap_mm"] == pytest.approx(100.0)       # 150 centre - 2 x 25 radius
    assert pairs[0]["n_sections"] == 8                                          # 2,000 mm shared / 250 mm
    assert pairs[0]["kinds"] == ["pipe", "pipe"]


def test_pieces_of_one_run_and_offset_runs_are_not_neighbours(mi):
    collinear = [_seg("a1", 0, 2000, 0, 0), _seg("a2", 2000, 4000, 0, 0)]
    offset = [_seg("p", 0, 2000, 0, 0), _seg("q", 3000, 5000, 120, 0)]          # never in the same section
    for segs in (collinear, offset):
        recs, _ = mi.section_gaps(mi.horizontal_runs(segs))
        assert recs == []


def test_rows_bands_crossings_and_breaks(mi):
    stacked = mi.horizontal_runs([_seg("a", 0, 3000, 0, 0), _seg("b", 0, 3000, 10, 100)])       # same band, overlapping across
    recs, counts = mi.section_gaps(stacked)
    assert recs == [] and counts["crossing_pairs"] == 12
    far_apart_in_z = mi.horizontal_runs([_seg("a", 0, 3000, 0, 0), _seg("b", 0, 3000, 200, 900)])
    assert mi.section_gaps(far_apart_in_z)[0] == []                                              # different rows
    wide = mi.horizontal_runs([_seg("a", 0, 3000, 0, 0), _seg("b", 0, 3000, 1500, 0)])
    recs, counts = mi.section_gaps(wide)
    assert recs == [] and counts["row_bundle_sizes"][1] == 24                                     # beyond the break: two bundles of one
    three = mi.horizontal_runs([_seg("a", 0, 3000, 0, 0), _seg("b", 0, 3000, 100, 0), _seg("c", 0, 3000, 300, 50)])
    pairs = mi.pair_table(mi.section_gaps(three)[0])
    assert [(p["a"], p["b"], p["gap_mm"]) for p in pairs] == [("a", "b", 50.0), ("b", "c", 150.0)]


def test_summary_weights_by_sections(mi):
    pairs = [{"a": "1", "b": "2", "kinds": ["pipe", "pipe"], "gap_mm": 100.0, "n_sections": 9},
             {"a": "3", "b": "4", "kinds": ["pipe", "pipe"], "gap_mm": 300.0, "n_sections": 1},
             {"a": "5", "b": "6", "kinds": ["duct", "duct"], "gap_mm": 20.0, "n_sections": 1}]
    s = mi.summarise(pairs)
    assert s["pipe-pipe"]["pairs"] == 2 and s["pipe-pipe"]["length_weighted_median_mm"] == 100.0
    assert s["all"]["share_below_25mm"] == pytest.approx(1 / 3)
    assert s["pairs_by_kind"] == {"pipe-pipe": 2, "duct-duct": 1}


# --------------------------------------------------------------------------- shipped records

@pytest.mark.parametrize("name", MODELS)
def test_shipped_record_recomputes_from_shipped_segments(mi, root, name):
    with open(os.path.join(root, "verify", "measured", name + ".json")) as f:
        rec = json.load(f)
    with open(os.path.join(root, "verify", "measured", "segments", name + ".json")) as f:
        seg = json.load(f)
    again = mi.measure_segments(seg["segments"], name, rec["source"])
    assert again["pairs"] == rec["pairs"] and again["summary"] == rec["summary"] and again["counts"] == rec["counts"]
    assert rec["procedure"]["version"] == mi.PROCEDURE and rec["source"]["sha256"] == SHA256[name] == seg["source"]["sha256"]


def test_attribution_notice(root):
    with open(os.path.join(root, "verify", "measured", "README.md"), encoding="utf-8") as f:
        text = f.read()
    for s in ('"Duplex Apartment Test Files," buildingSMART International', '"Medical-Dental Test Files," buildingSMART International',
              "CC BY 4.0", "Changes made", *SHA256.values()):
        assert s in text


# --------------------------------------------------------------------------- comparison

def test_weighted_w1_matches_scipy(cs):
    stats = pytest.importorskip("scipy.stats")
    rng = np.random.default_rng(3)
    a, b = rng.lognormal(5, 0.6, 200), rng.lognormal(5.2, 0.5, 90)
    wb = rng.integers(1, 20, 90).astype(float)
    assert cs.w1(a, b, None, wb) == pytest.approx(stats.wasserstein_distance(a, b, None, wb), rel=1e-9)
    assert cs.w1(a, b) == pytest.approx(stats.wasserstein_distance(a, b), rel=1e-9)


def test_w1_basic_properties(cs):
    x = np.array([10.0, 20.0, 40.0])
    assert cs.w1(x, x) == 0.0 and cs.w1(x, x + 5.0) == pytest.approx(5.0)
    assert cs.w1(x, [25.0]) == pytest.approx(np.mean(np.abs(x - 25.0)))
    assert cs.w1(x, x[::-1], [1, 1, 2], [2, 1, 1]) == pytest.approx(0.0)       # same weighted distribution


def test_samples_pinned(report):
    g, m = report["generated"], report["measured"]
    assert g["pairs"] == 1543 and g["contexts_with_pairs"] == 599 and g["median_mm"] == pytest.approx(206.7, abs=0.1)
    assert (m["clinic_plumbing"]["pairs"], m["clinic_plumbing"]["sections"]) == (797, 3833)
    assert (m["duplex_mep"]["pairs"], m["duplex_mep"]["sections"]) == (74, 204)
    assert (m["duplex_plumbing"]["pairs"], m["duplex_plumbing"]["sections"]) == (41, 112)
    assert m["duplex_mep"]["share_below_25mm"] > 0.2 > m["clinic_plumbing"]["share_below_25mm"]


def test_distances_pinned(report):
    gw = {k: v["length_weighted"]["w1"] for k, v in report["gen_to_real"].items()}
    gu = {k: v["unweighted"]["w1"] for k, v in report["gen_to_real"].items()}
    rw = {k: v["length_weighted"]["w1"] for k, v in report["real_to_real"].items()}
    assert gw == pytest.approx({"clinic_plumbing": 28.31, "duplex_mep": 70.39, "duplex_plumbing": 85.34}, abs=0.02)
    assert gu == pytest.approx({"clinic_plumbing": 14.91, "duplex_mep": 94.06, "duplex_plumbing": 100.10}, abs=0.02)
    assert rw == pytest.approx({"clinic_plumbing|duplex_mep": 71.00, "clinic_plumbing|duplex_plumbing": 85.02,
                                "duplex_mep|duplex_plumbing": 25.57}, abs=0.02)


def test_held_out_building_is_closer_than_the_buildings_are_to_each_other(report):
    """The finding the talk states: the generator is closer to the clinic than the two
    buildings are to each other, and about as far from the duplex as the clinic is."""
    g, r = report["gen_to_real"], report["real_to_real"]
    for key in ("length_weighted", "unweighted"):
        assert g["clinic_plumbing"][key]["w1"] < r["clinic_plumbing|duplex_mep"][key]["w1"] / 2
        assert g["clinic_plumbing"][key]["hi"] < r["clinic_plumbing|duplex_mep"][key]["lo"]
        for name in ("clinic_plumbing", "duplex_mep", "duplex_plumbing"):
            x = g[name][key]
            assert x["lo"] <= x["hi"]                                   # W1 is biased upwards: the estimate may sit at the lower end
            assert x["noise_floor"]["median"] < x["w1"] < x["fixed_25mm"]


def test_noise_floor_shrinks_with_sample_size(cs):
    rng = np.random.default_rng(0)
    gen = rng.lognormal(5.2, 0.5, 2000)
    small = cs.noise_floor(gen, np.ones(30), 200, np.random.default_rng(1), weighted=False)
    large = cs.noise_floor(gen, np.ones(800), 200, np.random.default_rng(1), weighted=False)
    assert large["median"] < small["median"] and large["p95"] < small["p95"]


def test_comparison_is_deterministic(cs, benchmark):
    a = cs.compare(benchmark[:300], n_boot=30, seed=4, n_floor=20)
    b = cs.compare(benchmark[:300], n_boot=30, seed=4, n_floor=20)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_sensitivity_keeps_the_finding(cs, benchmark_v40):
    rows = cs.sensitivity(benchmark_v40)
    assert [r["variation"] for r in rows][0] == "as measured" and len(rows) == len(cs.VARIATIONS)
    for r in rows:
        clinic = r["models"]["clinic_plumbing"]["w1_weighted"]
        assert clinic < 40.0 and clinic < r["clinic_to_duplex_mep_weighted"] / 1.5


def test_revision_3_is_farther_from_the_held_out_building(cs, benchmark_v3):
    """Removing the double-counted clearance (revision 4.0) moved the generated spacing
    towards a real building the generator was not fitted to."""
    g3 = np.concatenate(cs.generated_samples(benchmark_v3))
    g, w = cs.measured_sample(cs.load_measured("clinic_plumbing"))
    assert cs.w1(g3, g, None, w) == pytest.approx(65.1, abs=0.1)


# --------------------------------------------------------------------------- revision 4.1

def test_revision_4_1_samples_and_distances(report_41):
    """4.1 changes composition, not the gap draw: wider DN bands add insulation, so the
    bare-surface gaps sit a little farther from the clinic (32 vs 28 mm), inside the
    4.0 interval, and the finding holds."""
    g, r = report_41["gen_to_real"], report_41["real_to_real"]
    assert report_41["generated"]["pairs"] == 1690 and report_41["generated"]["contexts_with_pairs"] == 575
    assert g["clinic_plumbing"]["length_weighted"]["w1"] == pytest.approx(32.5, abs=0.1)
    for key in ("length_weighted", "unweighted"):
        assert g["clinic_plumbing"][key]["w1"] < r["clinic_plumbing|duplex_mep"][key]["w1"] / 2
        assert g["clinic_plumbing"][key]["hi"] < r["clinic_plumbing|duplex_mep"][key]["lo"]
        for name in ("clinic_plumbing", "duplex_mep", "duplex_plumbing"):
            x = g[name][key]
            assert x["noise_floor"]["median"] < x["w1"] < x["fixed_25mm"]


def test_revision_4_1_sensitivity(cs, benchmark):
    for r in cs.sensitivity(benchmark):
        clinic = r["models"]["clinic_plumbing"]["w1_weighted"]
        assert clinic < 45.0 and clinic < r["clinic_to_duplex_mep_weighted"] / 1.5
