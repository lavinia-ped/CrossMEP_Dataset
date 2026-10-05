"""Catalog stress test (paper section 5.3): definitions, pinned results, the exact
demand optimum, and the statistics in verify/catalog_stress.py."""
import importlib.util
import itertools
import json
import os
import random
from collections import Counter

import numpy as np
import pytest

import crossmep.catalog as cat
import crossmep.tasks as cm

BINS = [(48, 54, 2.5), (108, 114, 4.0)]


def _pipe(od=33.7, ins=0.0, service="sprinkler", load=0.06, label="DN25"):
    return {"kind": "pipe", "service": service, "label": label, "width_mm": od, "height_mm": od,
            "insulation_mm": ins, "load_kN": load}


@pytest.fixture(scope="module")
def cs(root):
    spec = importlib.util.spec_from_file_location("catalog_stress", os.path.join(root, "verify", "catalog_stress.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- definitions

def test_attach_diameter_rules():
    hot = _pipe(od=48.3, ins=30.0, service="sprinkler")
    cold = _pipe(od=48.3, ins=30.0, service="chilled")
    assert [cat.attach_diameter(e, "service") for e in (hot, cold)] == [48.3, 108.3]
    assert [cat.attach_diameter(e, "bare") for e in (hot, cold)] == [48.3, 48.3]
    assert [cat.attach_diameter(e, "insulated") for e in (hot, cold)] == [108.3, 108.3]
    assert cat.attach_diameter(_pipe(od=48.3, ins=30.0, service="domestic_cold")) == 108.3
    with pytest.raises(ValueError):
        cat.attach_diameter(hot, "nope")


def test_classify_gives_exactly_one_reason():
    assert cat.classify(_pipe(od=48.3), BINS) == "covered"
    assert cat.classify(_pipe(od=48.3, load=2.5), BINS) == "covered"          # capacity is inclusive
    assert cat.classify(_pipe(od=48.3, load=2.51), BINS) == "load"
    assert cat.classify(_pipe(od=60.3), BINS) == "size"
    assert cat.classify(_pipe(od=54.0), BINS) == "covered" and cat.classify(_pipe(od=48.0), BINS) == "covered"
    assert cat.classify({**_pipe(), "kind": "duct"}, BINS) == "not_pipe"
    assert cat.classify({**_pipe(od=60.3), "kind": "cable_tray"}, BINS) == "not_pipe"   # kind is tested first


def test_tolerance_widens_both_edges():
    e = _pipe(od=114.3)                                                       # 0.3 mm above the 108-114 bin
    assert cat.classify(e, BINS, tol_mm=0.0) == "size"
    assert cat.classify(e, BINS, tol_mm=0.3) == "covered"
    assert cat.classify(_pipe(od=107.8), BINS, tol_mm=0.0) == "size"
    assert cat.classify(_pipe(od=107.8), BINS, tol_mm=0.2) == "covered"


def test_overlapping_bins_use_the_stronger_one():
    bins = [(40, 60, 1.0), (45, 65, 5.0)]
    assert cat.classify(_pipe(od=50.0, load=3.0), bins) == "covered"
    assert cat.classify(_pipe(od=50.0, load=6.0), bins) == "load"


def test_summary_counts_add_up(benchmark):
    s = cat.summary(benchmark, BINS)
    assert s["covered"] + s["size"] + s["load"] == s["pipes"]
    assert s["pipes"] + s["not_pipe"] == s["elements"] == 4500
    assert sum(t["pipes"] for t in s["per_tier"].values()) == s["pipes"]
    assert sum(t["covered"] for t in s["per_tier"].values()) == s["covered"]


def test_as_bins_accepts_tuples_and_bins():
    assert cat.as_bins(BINS) == cat.PAPER_CATALOG == (cat.Bin(48.0, 54.0, 2.5), cat.Bin(108.0, 114.0, 4.0))
    assert cat.as_bins(cat.PAPER_CATALOG) == cat.PAPER_CATALOG


def test_tasks_delegates_to_catalog(benchmark):
    cov = cm.catalog_coverage(benchmark, BINS)
    assert cov["overall"] == round(cat.summary(benchmark, BINS)["pct_pipes"], 1)
    assert cov["non_pipe_elements"] == cat.summary(benchmark, BINS)["not_pipe"]
    assert cm.COLD is cat.COLD


# --------------------------------------------------------------------------- pinned results (released benchmark)

def test_paper_catalog_on_benchmark_pinned(benchmark):
    s = cat.summary(benchmark, cat.PAPER_CATALOG)
    assert {k: s[k] for k in ("elements", "pipes", "covered", "size", "load", "not_pipe")} == \
        {"elements": 4500, "pipes": 2529, "covered": 293, "size": 2236, "load": 0, "not_pipe": 1971}
    assert round(s["pct_pipes"], 1) == 11.6


def test_load_never_binds(benchmark):
    """The heaviest pipe is far below the weakest bin, so the 'load' reason never occurs and
    the result is the same for any capacity at or above that pipe."""
    heaviest = max(e["load_kN"] for c in benchmark for e in c["elements"] if e["kind"] == "pipe")
    assert heaviest == pytest.approx(0.88) and heaviest < min(b.capacity_kN for b in cat.PAPER_CATALOG)
    strong = [(lo, hi, 100.0) for lo, hi, _ in BINS]
    assert cat.summary(benchmark, strong)["covered"] == cat.summary(benchmark, BINS)["covered"] == 293


def test_only_one_nominal_size_is_attached(benchmark):
    """Every covered pipe is DN40 (bare, or insulated cold) and no other size is covered."""
    cov, tot = Counter(), Counter()
    for c in benchmark:
        for e in c["elements"]:
            if e["kind"] == "pipe":
                tot[e["label"]] += 1
                cov[e["label"]] += cat.classify(e, cat.PAPER_CATALOG) == "covered"
    assert {k: v for k, v in cov.items() if v} == {"DN40": 293}
    assert tot["DN40"] == 293                                                 # every DN40 pipe is covered
    assert {round(cat.attach_diameter(e), 1) for c in benchmark for e in c["elements"]
            if e["kind"] == "pipe" and cat.classify(e, cat.PAPER_CATALOG) == "covered"} == {48.3, 108.3}


def test_edge_effect_on_dn100(benchmark):
    """DN100 (114.3 mm) sits 0.3 mm outside the 108-114 bin; the headline moves with the tolerance."""
    pct = lambda rule, tol: round(cat.summary(benchmark, BINS, rule, tol)["pct_pipes"], 1)
    assert pct("service", 0.0) == 11.6 and pct("service", 0.5) == 12.9 and pct("service", 1.0) == 12.9
    assert pct("bare", 0.0) == 11.6 and pct("bare", 0.5) == 16.4
    assert pct("insulated", 0.0) == 6.2 and pct("insulated", 0.5) == 7.5


def test_released_splits_agree_within_noise(all_splits):
    pcts = {s: cat.summary(c, BINS)["pct_pipes"] for s, c in all_splits.items()}
    assert all(8.5 < v < 13.0 for v in pcts.values()), pcts


# --------------------------------------------------------------------------- the exact demand optimum

def _brute_force(points, k, width):
    """Best coverage by trying every choice of k window left-edges among the distinct diameters."""
    xs = sorted(points)
    best = 0
    for starts in itertools.combinations_with_replacement(xs, min(k, len(xs))):
        covered = {x for s in starts for x in xs if s <= x <= s + width + 1e-9}
        best = max(best, sum(points[x] for x in covered))
    return best


@pytest.mark.parametrize("seed", range(12))
def test_best_windows_matches_brute_force(seed):
    rng = random.Random(seed)
    pts = {round(rng.uniform(20, 120), 1): rng.randint(1, 30) for _ in range(rng.randint(3, 9))}
    for k in (1, 2, 3):
        for width in (0.0, 6.0, 15.0, 40.0):
            n, wins = cat.best_windows(pts, k, width)
            assert n == _brute_force(pts, k, width), (seed, k, width)
            assert len(wins) <= k and all(hi - lo <= width + 1e-9 for lo, hi in wins)
            assert n == sum(w for x, w in pts.items() if any(lo <= x <= hi for lo, hi in wins))   # windows reproduce n


def test_best_windows_edge_cases():
    assert cat.best_windows({}, 3, 6.0) == (0, [])
    assert cat.best_windows({50.0: 7}, 0, 6.0) == (0, [])
    assert cat.best_windows({50.0: 7, 80.0: 5}, 1, 0.0)[0] == 7
    assert cat.best_windows({50.0: 7, 80.0: 5}, 5, 0.0)[0] == 12
    with pytest.raises(ValueError):
        cat.best_windows({50.0: 1}, -1, 6.0)


def test_demand_curve_on_benchmark(benchmark):
    pts = cat.demand_points(benchmark)
    assert sum(pts.values()) == 2529 and len(pts) == 16
    curve = cat.demand_curve(pts, 6.0)
    pcts = [r["pct"] for r in curve]
    assert pcts == sorted(pcts) and pcts[-1] == 100.0 and [r["k"] for r in curve] == list(range(1, len(curve) + 1))
    assert len(curve) == 12                                                    # 12 six-mm sizes cover all 16 diameters
    by_k = {r["k"]: round(r["pct"], 1) for r in curve}
    assert by_k[1] == 22.6 and by_k[2] == 43.0 and by_k[6] == 80.1
    assert curve[1]["windows"] == [(21.3, 26.9), (42.4, 48.3)]
    assert curve[1]["pct"] > 3 * cat.summary(benchmark, BINS)["pct_pipes"]    # two well-placed sizes vs the paper's two


def test_demand_points_respects_capacity_and_rule(benchmark):
    assert sum(cat.demand_points(benchmark, max_capacity_kN=0.0).values()) == 0
    assert sum(cat.demand_points(benchmark, max_capacity_kN=100.0).values()) == 2529
    assert len(cat.demand_points(benchmark, "bare")) < len(cat.demand_points(benchmark, "insulated")) + 1


# --------------------------------------------------------------------------- verify/catalog_stress.py

def test_cluster_interval_is_reproducible_and_brackets_estimate(cs, benchmark):
    n_pipes, n_cov, _ = cs.context_counts(benchmark, BINS, "service", 0.0)
    assert n_pipes.sum() == 2529 and n_cov.sum() == 293
    a = cs.cluster_interval(n_pipes, n_cov, 300, np.random.default_rng(5))
    b = cs.cluster_interval(n_pipes, n_cov, 300, np.random.default_rng(5))
    assert a == b
    assert a["pct"] == pytest.approx(100 * 293 / 2529) and a["lo"] < a["pct"] < a["hi"]
    wider = cs.cluster_interval(n_pipes, n_cov, 300, np.random.default_rng(5), level=0.99)
    assert wider["lo"] <= a["lo"] and wider["hi"] >= a["hi"]


def test_cluster_interval_degenerate_cases(cs):
    ones = np.ones(50)
    nothing = cs.cluster_interval(np.zeros(5), np.zeros(5), 20, np.random.default_rng(0))
    assert all(np.isnan(v) for v in nothing.values())                         # no pipes: undefined, not an error
    sparse = cs.cluster_interval(np.array([1.0, 0.0, 0.0, 0.0, 0.0]), np.array([1.0, 0, 0, 0, 0]), 200,
                                 np.random.default_rng(0))                    # resamples without the single pipe are left out
    assert sparse == {"pct": 100.0, "lo": 100.0, "hi": 100.0}
    assert cs.cluster_interval(ones, np.zeros(50), 50, np.random.default_rng(0)) == {"pct": 0.0, "lo": 0.0, "hi": 0.0}
    assert cs.cluster_interval(ones, ones, 50, np.random.default_rng(0)) == {"pct": 100.0, "lo": 100.0, "hi": 100.0}


def test_cluster_bootstrap_has_nominal_coverage(cs):
    """On synthetic clustered data with a known truth, a 90 % interval contains it about 90 % of the time."""
    truth, hits, trials = 0.3, 0, 120
    for t in range(trials):
        rng = np.random.default_rng(1000 + t)
        pipes = rng.integers(1, 9, size=80).astype(float)
        p_ctx = rng.beta(3, 7, size=80)                                       # between-context variation around 0.3
        cov = rng.binomial(pipes.astype(int), p_ctx).astype(float)
        ci = cs.cluster_interval(pipes, cov, 200, np.random.default_rng(t), level=0.90)
        hits += ci["lo"] <= 100 * truth <= ci["hi"]
    assert 0.78 <= hits / trials <= 0.97


def test_stress_test_small_run(cs, all_splits):
    r = cs.stress_test(BINS, n_boot=150, seed=1, mc_per_tier=25, mc_seed=3, splits=all_splits)
    assert set(r) == {"settings", "benchmark", "splits", "population", "by_size", "by_size_all_splits",
                      "sensitivity", "demand"}
    b = r["benchmark"]
    assert (b["pipes"], b["covered"], b["size"], b["load"], b["not_pipe"]) == (2529, 293, 2236, 0, 1971)
    assert b["covered"] + b["size"] + b["load"] == b["pipes"]
    assert b["ci"][0] < b["pct_pipes"] < b["ci"][1] and round(b["pct_all_elements"], 1) == 6.5
    assert b["max_pipe_load_kN"] == pytest.approx(0.88) and b["min_bin_capacity_kN"] == 2.5
    assert list(b["per_tier"]) == [f"C{n}" for n in range(1, 9)]
    assert sum(v["pipes"] for v in b["per_tier"].values()) == 2529
    assert set(r["splits"]) == {"train", "val", "test", "benchmark"}
    assert set(r["population"]["per_tier"]) == set(b["per_tier"]) and r["population"]["overall"]["lo"] < 100
    assert {k for k, v in r["by_size"].items() if v["covered"]} == {"DN40"}
    assert r["by_size"]["DN40"] == {"pipes": 293, "covered": 293}
    assert [(x["rule"], x["tol_mm"]) for x in r["sensitivity"]] == [(ru, t) for ru in cat.DIAMETER_RULES for t in (0.0, 0.5, 1.0)]
    assert r["demand"]["distinct_diameters"] == 16 and r["demand"]["curve"][-1]["pct"] == 100.0
    assert r["demand"]["width_mm"] == 6.0 and r["demand"]["curve_all_splits"][-1]["pct"] == 100.0
    bw = r["demand"]["by_width"]
    assert list(bw) == ["0", "6", "12", "24", "48"] and bw["6"]["2"] == pytest.approx(43.0, abs=0.05)
    assert all(bw[w][str(k)] <= bw[w2][str(k)] for w, w2 in zip(list(bw), list(bw)[1:]) for k in (1, 2, 3, 4, 6))  # wider is never worse
    assert all(bw[w]["1"] <= bw[w]["2"] <= bw[w]["3"] <= bw[w]["4"] <= bw[w]["6"] for w in bw)                     # more sizes is never worse
    txt = cs.render(r)
    assert "11.6 %" in txt and "DN40 293/293" in txt and "k =  2:  43.0" in txt


def test_stress_test_is_deterministic(cs, all_splits):
    kw = dict(n_boot=100, seed=2, mc_per_tier=10, mc_seed=4, splits=all_splits)
    first, second = (json.dumps(cs.stress_test(BINS, **kw), sort_keys=True) for _ in range(2))
    assert first == second


def test_stress_test_skips_population_when_asked(cs, all_splits):
    r = cs.stress_test(BINS, n_boot=50, mc_per_tier=0, splits=all_splits)
    assert "population" not in r
    assert "population" not in cs.render(r)


def test_parse_bins_and_main(cs, capsys):
    assert cs.parse_bins("40:60:2.0,100:120:3.5") == (cat.Bin(40.0, 60.0, 2.0), cat.Bin(100.0, 120.0, 3.5))
    assert cs.main(["--n-boot", "40", "--mc-per-tier", "0", "--bins", "40:60:2.0", "--json"]) == 0
    assert '"pct_pipes"' in capsys.readouterr().out


# --------------------------------------------------------------------------- documents and the deck agree with the code

def _squash(text):
    return " ".join(text.split())


def test_results_md_carries_the_stress_test(root):
    """RESULTS.md prints verify/catalog_stress.py; its deterministic lines must match the code."""
    text = _squash(open(os.path.join(root, "RESULTS.md"), encoding="utf-8").read())
    for line in ("## Catalog stress test (paper section 5.3)",
                 "Benchmark: 2,529 pipes, 4,500 elements",
                 "attachable pipes 293 = 11.6 % of pipes",
                 "missed: no size fits 2,236 pipes; too heavy 0 pipes; not a pipe 1,971 elements",
                 "heaviest pipe 0.88 kN vs weakest bin 2.5 kN -> load never binds",
                 "DN40 293/293",
                 "service 11.6 (10.7) 12.9 (12.2) 12.9 (12.2)",
                 "bare 11.6 (10.7) 16.4 (15.6) 16.4 (15.6)",
                 "insulated 6.2 ( 5.3) 7.5 ( 6.8) 7.5 ( 6.8)",
                 "k = 2: 43.0 % 21.3-26.9 42.4-48.3",
                 "k = 12: 100.0 %"):
        assert _squash(line) in text, line


def test_deck_data_matches_the_released_data(root, benchmark):
    """The slide deck prints docs/figures/deck_data.json; it must not go stale."""
    with open(os.path.join(root, "docs", "figures", "deck_data.json"), encoding="utf-8") as f:
        cd = json.load(f)["catalog"]
    s = cat.summary(benchmark, BINS)
    b = cd["benchmark"]
    assert {k: b[k] for k in ("elements", "pipes", "covered", "size", "load", "not_pipe")} == \
        {k: s[k] for k in ("elements", "pipes", "covered", "size", "load", "not_pipe")}
    assert b["pct_pipes"] == pytest.approx(s["pct_pipes"]) and b["ci"][0] < b["pct_pipes"] < b["ci"][1]
    assert cd["by_size"]["DN40"] == {"pipes": 293, "covered": 293}
    curve = cat.demand_curve(cat.demand_points(benchmark), cd["demand"]["width_mm"])
    assert [r["k"] for r in cd["demand"]["curve"]] == [r["k"] for r in curve]
    assert [r["pct"] for r in cd["demand"]["curve"]] == pytest.approx([r["pct"] for r in curve])
