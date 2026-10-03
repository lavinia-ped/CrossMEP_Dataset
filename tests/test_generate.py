"""Generator invariants over unseen seeds, determinism, and the custom API."""
import numpy as np
import pytest

from crossmep import generate as G
from crossmep.model import (ELECTRICAL_KINDS, WET_TRADES, depth_out, is_valid, span_along,
                            validate_context)


@pytest.mark.parametrize("seed", list(range(0, 200, 7)))
def test_every_context_valid_any_seed(seed):
    for c in G.generate_dataset(40, seed=seed):
        validate_context(c)                      # generate() already validates; be explicit


@pytest.mark.parametrize("n", list(range(1, 9)))
def test_tier_exact_element_count(n):
    for c in G.generate_dataset(80, seed=3, tier=f"C{n}"):
        assert len(c.elements) == n and c.tier == f"C{n}"


def test_tiers_round_robin_and_ids():
    d = G.generate_dataset(16, seed=1)
    assert [c.tier for c in d] == [f"C{i % 8 + 1}" for i in range(16)]
    assert [c.context_id for c in d] == [f"mep_{i}" for i in range(16)]


def test_c1_covers_all_kinds():
    kinds = {c.elements[0].kind for c in G.generate_dataset(400, seed=11, tier="C1")}
    assert kinds == {"pipe", "cable_tray", "duct", "conduit"}


def test_single_element_has_no_stagger_and_one_row():
    for c in G.generate_dataset(50, seed=5, tier="C1"):
        assert c.n_levels == 1 and c.elements[0].level == 0
        assert c.elements[0].position_along_mm == 0.0


def test_rows_and_levels_bounds():
    for c in G.generate_dataset(800, seed=21):
        assert 1 <= c.n_levels <= 3
        if c.surface.kind == "wall":
            assert c.n_levels <= 2
        if len(c.elements) <= 5:
            assert c.n_levels <= 2


def test_determinism_and_seed_sensitivity():
    a = [c.to_dict() for c in G.generate_dataset(200, seed=42)]
    b = [c.to_dict() for c in G.generate_dataset(200, seed=42)]
    assert a == b
    assert a != [c.to_dict() for c in G.generate_dataset(200, seed=43)]


def test_surface_mix_is_design_parameter():
    d = G.generate_dataset(4000, seed=99)
    share = np.mean([c.surface.kind == "ceiling" for c in d])
    assert abs(share - G.SURFACE_P[0]) < 0.02


def _drip_violations(contexts):
    bad = 0
    for c in contexts:
        surf = c.surface
        pipes = [e for e in c.elements if e.kind == "pipe" and e.trade in WET_TRADES]
        elec = [e for e in c.elements if e.kind in ELECTRICAL_KINDS]
        for p in pipes:
            for t in elec:
                if surf.kind == "ceiling":
                    overlap = abs(p.position_along_mm - t.position_along_mm) < \
                        (span_along(p, surf) + span_along(t, surf)) / 2
                    bad += p.position_out_mm < t.position_out_mm and overlap
                else:
                    oo = abs(p.position_out_mm - t.position_out_mm) < \
                        (depth_out(p, surf) + depth_out(t, surf)) / 2
                    bad += p.position_along_mm < t.position_along_mm and oo
    return bad


def test_no_wet_above_electrical():
    assert _drip_violations(G.generate_dataset(600, seed=42)) == 0


def test_gap_floor_and_cap_hold():
    import crossmep.tasks as cm
    from crossmep.layout import GAP_CAP_MM, GAP_FLOOR_MM
    gaps = [g for c in G.generate_dataset(500, seed=8) for g in cm.neighbour_gaps(c.to_dict(), "envelope")]
    assert min(gaps) >= GAP_FLOOR_MM - 0.2 and max(gaps) <= GAP_CAP_MM + 0.2


# ---------- custom API ----------

def _kinds(c):
    k = {"pipe": 0, "cable_tray": 0, "duct": 0, "conduit": 0}
    for e in c.elements:
        k[e.kind] += 1
    return k["pipe"], k["cable_tray"], k["duct"], k["conduit"]


def test_generate_custom_exact_composition():
    for c in G.generate_custom(40, pipes=3, trays=1, ducts=1, conduits=2, seed=5):
        assert _kinds(c) == (3, 1, 1, 2) and c.tier == "custom" and is_valid(c)


def test_generate_custom_ranges_and_surface():
    for c in G.generate_custom(60, pipes=(2, 4), conduits=(0, 3), surface="wall", seed=9):
        p, _, _, k = _kinds(c)
        assert 2 <= p <= 4 and 0 <= k <= 3 and c.surface.kind == "wall"


def test_generate_custom_trades_restriction():
    for c in G.generate_custom(40, pipes=(1, 3), trades=["chilled"], seed=2):
        assert all(e.trade == "chilled" for e in c.elements if e.kind == "pipe")


def test_generate_custom_deterministic():
    a = [c.to_dict() for c in G.generate_custom(20, pipes=2, trays=1, seed=77)]
    b = [c.to_dict() for c in G.generate_custom(20, pipes=2, trays=1, seed=77)]
    assert a == b


def test_generate_custom_single_element_and_drip_rule():
    for c in G.generate_custom(30, ducts=1, seed=4):
        assert len(c.elements) == 1 and c.elements[0].kind == "duct"
    assert _drip_violations(G.generate_custom(60, pipes=2, trays=1, surface="wall", seed=6)) == 0


def test_generate_custom_input_validation():
    for bad in [dict(pipes=-1), dict(), dict(pipes=13), dict(pipes=2, surface="floor"),
                dict(pipes=2, trades=["gas"]), dict(pipes=(3, 1)), dict(pipes=True), dict(pipes=1.5)]:
        with pytest.raises(ValueError):
            G.generate_custom(5, **bad)
    with pytest.raises(ValueError):
        G.generate_custom(0, pipes=1)


def test_generate_split_names():
    assert set(G.CANONICAL_SPLITS) == {"train", "val", "test", "benchmark"}
    with pytest.raises(KeyError):
        G.generate_split("nope")
