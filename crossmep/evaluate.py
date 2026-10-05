"""Score a method on a CrossMEP split: per tier, with intervals, and paired comparisons.

CrossMEP contains no answers, so a method is scored by its own outcome on each
context -- for example whether it produced a feasible support assembly (binary),
or its cost relative to a reference (continuous).  This module turns one outcome
per context into the numbers a paper should report, so that results from
different methods are comparable:

* **Per tier** (C1..C8): the mean outcome with a 95 % interval -- Wilson score
  interval for binary outcomes, percentile bootstrap for continuous ones.
* **Tier-balanced overall** (``macro``): the mean of the tier means, i.e. every
  difficulty level counts the same, which is what the stratified benchmark is
  designed for; with a stratified bootstrap interval.
* **Overall** (``micro``): every context counts the same (equal to ``macro`` on
  the balanced benchmark split).
* **Weighted** (optional): tier means weighted by a target mix, e.g. the share of
  supports of each size in a real building, to estimate performance on that
  building rather than on the balanced benchmark.
* **First tier below a threshold** (optional): the first tier whose whole
  interval lies below a success threshold -- a conservative "where does the
  method collapse" measure.
* **Paired comparison** of two methods on the same contexts: per-tier and
  tier-balanced differences with paired stratified-bootstrap intervals and, for
  binary outcomes, the exact McNemar test.

Every context of the split must have exactly one outcome: a missing or unknown
context id is an error, never silently dropped.

Standard library only.  Command line: ``python -m crossmep evaluate``.
"""
from __future__ import annotations

import math
import numbers
import random
from statistics import NormalDist
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union

Outcome = Union[bool, int, float]
TIERS = tuple(f"C{n}" for n in range(1, 9))


class EvaluationError(ValueError):
    """The results do not match the split (missing, unknown or invalid outcomes)."""


# --------------------------------------------------------------------------- inputs

def _check(results: Mapping[str, Outcome], contexts: Sequence[Mapping]) -> Tuple[Dict[str, List[float]], bool]:
    ids = [c["context_id"] for c in contexts]
    if len(set(ids)) != len(ids):
        raise EvaluationError("context ids are not unique in this split")
    missing = [i for i in ids if i not in results]
    unknown = [k for k in results if k not in set(ids)]
    if missing:
        raise EvaluationError(f"{len(missing)} contexts have no outcome, e.g. {missing[:3]}")
    if unknown:
        raise EvaluationError(f"{len(unknown)} outcomes for contexts not in this split, e.g. {unknown[:3]}")
    values = []
    for k in ids:
        v = results[k]
        if not isinstance(v, (bool, numbers.Real)) or not math.isfinite(float(v)):
            raise EvaluationError(f"outcome of {k!r} must be a finite number or a boolean, got {v!r}")
        values.append(float(v))
    binary = all(v in (0.0, 1.0) for v in values)
    by_tier: Dict[str, List[float]] = {}
    for c, v in zip(contexts, values):
        by_tier.setdefault(c["tier"], []).append(v)
    return {t: by_tier[t] for t in sorted(by_tier, key=_tier_key)}, binary


def _tier_key(t: str):
    return (0, int(t[1:])) if t[:1] == "C" and t[1:].isdigit() else (1, t)


# --------------------------------------------------------------------------- statistics

def _z(level: float) -> float:
    return NormalDist().inv_cdf(0.5 + level / 2.0)


def wilson(successes: int, n: int, level: float = 0.95) -> Tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (float("nan"), float("nan"))
    z = _z(level)
    p = successes / n
    den = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    lo = 0.0 if successes == 0 else max(0.0, centre - half)
    hi = 1.0 if successes == n else min(1.0, centre + half)
    return (lo, hi)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the discordant counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2.0 ** n
    return min(1.0, 2.0 * tail)


def _mean(xs: Sequence[float]) -> float:
    return math.fsum(xs) / len(xs)


