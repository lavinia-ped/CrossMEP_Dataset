"""What a hanger carries: section bundles of the open models against the generator
(verify/measure_ifc.section_bundles, verify/compare_composition.py).  No
IfcOpenShell needed: the bundle extraction is tested on hand-built segments and
the shipped segment tables give the measured numbers."""
import importlib.util
import os

import numpy as np
import pytest


def _module(root, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(root, "verify", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mi(root):
    return _module(root, "measure_ifc")


@pytest.fixture(scope="module")
def cc(root):
    return _module(root, "compare_composition")


@pytest.fixture(scope="module")
def report(cc, benchmark_v40):
    """Revision 4.0: the composition the comparison was first run on (out of sample)."""
    return cc.compare(benchmark_v40, n_boot=100, seed=0)


@pytest.fixture(scope="module")
def report_41(cc, benchmark):
    """Revision 4.1: composition adjusted after that comparison (in sample)."""
    return cc.compare(benchmark, n_boot=100, seed=0)


def _seg(gid, x0, x1, y, z, d=50.0, kind="pipe", size=None):
    return {"gid": gid, "kind": kind, "size": size, "lo": [x0, y - d / 2, z - d / 2], "hi": [x1, y + d / 2, z + d / 2],
            "angle_deg": 0.0}


# --------------------------------------------------------------------------- bundle extraction

def test_bundles_split_at_the_break_and_record_kinds(mi):
    segs = [_seg("a", 0, 2000, 0, 3000), _seg("b", 0, 2000, 200, 3000, kind="duct"),
            _seg("c", 0, 2000, 3000, 3000)]                                   # c is 2.7 m away: its own bundle
    runs = mi.horizontal_runs(segs)
    bundles = mi.section_bundles(runs)
    assert len(bundles) == 16                                                  # 8 sections x 2 bundles
    sizes = sorted({(b["n"], tuple(b["kinds"])) for b in bundles})
    assert sizes == [(1, ("pipe",)), (2, ("pipe", "duct"))]
    assert all(b["stack"] == 1 for b in bundles)
    assert {b["gids"] for b in bundles} == {("a", "b"), ("c",)}


def test_stacking_counts_rows_within_reach_not_the_other_storey(mi):
    segs = [_seg("a", 0, 2000, 0, 3000), _seg("b", 0, 2000, 0, 3600),           # 600 mm above: a stacked row
            _seg("c", 0, 2000, 0, 6500)]                                       # 3.5 m above: the next storey
    bundles = mi.section_bundles(mi.horizontal_runs(segs))
    by = {b["gids"]: b["stack"] for b in bundles}
    assert by[("a",)] == 2 and by[("b",)] == 2 and by[("c",)] == 1
    # with a larger reach the storey above counts too
    by = {b["gids"]: b["stack"] for b in mi.section_bundles(mi.horizontal_runs(segs), stack_mm=5000.0)}
    assert by[("a",)] == 3


def test_stacking_needs_across_overlap(mi):
    segs = [_seg("a", 0, 2000, 0, 3000), _seg("b", 0, 2000, 900, 3600)]        # 850 mm apart across: not over each other
    bundles = mi.section_bundles(mi.horizontal_runs(segs))
    assert all(b["stack"] == 1 for b in bundles)


# --------------------------------------------------------------------------- statistics

def test_dn_bins(cc):
    assert cc.dn_bin("80 mmø") == "80" and cc.dn_bin("27 mmø") == "25" and cc.dn_bin("150 mmø") == "150"
    assert cc.dn_bin("200 mmø") == ">150"
    assert cc.dn_bin("Size") is None and cc.dn_bin(None) is None and cc.dn_bin("200ø") is None


def test_table_sums_to_the_sample(cc):
    bundles = [{"n": 2, "kinds": ["pipe", "duct"], "stack": 2, "dns": ["25"], "gids": ("a", "b")},
               {"n": 2, "kinds": ["pipe", "duct"], "stack": 1, "dns": ["25"], "gids": ("a", "b")},
               {"n": 1, "kinds": ["pipe"], "stack": 1, "dns": ["80"], "gids": ("c",)}]
    T = cc.table(bundles)
    assert T.shape[0] == 2                                                     # two physical bundles
    s = cc.shares(T.sum(axis=0))
    assert s["locations"] == 3 and s["size_share"]["1"] == pytest.approx(1 / 3)
    two = s["by_count"]["2"]
    assert two["locations"] == 2 and two["mixed_share"] == 1.0 and two["stacked_share"] == 0.5
    assert two["kind_share"] == {"pipe": 0.5, "duct": 0.5, "electrical": 0.0}
    assert s["dn_share"]["25"] == pytest.approx(2 / 3) and s["dn_known"] == 3


def test_tv_properties(cc):
    assert cc.tv({"a": 1.0}, {"a": 1.0}) == 0.0
    assert cc.tv({"a": 1.0}, {"b": 1.0}) == 1.0
    assert cc.tv({"a": 0.7, "b": 0.3}, {"a": 0.3, "b": 0.7}) == pytest.approx(0.4)


def test_generated_reference_is_restricted_to_the_kinds_present(cc, benchmark):
    pd = cc.generated_bundles(benchmark, ("pipe", "duct"))
    assert pd and all(set(b["kinds"]) <= {"pipe", "duct"} for b in pd)
    assert len(cc.generated_bundles(benchmark)) == len(benchmark)


# --------------------------------------------------------------------------- the open buildings

def test_measured_samples_pinned(report):
    m = report["measured"]
    assert m["clinic"]["kinds_present"] == ["duct", "pipe"] and m["duplex"]["kinds_present"] == ["electrical", "pipe"]
    assert (m["clinic"]["locations"], m["clinic"]["physical_bundles"]) == (12529, 2430)
    assert (m["duplex"]["locations"], m["duplex"]["physical_bundles"]) == (393, 121)
    assert (m["clinic"]["generated_contexts"], m["duplex"]["generated_contexts"]) == (397, 792)


def test_single_elements_dominate_the_open_buildings(report):
    for s in report["measured"].values():
        assert s["size_share"]["1"] > 0.5
        assert sum(s["size_share"][str(k)] for k in (1, 2, 3)) > 0.85


def test_clinic_kind_shares_are_close_above_two_elements(report):
    d = report["measured"]["clinic"]["distance_by_count"]
    assert all(d[str(k)]["kind_tv"] < 0.10 for k in (3, 4, 5, 6, 7, 8))
    assert d["2"]["kind_tv"] < 0.25                                            # ducts pair with pipes more often than drawn


def test_generator_mixes_and_stacks_more_than_the_clinic(report):
    s = report["measured"]["clinic"]
    for k in (2, 3, 6, 7, 8):
        assert s["distance_by_count"][str(k)]["mixed_diff"] < 0
        assert s["distance_by_count"][str(k)]["stacked_diff"] < 0


def test_buildings_differ_more_in_pipe_sizes_than_either_from_the_generator(report):
    real = report["real_to_real_dn_tv"]["clinic<->duplex"]
    assert real > max(s["dn_tv"] for s in report["measured"].values())


def test_intervals_contain_the_point_estimates(report):
    for s in report["measured"].values():
        assert s["dn_tv_ci"][0] <= s["dn_tv"] <= s["dn_tv_ci"][1]
        for d in s["distance_by_count"].values():
            assert d["kind_tv_ci"][0] - 1e-9 <= d["kind_tv"] <= d["kind_tv_ci"][1] + 1e-9


def test_comparison_is_deterministic(cc, benchmark_v40, report):
    again = cc.compare(benchmark_v40, n_boot=100, seed=0)
    assert again["measured"]["clinic"]["dn_tv_ci"] == report["measured"]["clinic"]["dn_tv_ci"]
    assert np.isfinite(again["measured"]["duplex"]["dn_tv"])


# --------------------------------------------------------------------------- revision 4.1 (in sample)

def test_revision_4_1_reference_pinned(report_41):
    m = report_41["measured"]
    assert (m["clinic"]["locations"], m["clinic"]["physical_bundles"]) == (12529, 2430)      # measured side unchanged
    assert (m["clinic"]["generated_contexts"], m["duplex"]["generated_contexts"]) == (526, 786)


def test_revision_4_1_is_closer_to_the_clinic_in_composition(report, report_41):
    """What the adjustment was for: kind shares, mixing and stacking by count move
    towards the clinic for every count; in sample, so a design check, not a test."""
    old, new = report["measured"]["clinic"]["distance_by_count"], report_41["measured"]["clinic"]["distance_by_count"]
    for k in range(2, 9):
        d = new[str(k)]
        assert d["kind_tv"] <= 0.15
        assert abs(d["stacked_diff"]) <= 0.15
    assert sum(abs(new[str(k)]["mixed_diff"]) for k in range(2, 9)) < sum(abs(old[str(k)]["mixed_diff"]) for k in range(2, 9))
    assert sum(abs(new[str(k)]["stacked_diff"]) for k in range(2, 9)) < sum(abs(old[str(k)]["stacked_diff"]) for k in range(2, 9))
    assert report_41["measured"]["clinic"]["dn_tv"] <= report["measured"]["clinic"]["dn_tv"] + 0.01
