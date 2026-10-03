"""Stdlib metrics on hand-built contexts and on the released benchmark."""
import pytest

import crossmep.tasks as cm
from crossmep.model import CLEARANCE_MM


def _pipe(along, out, od=33.7, ins=0.0, service="sprinkler", level=0, load=0.06):
    return {"kind": "pipe", "service": service, "trade": "sprinkler" if service == "sprinkler" else "chilled",
            "shape": "round", "label": "DN25", "width_mm": od, "height_mm": od,
            "insulation_mm": ins, "load_kN": load, "level": level, "along_mm": along, "out_mm": out}


def _ctx(elements, surface="ceiling", tier="custom"):
    return {"context_id": "t", "tier": tier, "surface": {"kind": surface, "substrate": "concrete_C25", "thickness_mm": 200.0},
            "n_elements": len(elements), "n_levels": len({e["level"] for e in elements}),
            "total_load_kN": round(sum(e["load_kN"] for e in elements), 2),
            "bundle_width_mm": 0.0, "elements": elements}


def test_clearance_definitions_on_two_bare_pipes():
    # centres 200 mm apart, OD 33.7 each -> bare gap 166.3; envelope gap = bare - 50
    c = _ctx([_pipe(-100.0, 100.0), _pipe(100.0, 100.0)])
    assert cm.envelope_clearance(c) == pytest.approx(166.3 - 2 * CLEARANCE_MM)
    assert cm.min_clear_gap(c) == pytest.approx(166.3)
    assert cm.congestion_score is cm.envelope_clearance
    assert cm.neighbour_gaps(c, "bare") == pytest.approx([166.3])
    assert cm.neighbour_gaps(c, "insulation") == pytest.approx([166.3])
    assert cm.neighbour_gaps(c, "envelope") == pytest.approx([116.3])


def test_insulation_enters_gap_definitions():
    c = _ctx([_pipe(-100.0, 100.0, ins=30.0, service="chilled"), _pipe(100.0, 100.0)])
    assert cm.neighbour_gaps(c, "bare") == pytest.approx([166.3])
    assert cm.neighbour_gaps(c, "insulation") == pytest.approx([136.3])
    assert cm.neighbour_gaps(c, "envelope") == pytest.approx([86.3])
    assert cm.min_clear_gap(c) == pytest.approx(136.3)


def test_single_element_has_no_score():
    assert cm.envelope_clearance(_ctx([_pipe(0.0, 100.0)])) is None
    assert cm.min_clear_gap(_ctx([_pipe(0.0, 100.0)])) is None


def test_wall_uses_height_along():
    e1 = dict(_pipe(-300.0, 100.0)); e1.update(kind="duct", shape="rect", width_mm=400.0, height_mm=250.0, label="d", service="duct", trade="ventilation")
    e2 = dict(_pipe(300.0, 100.0)); e2.update(kind="duct", shape="rect", width_mm=400.0, height_mm=250.0, label="d", service="duct", trade="ventilation")
    assert cm.neighbour_gaps(_ctx([e1, e2], "wall"), "bare") == pytest.approx([600 - 250])
    assert cm.neighbour_gaps(_ctx([e1, e2], "ceiling"), "bare") == pytest.approx([600 - 400])


def test_catalog_coverage_service_correct_diameter():
    bins = [(48, 54, 2.5), (108, 114, 4.0)]
    hot = _pipe(0.0, 100.0, od=48.3, ins=30.0, service="sprinkler", load=0.10)     # bare 48.3 -> covered
    cold = _pipe(0.0, 100.0, od=48.3, ins=30.0, service="chilled", load=0.10)      # insulated 108.3 -> covered by bin 2
    cold_big = _pipe(0.0, 100.0, od=60.3, ins=30.0, service="chilled", load=0.21)  # 120.3 -> not covered
    heavy = _pipe(0.0, 100.0, od=50.0, ins=0.0, service="sprinkler", load=9.0)     # load exceeds capacity
    tray = {**_pipe(0.0, 100.0), "kind": "cable_tray"}
    data = [_ctx([hot], tier="C1"), _ctx([cold], tier="C1"), _ctx([cold_big, heavy], tier="C2"), _ctx([tray], tier="C1")]
    cov = cm.catalog_coverage(data, bins)
    assert cov == {"C1": 100.0, "C2": 0.0, "overall": 50.0, "non_pipe_elements": 1}


def test_filter_and_counts(benchmark):
    sel = cm.filter_contexts(benchmark, pipes=2, trays=1)
    assert sel and all(cm.kind_counts(c)["pipe"] == 2 and cm.kind_counts(c)["cable_tray"] == 1 for c in sel)
    sel = cm.filter_contexts(benchmark, ducts=(1, None), surface="ceiling")
    assert sel and all(cm.kind_counts(c)["duct"] >= 1 and c["surface"]["kind"] == "ceiling" for c in sel)
    assert len(cm.filter_contexts(benchmark, elements=(7, 8))) == 250
    assert len(cm.filter_contexts(benchmark, tier="C1", surface="wall")) == sum(
        c["tier"] == "C1" and c["surface"]["kind"] == "wall" for c in benchmark)
    assert all({"chilled", "electrical"} <= {e["trade"] for e in c["elements"]}
               for c in cm.filter_contexts(benchmark, trades=["chilled", "electrical"]))
    assert cm.filter_contexts(benchmark, levels=(4, None)) == []


def test_per_tier_table_and_summary(benchmark):
    table = cm.per_tier_table(benchmark)
    lines = table.splitlines()
    assert lines[0].split() == ["tier", "n_ctx", "elems", "env-clear", "mm", "clear-gap", "mm", "load", "kN", "width", "mm"]
    assert len(lines) == 9 and lines[1].startswith("C1") and lines[-1].startswith("C8")
    s = cm.tier_summary(benchmark)
    for n in range(2, 9):
        assert s[f"C{n}"]["clear_gap_mm"] >= s[f"C{n}"]["envelope_clearance_mm"]


def test_validate_dicts(benchmark):
    for c in benchmark[:100]:
        cm.validate(c)
    bad = dict(benchmark[1]); bad["elements"] = [dict(e, along_mm=0.0) for e in bad["elements"]]
    with pytest.raises(ValueError):
        cm.validate(bad)