def _percentile(sorted_xs: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile (NumPy's default) of an already sorted list."""
    if not sorted_xs:
        return float("nan")
    pos = (len(sorted_xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return sorted_xs[lo] + (sorted_xs[hi] - sorted_xs[lo]) * (pos - lo)


def _interval(stats: List[float], level: float) -> Tuple[float, float]:
    s = sorted(stats)
    a = (1.0 - level) / 2.0
    return (_percentile(s, a), _percentile(s, 1.0 - a))


def _normalise(weights: Optional[Mapping[str, float]], tiers: Sequence[str]) -> Optional[Dict[str, float]]:
    if weights is None:
        return None
    unknown = [t for t in weights if t not in tiers]
    if unknown:
        raise EvaluationError(f"weights for tiers not in the split: {unknown}")
    if any(w < 0 for w in weights.values()):
        raise EvaluationError("tier weights must be non-negative")
    total = math.fsum(weights.get(t, 0.0) for t in tiers)
    if total <= 0:
        raise EvaluationError("tier weights sum to zero")
    return {t: weights.get(t, 0.0) / total for t in tiers}


def _aggregate(tier_means: Mapping[str, float], w: Optional[Mapping[str, float]]) -> float:
    if w is None:
        return _mean(list(tier_means.values()))
    return math.fsum(tier_means[t] * w[t] for t in tier_means)


# --------------------------------------------------------------------------- scoring

def score(results: Mapping[str, Outcome], contexts: Sequence[Mapping], weights: Optional[Mapping[str, float]] = None,
          threshold: Optional[float] = None, level: float = 0.95, n_boot: int = 2000, seed: int = 0) -> Dict:
    """Per-tier and overall results with intervals (see the module docstring)."""
    by_tier, binary = _check(results, contexts)
    tiers = list(by_tier)
    w = _normalise(weights, tiers)
    per_tier: Dict[str, Dict] = {}
    rng = random.Random(seed)
    for t, xs in by_tier.items():
        m = _mean(xs)
        if binary:
            lo, hi = wilson(int(round(sum(xs))), len(xs), level)
        else:
            lo, hi = _interval([_mean([xs[rng.randrange(len(xs))] for _ in xs]) for _ in range(n_boot)], level)
        per_tier[t] = {"n": len(xs), "mean": m, "lo": lo, "hi": hi}
    means = {t: v["mean"] for t, v in per_tier.items()}
    all_values = [x for xs in by_tier.values() for x in xs]
    boot = {"macro": [], "micro": [], "weighted": []}
    for _ in range(n_boot):
        res = {t: [xs[rng.randrange(len(xs))] for _ in xs] for t, xs in by_tier.items()}
        tm = {t: _mean(v) for t, v in res.items()}
        boot["macro"].append(_aggregate(tm, None))
        boot["micro"].append(_mean([x for v in res.values() for x in v]))
        if w is not None:
            boot["weighted"].append(_aggregate(tm, w))
    out = {"outcome": "binary" if binary else "continuous", "n": len(all_values), "level": level,
           "per_tier": per_tier}
    for key, est in (("macro", _aggregate(means, None)), ("micro", _mean(all_values))):
        lo, hi = _interval(boot[key], level)
        out[key] = {"mean": est, "lo": lo, "hi": hi}
    if w is not None:
        lo, hi = _interval(boot["weighted"], level)
        out["weighted"] = {"mean": _aggregate(means, w), "lo": lo, "hi": hi, "weights": w}
    if threshold is not None:
        below = next((t for t, v in per_tier.items() if v["hi"] < threshold), None)
        out["first_tier_below"] = {"threshold": threshold, "tier": below}
    return out


def compare(results_a: Mapping[str, Outcome], results_b: Mapping[str, Outcome], contexts: Sequence[Mapping],
            level: float = 0.95, n_boot: int = 2000, seed: int = 0) -> Dict:
    """Paired comparison of method A against method B on the same contexts (A - B)."""
    a_tier, a_bin = _check(results_a, contexts)
    b_tier, b_bin = _check(results_b, contexts)
    rng = random.Random(seed)
    per_tier: Dict[str, Dict] = {}
    pairs = {t: list(zip(a_tier[t], b_tier[t])) for t in a_tier}
    for t, ps in pairs.items():
        d = [x - y for x, y in ps]
        lo, hi = _interval([_mean([d[rng.randrange(len(d))] for _ in d]) for _ in range(n_boot)], level)
        per_tier[t] = {"n": len(d), "diff": _mean(d), "lo": lo, "hi": hi}
    est = _mean([v["diff"] for v in per_tier.values()])
    stats = []
    for _ in range(n_boot):
        stats.append(_mean([_mean([x - y for x, y in (ps[rng.randrange(len(ps))] for _ in ps)]) for ps in pairs.values()]))
    lo, hi = _interval(stats, level)
    out = {"level": level, "per_tier": per_tier, "macro": {"diff": est, "lo": lo, "hi": hi}}
    if a_bin and b_bin:
        b = sum(1 for ps in pairs.values() for x, y in ps if x == 1.0 and y == 0.0)
        c = sum(1 for ps in pairs.values() for x, y in ps if x == 0.0 and y == 1.0)
        out["mcnemar"] = {"a_only": b, "b_only": c, "p": mcnemar_exact(b, c)}
    return out


# --------------------------------------------------------------------------- text

def render(s: Dict, name: str = "method") -> str:
    pct = s["outcome"] == "binary"
    f = (lambda x: f"{100 * x:5.1f}") if pct else (lambda x: f"{x:8.3f}")
    unit = " (%)" if pct else ""
    L = [f"{name}: {s['n']:,} contexts, {s['outcome']} outcome, {100 * s['level']:.0f} % intervals",
         f"{'tier':<6}{'n':>5}  mean{unit}   interval"]
    for t, v in s["per_tier"].items():
        L.append(f"{t:<6}{v['n']:>5}  {f(v['mean'])}   {f(v['lo']).strip()}-{f(v['hi']).strip()}")
    L.append(f"tier-balanced  {f(s['macro']['mean'])}   {f(s['macro']['lo']).strip()}-{f(s['macro']['hi']).strip()}")
    L.append(f"all contexts   {f(s['micro']['mean'])}   {f(s['micro']['lo']).strip()}-{f(s['micro']['hi']).strip()}")
    if "weighted" in s:
        L.append(f"weighted mix   {f(s['weighted']['mean'])}   {f(s['weighted']['lo']).strip()}-{f(s['weighted']['hi']).strip()}")
    if "first_tier_below" in s:
        fb = s["first_tier_below"]
        L.append(f"first tier whose interval lies below {fb['threshold']:g}: {fb['tier'] or 'none'}")
    return "\n".join(L)


def render_comparison(c: Dict, a: str = "A", b: str = "B") -> str:
    L = [f"{a} - {b}, paired, {100 * c['level']:.0f} % intervals", f"{'tier':<6}{'n':>5}  diff     interval"]
    for t, v in c["per_tier"].items():
        L.append(f"{t:<6}{v['n']:>5}  {v['diff']:+.3f}   {v['lo']:+.3f} to {v['hi']:+.3f}")
    m = c["macro"]
    L.append(f"tier-balanced  {m['diff']:+.3f}   {m['lo']:+.3f} to {m['hi']:+.3f}")
    if "mcnemar" in c:
        mc = c["mcnemar"]
        L.append(f"McNemar exact: {a} only {mc['a_only']}, {b} only {mc['b_only']}, p = {mc['p']:.3g}")
    return "\n".join(L)
