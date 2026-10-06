"""verify/tier_trends.py: Experiment 1 with intervals and a population estimate."""
import importlib.util
import json
import os

import numpy as np
import pytest


@pytest.fixture(scope="module")
def tt(root):
    spec = importlib.util.spec_from_file_location("tier_trends", os.path.join(root, "verify", "tier_trends.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def bench_trends(tt, benchmark):
    return tt.trends(tt.metric_values(benchmark), n_boot=300, seed=0)


@pytest.fixture(scope="module")
def bench_trends_v40(tt, benchmark_v40):
    return tt.trends(tt.metric_values(benchmark_v40), n_boot=300, seed=0)


def test_spearman_matches_scipy(tt):
    stats = pytest.importorskip("scipy.stats")
    rng = np.random.default_rng(0)
    x = rng.integers(1, 9, 400).astype(float)                      # many ties, like tiers
    y = x * 0.3 + rng.normal(0, 1, 400)
    assert tt.spearman(x, y) == pytest.approx(stats.spearmanr(x, y).statistic, abs=1e-12)


def test_ranks_average_ties(tt):
    assert tt._ranks(np.array([10.0, 20.0, 20.0, 5.0])).tolist() == [2.0, 3.5, 3.5, 1.0]


def test_benchmark_medians_pinned(bench_trends_v40, bench_trends):
    gap = {t: v["median"] for t, v in bench_trends_v40["clear_gap_mm"]["per_tier"].items()}
    load = {t: v["median"] for t, v in bench_trends_v40["load_kN"]["per_tier"].items()}
    assert [round(gap[f"C{n}"]) for n in range(2, 9)] == [120, 98, 90, 73, 76, 60, 62]
    assert [round(load[f"C{n}"], 2) for n in range(1, 9)] == [0.10, 0.23, 0.44, 0.55, 0.78, 1.21, 1.49, 1.71]
    assert "C1" not in gap
    gap = {t: v["median"] for t, v in bench_trends["clear_gap_mm"]["per_tier"].items()}
    load = {t: v["median"] for t, v in bench_trends["load_kN"]["per_tier"].items()}
    assert [round(gap[f"C{n}"]) for n in range(2, 9)] == [130, 89, 77, 72, 69, 61, 51]            # revision 4.1
    assert [round(load[f"C{n}"], 2) for n in range(1, 9)] == [0.30, 0.24, 1.04, 0.94, 1.22, 1.36, 2.24, 2.04]                                          # no pair in a one-element context


def test_directions_and_intervals(bench_trends, bench_trends_v40):
    for b, rho in ((bench_trends, 0.4), (bench_trends_v40, 0.5)):
        assert b["clear_gap_mm"]["spearman"] < -0.3 and b["clear_gap_mm"]["spearman_ci"][1] < 0
        assert b["load_kN"]["spearman"] > rho and b["load_kN"]["spearman_ci"][0] > 0
    assert bench_trends_v40["load_kN"]["monotone_medians"] and not bench_trends_v40["clear_gap_mm"]["monotone_medians"]
    assert bench_trends["clear_gap_mm"]["monotone_medians"]                   # 4.1: rows no longer jump at C6
    for m in bench_trends.values():
        for v in m["per_tier"].values():
            assert v["ci"][0] <= v["median"] <= v["ci"][1]


def test_population_shows_the_row_effect(tt):
    """In the 4.0 generator, load rises at every step while the clear gap widens
    from C5 to C6, where contexts start to stack in two or three rows."""
    r = tt.trends(tt.metric_values(tt.population(400, 11, "4.0")), n_boot=200, seed=0)
    load = [r["load_kN"]["per_tier"][f"C{n}"]["median"] for n in range(1, 9)]
    gap = {t: v["median"] for t, v in r["clear_gap_mm"]["per_tier"].items()}
    assert all(np.diff(load) > 0)
    assert gap["C6"] > gap["C5"] and gap["C2"] > gap["C5"] > gap["C8"]


def test_run_is_deterministic(tt, benchmark):
    a = tt.run(benchmark[:400], per_tier=20, n_boot=100, seed=1, mc_seed=2)
    b = tt.run(benchmark[:400], per_tier=20, n_boot=100, seed=1, mc_seed=2)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert "C8" in tt.render(a)


def test_population_4_1_load_rises_and_gap_narrows(tt):
    """In the 4.1 generator rows follow the count smoothly, so the clear gap narrows
    at every step and load rises at every step (population estimate, 400 per tier)."""
    r = tt.trends(tt.metric_values(tt.population(400, 11)), n_boot=200, seed=0)
    load = [r["load_kN"]["per_tier"][f"C{n}"]["median"] for n in range(1, 9)]
    gap = [r["clear_gap_mm"]["per_tier"][f"C{n}"]["median"] for n in range(2, 9)]
    assert all(np.diff(load) > 0)
    assert all(np.diff(gap) < 0)
