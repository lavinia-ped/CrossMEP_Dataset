"""verify/compare_gaps.py reproduces the paper's section 5.2 numbers from the
shipped measurements, for both data revisions."""
import importlib.util
import json
import os

import numpy as np
import pytest

from crossmep.layout import GAP_LOGNORMAL_MU, GAP_LOGNORMAL_SIGMA


@pytest.fixture(scope="module")
def cg(root):
    spec = importlib.util.spec_from_file_location("compare_gaps", os.path.join(root, "verify", "compare_gaps.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def measured(cg):
    with open(cg.MEASURED_MEP) as f:
        mep = json.load(f)
    with open(cg.MEASURED_PLUMBING) as f:
        pl = json.load(f)
    return mep, pl


@pytest.fixture(scope="module")
def result_v4(cg, benchmark, measured):
    return cg.compare(benchmark, *measured, version="4.0")


@pytest.fixture(scope="module")
def result_v3(cg, benchmark_v3, measured):
    return cg.compare(benchmark_v3, *measured, version="3.0")


def test_wasserstein_matches_scipy(cg):
    stats = pytest.importorskip("scipy.stats")
    rng = np.random.default_rng(0)
    a, b = rng.lognormal(5, 0.8, 300), rng.lognormal(4.5, 1.0, 120)
    assert cg.wasserstein_1(a, b) == pytest.approx(stats.wasserstein_distance(a, b), rel=1e-9)


def test_ks_statistic_matches_scipy(cg):
    stats = pytest.importorskip("scipy.stats")
    rng = np.random.default_rng(1)
    x = rng.lognormal(5, 0.8, 80)
    d = cg.ks_statistic_lognormal(x, 5.0, 0.8)
    assert d == pytest.approx(stats.kstest(x, "lognorm", args=(0.8, 0, np.exp(5.0))).statistic, rel=1e-9)


def test_lognormal_fit_reproduces_generator_constants(result_v4):
    f = result_v4["fit"]
    assert f["n"] == 73
    assert round(f["mu"], 3) == GAP_LOGNORMAL_MU == 5.018
    assert round(f["sigma"], 3) == GAP_LOGNORMAL_SIGMA == 0.848
    assert f["ks_D"] == pytest.approx(0.092, abs=0.001)
    if f["ks_p"] is not None:
        assert f["ks_p"] == pytest.approx(0.53, abs=0.01)


def test_measured_summaries(result_v4):
    m = result_v4["measured"]
    assert m["mep"]["n"] == 99 and m["mep"]["median"] == pytest.approx(108, abs=0.5)
    assert m["plumbing"]["n"] == 59 and m["plumbing"]["median"] == pytest.approx(53, abs=0.5)
    assert m["mep_all"]["n"] == 103 and m["plumbing_all"]["n"] == 61


def test_revision_4_insulation_gap_is_the_sampled_gap(result_v4):
    """Paper section 5.2: 41 mm to the MEP model, 89 to Plumbing, 59 pooled; fixed
    modular gaps 139 mm; the two real models 50 mm apart.  In revision 4.0 these
    hold for the physical gap between insulation surfaces."""
    w = result_v4["w1"]["insulation"]
    assert result_v4["generated"]["insulation"]["min"] == pytest.approx(24.9, abs=0.2)
    assert w["mep"] == pytest.approx(40.7, abs=0.15)
    assert w["plumbing"] == pytest.approx(89.3, abs=0.15)
    assert w["pooled"] == pytest.approx(58.9, abs=0.15)
    assert result_v4["baselines"]["fixed_floor_gap_to_mep"] == pytest.approx(138.5, abs=0.15)
    assert result_v4["baselines"]["real_to_real"] == pytest.approx(49.9, abs=0.15)
    assert "envelope" not in result_v4["w1"]


def test_revision_4_bare_gap(result_v4):
    """Bare-surface gaps (the quantity an uninsulated IFC model yields) are wider
    by the pair's insulation: W1 67.7 mm to the MEP model."""
    w = result_v4["w1"]["bare"]
    assert result_v4["generated"]["bare"]["median"] == pytest.approx(186, abs=1)
    assert w["mep"] == pytest.approx(67.7, abs=0.15)
    assert w["plumbing"] == pytest.approx(117.4, abs=0.15)
    assert w["pooled"] == pytest.approx(86.3, abs=0.15)


def test_revision_3_definitions(result_v3):
    """The paper release: the 41 mm held only for the envelope draw; physically no
    two neighbours were closer than 75 mm (README 'Known issues', resolved in 4.0)."""
    assert result_v3["w1"]["envelope"]["mep"] == pytest.approx(40.7, abs=0.15)
    assert result_v3["generated"]["insulation"]["min"] == pytest.approx(74.9, abs=0.2)
    assert result_v3["w1"]["insulation"]["mep"] == pytest.approx(88.5, abs=0.2)
    assert result_v3["w1"]["bare"]["mep"] == pytest.approx(110.0, abs=0.2)
    assert result_v3["baselines"]["share_measured_mep_below_75mm"] == pytest.approx(0.424, abs=0.005)
