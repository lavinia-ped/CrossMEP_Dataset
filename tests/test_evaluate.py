"""crossmep.evaluate: interval formulas, scoring, paired comparison, validation, CLI."""
import json
import math
import random

import pytest

import crossmep.evaluate as ev
from crossmep.cli import main


def _ctxs(n_per_tier=20, tiers=("C1", "C2", "C3")):
    return [{"context_id": f"{t}_{i}", "tier": t} for t in tiers for i in range(n_per_tier)]


def test_wilson_reference_values():
    assert ev.wilson(5, 10) == pytest.approx((0.2366, 0.7634), abs=1e-4)
    assert ev.wilson(0, 10) == (0.0, pytest.approx(0.2775, abs=1e-4))
    assert ev.wilson(10, 10) == (pytest.approx(0.7225, abs=1e-4), 1.0)
    assert ev.wilson(81, 263) == pytest.approx((0.2553, 0.3662), abs=1e-4)
    lo90, hi90 = ev.wilson(5, 10, level=0.90)
    assert 0.2366 < lo90 and hi90 < 0.7634


def test_wilson_coverage():
    rng = random.Random(7)
    for p, n in ((0.3, 50), (0.9, 125), (0.05, 125)):
        hits = 0
        for _ in range(2000):
            x = sum(rng.random() < p for _ in range(n))
            lo, hi = ev.wilson(x, n)
            hits += lo <= p <= hi
        assert 0.92 <= hits / 2000 <= 0.98, (p, n, hits)


def test_mcnemar_exact():
    assert ev.mcnemar_exact(10, 2) == pytest.approx(158 / 4096)
    assert ev.mcnemar_exact(2, 10) == ev.mcnemar_exact(10, 2)
    assert ev.mcnemar_exact(0, 0) == 1.0 and ev.mcnemar_exact(5, 5) == 1.0
    assert ev.mcnemar_exact(0, 6) == pytest.approx(2 / 64)


def test_score_binary_tiers_and_aggregates():
    ctx = _ctxs(20)
    res = {c["context_id"]: (c["tier"] == "C1" or (c["tier"] == "C2" and int(c["context_id"].split("_")[1]) < 10))
           for c in ctx}
    s = ev.score(res, ctx, weights={"C1": 3, "C2": 1}, threshold=0.4, n_boot=300)
    assert s["outcome"] == "binary" and s["n"] == 60
    assert [s["per_tier"][t]["mean"] for t in ("C1", "C2", "C3")] == [1.0, 0.5, 0.0]
    assert s["per_tier"]["C1"]["hi"] == 1.0 and s["per_tier"]["C3"]["lo"] == 0.0
    assert s["macro"]["mean"] == pytest.approx(0.5) and s["micro"]["mean"] == pytest.approx(0.5)
    assert s["weighted"]["mean"] == pytest.approx(0.75 * 1.0 + 0.25 * 0.5)
    assert s["weighted"]["weights"] == {"C1": 0.75, "C2": 0.25, "C3": 0.0}
    assert s["first_tier_below"] == {"threshold": 0.4, "tier": "C3"}
    for k in ("macro", "micro", "weighted"):
        assert s[k]["lo"] <= s[k]["mean"] <= s[k]["hi"]


def test_macro_differs_from_micro_on_unbalanced_splits():
    ctx = [{"context_id": f"a{i}", "tier": "C1"} for i in range(30)] + [{"context_id": f"b{i}", "tier": "C2"} for i in range(10)]
    res = {c["context_id"]: c["tier"] == "C1" for c in ctx}
    s = ev.score(res, ctx, n_boot=100)
    assert s["macro"]["mean"] == pytest.approx(0.5) and s["micro"]["mean"] == pytest.approx(0.75)


def test_score_continuous_and_determinism():
    ctx = _ctxs(30)
    rng = random.Random(3)
    res = {c["context_id"]: rng.gauss(1.0 + int(c["tier"][1]), 0.2) for c in ctx}
    a = ev.score(res, ctx, n_boot=200, seed=5)
    b = ev.score(res, ctx, n_boot=200, seed=5)
    assert a == b and a["outcome"] == "continuous"
    for t in ("C1", "C2", "C3"):
        v = a["per_tier"][t]
        assert v["lo"] < v["mean"] < v["hi"] and abs(v["mean"] - (1.0 + int(t[1]))) < 0.15


def test_validation_errors():
    ctx = _ctxs(3)
    ok = {c["context_id"]: True for c in ctx}
    with pytest.raises(ev.EvaluationError, match="no outcome"):
        ev.score({k: v for k, v in list(ok.items())[1:]}, ctx)
    with pytest.raises(ev.EvaluationError, match="not in this split"):
        ev.score({**ok, "elsewhere": True}, ctx)
    for bad in (float("nan"), "yes", None, float("inf")):
        with pytest.raises(ev.EvaluationError, match="finite number"):
            ev.score({**ok, ctx[0]["context_id"]: bad}, ctx)
    with pytest.raises(ev.EvaluationError, match="not unique"):
        ev.score(ok, ctx + ctx[:1])
    with pytest.raises(ev.EvaluationError):
        ev.score(ok, ctx, weights={"C9": 1.0})
    with pytest.raises(ev.EvaluationError):
        ev.score(ok, ctx, weights={"C1": 0.0})


def test_compare_paired():
    ctx = _ctxs(40)
    a = {c["context_id"]: True for c in ctx}
    b = {c["context_id"]: int(c["context_id"].split("_")[1]) % 2 == 0 for c in ctx}
    c = ev.compare(a, b, ctx, n_boot=300)
    assert c["macro"]["diff"] == pytest.approx(0.5) and c["macro"]["lo"] > 0
    assert c["mcnemar"] == {"a_only": 60, "b_only": 0, "p": pytest.approx(2 * 0.5 ** 60)}
    same = ev.compare(a, a, ctx, n_boot=100)
    assert same["macro"] == {"diff": 0.0, "lo": 0.0, "hi": 0.0} and same["mcnemar"]["p"] == 1.0


def test_on_the_benchmark_and_cli(benchmark, tmp_path, capsys):
    rng = random.Random(0)
    res = {c["context_id"]: rng.random() < 1.0 - 0.1 * int(c["tier"][1]) for c in benchmark}
    s = ev.score(res, benchmark, n_boot=200)
    assert all(v["n"] == 125 for v in s["per_tier"].values()) and s["macro"]["mean"] == pytest.approx(s["micro"]["mean"])
    f, g = tmp_path / "a.json", tmp_path / "b.json"
    f.write_text(json.dumps(res))
    g.write_text(json.dumps({"results": {k: not v for k, v in res.items()}}))
    assert main(["evaluate", str(f), "--n-boot", "100", "--threshold", "0.5", "--against", str(g),
                 "--weights", "C1=4,C2=2,C3=1"]) == 0
    out = capsys.readouterr().out
    assert "C8" in out and "tier-balanced" in out and "weighted mix" in out and "McNemar" in out
    assert main(["evaluate", str(f), "--n-boot", "50", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["score"]["n"] == 1000
    f.write_text(json.dumps({k: v for k, v in list(res.items())[:10]}))
    assert main(["evaluate", str(f), "--n-boot", "10"]) == 2
