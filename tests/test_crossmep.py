"""CrossMEP quality gates. Run: pytest tests/test_crossmep.py -q
Covers: JSON Schema validity of all splits, geometric invariants over many seeds,
byte-determinism, distribution drift, and convention compliance."""
import json, glob, os, sys, hashlib
import numpy as np
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import mep_context_sampler as M

SPLITS = sorted(glob.glob(os.path.join(HERE, "mep_contexts_v3.0_*.json")))


# ---------- schema ----------
def test_all_splits_match_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.load(open(os.path.join(HERE, "schema", "context-v3.schema.json")))
    assert SPLITS, "no split files found"
    for path in SPLITS:
        jsonschema.validate(json.load(open(path)), schema)


# ---------- geometric invariants over many seeds ----------
@pytest.mark.parametrize("seed", list(range(0, 200, 7)))
def test_no_overlaps_any_seed(seed):
    for c in M.generate_dataset(40, seed=seed):
        M.validate_context(c)


@pytest.mark.parametrize("n", list(range(1, 9)))
def test_tier_exact_element_count(n):
    for c in M.generate_dataset(80, seed=3, tier=f"C{n}"):
        assert len(c.elements) == n


def test_c1_covers_all_kinds():
    kinds = {c.elements[0].kind for c in M.generate_dataset(400, seed=11, tier="C1")}
    assert kinds == {"pipe", "cable_tray", "duct", "conduit"}


def test_generate_custom_exact_composition():
    for c in M.generate_custom(40, pipes=3, trays=1, ducts=1, conduits=2, seed=5):
        M.validate_context(c)
        k = {"pipe": 0, "cable_tray": 0, "duct": 0, "conduit": 0}
        for e in c.elements:
            k[e.kind] += 1
        assert (k["pipe"], k["cable_tray"], k["duct"], k["conduit"]) == (3, 1, 1, 2)
        assert c.tier == "custom"


def test_generate_custom_ranges_and_surface():
    for c in M.generate_custom(60, pipes=(2, 4), conduits=(0, 3),
                               surface="wall", seed=9):
        M.validate_context(c)
        n_p = sum(e.kind == "pipe" for e in c.elements)
        n_c = sum(e.kind == "conduit" for e in c.elements)
        assert 2 <= n_p <= 4 and 0 <= n_c <= 3
        assert c.surface.kind == "wall"


def test_generate_custom_trades_restriction():
    for c in M.generate_custom(40, pipes=(1, 3), trades=["chilled"], seed=2):
        assert all(e.trade == "chilled" for e in c.elements if e.kind == "pipe")


def test_generate_custom_deterministic():
    a = [c.to_dict() for c in M.generate_custom(20, pipes=2, trays=1, seed=77)]
    b = [c.to_dict() for c in M.generate_custom(20, pipes=2, trays=1, seed=77)]
    assert a == b


def test_generate_custom_single_element_and_drip_rule():
    for c in M.generate_custom(30, ducts=1, seed=4):
        assert len(c.elements) == 1 and c.elements[0].kind == "duct"
    WET = {"domestic", "heating", "chilled", "sprinkler"}
    for c in M.generate_custom(60, pipes=2, trays=1, surface="wall", seed=6):
        for p_ in [e for e in c.elements if e.kind == "pipe" and e.trade in WET]:
            for t_ in [e for e in c.elements if e.kind in ("cable_tray", "conduit")]:
                oo = abs(p_.position_out_mm - t_.position_out_mm) < \
                    (M._depth(p_, c.surface) + M._depth(t_, c.surface)) / 2
                assert not (p_.position_along_mm < t_.position_along_mm and oo)


def test_generate_custom_input_validation():
    for bad in [dict(pipes=-1), dict(), dict(pipes=13),
                dict(pipes=2, surface="floor"), dict(pipes=2, trades=["gas"]),
                dict(pipes=(3, 1))]:
        with pytest.raises(ValueError):
            M.generate_custom(5, **bad)


def test_filter_contexts():
    import crossmep_tasks as cm
    data = cm.load("benchmark", root=HERE)
    sel = cm.filter_contexts(data, pipes=2, trays=1)
    assert all(cm.kind_counts(c)["pipe"] == 2 and cm.kind_counts(c)["cable_tray"] == 1
               for c in sel) and len(sel) > 0
    sel = cm.filter_contexts(data, ducts=(1, None), surface="ceiling")
    assert all(cm.kind_counts(c)["duct"] >= 1 and c["surface"]["kind"] == "ceiling"
               for c in sel) and len(sel) > 0
    assert len(cm.filter_contexts(data, elements=(7, 8))) == 250


def test_loads_positive_and_monotone_in_size():
    assert all(v > 0 for v in M.DN_LOAD_KN.values())
    dns = sorted(M.DN_LOAD_KN)
    assert all(M.DN_LOAD_KN[a] < M.DN_LOAD_KN[b] for a, b in zip(dns, dns[1:]))
    tws = sorted(M.TRAY_LOAD_KN)
    assert all(M.TRAY_LOAD_KN[a] < M.TRAY_LOAD_KN[b] for a, b in zip(tws, tws[1:]))


def test_insulation_schedule():
    assert M.insulation_mm("heating", 15) == 20.0
    assert M.insulation_mm("heating", 100) == 100.0
    assert M.insulation_mm("chilled", 25) == 30.0  # UNOG schedule
    assert M.insulation_mm("chilled", 65) == 50.0
    assert M.insulation_mm("sprinkler", 50) == 0.0
    assert M.insulation_mm("domestic_cold", 25) == 0.0


def test_surface_axis_mapping():
    """On ceilings, span = width; on walls, span = height (the section rotates)."""
    e = M.Element("duct", "duct", "ventilation", "rect", 400.0, 250.0, 0.0, 0.2, "d")
    ceil = M.MountingSurface("ceiling", "concrete_C25", 200.0)
    wall = M.MountingSurface("wall", "concrete_C25", 200.0)
    assert M._span(e, ceil) > M._span(e, wall)          # 400-based vs 250-based
    assert M._depth(e, ceil) < M._depth(e, wall)


# ---------- determinism ----------
def _digest(n, seed):
    d = M.generate_dataset(n, seed=seed)
    payload = json.dumps([c.to_dict() for c in d], sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def test_byte_determinism():
    assert _digest(200, 42) == _digest(200, 42)


def test_released_benchmark_reproduces():
    path = os.path.join(HERE, "mep_contexts_v3.0_benchmark.json")
    released = json.load(open(path))
    regen = [c.to_dict() for c in M.generate_dataset(1000, seed=42)]
    assert released["contexts"] == regen


# ---------- distribution drift (reference stats from v2.0 release) ----------
REF = {"gap_median": 150.0, "spread_t2p_median": 93.0, "pipe_share": 0.562}

def test_distribution_drift():
    d = M.generate_dataset(1000, seed=777)            # unseen seed
    gaps, spreads, kinds = [], [], {"pipe": 0, "other": 0}
    for c in d:
        for e in c.elements:
            kinds["pipe" if e.kind == "pipe" else "other"] += 1
        for lvl in {e.level for e in c.elements}:
            row = sorted([e for e in c.elements if e.level == lvl],
                         key=lambda e: e.position_along_mm)
            for a, b in zip(row, row[1:]):
                gaps.append((b.position_along_mm - a.position_along_mm)
                            - M._span(a, c.surface) / 2 - M._span(b, c.surface) / 2)
            if len(row) >= 2 and c.tier != "C1":
                outs = [e.position_out_mm for e in row]
                spreads.append(max(outs) - min(outs))
    assert abs(np.median(gaps) - REF["gap_median"]) < 30
    assert abs(np.median(spreads) - REF["spread_t2p_median"]) < 25
    share = kinds["pipe"] / sum(kinds.values())
    assert abs(share - REF["pipe_share"]) < 0.06


# ---------- conventions ----------
def test_no_wet_above_electrical():
    WET = {"domestic", "heating", "chilled", "sprinkler"}
    for c in M.generate_dataset(600, seed=42):
        surf = c.surface
        pipes = [e for e in c.elements if e.kind == "pipe" and e.trade in WET]
        elec = [e for e in c.elements if e.kind in ("cable_tray", "conduit")]
        for p in pipes:
            for t in elec:
                if surf.kind == "ceiling":
                    overlap = abs(p.position_along_mm - t.position_along_mm) < \
                        (M._span(p, surf) + M._span(t, surf)) / 2
                    assert not (p.position_out_mm < t.position_out_mm and overlap)
                else:
                    oo = abs(p.position_out_mm - t.position_out_mm) < \
                        (M._depth(p, surf) + M._depth(t, surf)) / 2
                    assert not (p.position_along_mm < t.position_along_mm and oo)
