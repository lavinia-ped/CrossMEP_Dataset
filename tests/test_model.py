"""Data model: geometry helpers, validator, serialisation round trip, revisions."""
import math
from dataclasses import replace

import pytest

from crossmep import library as lib
from crossmep.model import (MIN_CLEAR_GAP_MM, REV_3_0, REV_4_0, REV_4_1, ContextValidationError, Element,
                            MEPContext, MountingSurface, depth_out, is_valid, pair_clearance,
                            revision_for, span_along, validate_context)

CEIL = MountingSurface("ceiling", "concrete_C25", 200.0)
WALL = MountingSurface("wall", "concrete_C25", 200.0)


def _at(e: Element, along: float, out: float, level: int = 0) -> Element:
    return replace(e, position_along_mm=along, position_out_mm=out, level=level)


def test_surface_axis_mapping():
    """On ceilings span = width; on walls span = height (the section rotates)."""
    duct = lib.make_rect_duct(400, 250)
    assert span_along(duct, CEIL) == 400 and span_along(duct, WALL) == 250
    assert depth_out(duct, CEIL) == 250 and depth_out(duct, WALL) == 400
    pipe = lib.make_pipe(50, "chilled", "chilled")          # 60.3 bare + 50 insulation per side
    assert span_along(pipe, CEIL) == pytest.approx(60.3 + 100)
    assert depth_out(pipe, CEIL) == pytest.approx(60.3 + 100)


def test_validator_clearance_rule_along():
    p = lib.make_pipe(25, "sprinkler", "sprinkler")           # OD 33.7, bare
    centre = 33.7 + MIN_CLEAR_GAP_MM                           # exactly 25 mm clear
    ok = MEPContext((_at(p, -centre / 2, 100.0), _at(p, centre / 2, 100.0)), CEIL, "custom", "ok")
    validate_context(ok)
    assert pair_clearance(ok.elements[0], ok.elements[1], CEIL) == pytest.approx(25.0)
    tight = MEPContext((_at(p, -centre / 2, 100.0), _at(p, centre / 2 - 5.0, 100.0)), CEIL, "custom", "bad")
    with pytest.raises(ContextValidationError, match="closer than 25 mm"):
        validate_context(tight)
    assert not is_valid(tight)


def test_validator_clearance_rule_out():
    p = lib.make_pipe(25, "sprinkler", "sprinkler")           # depth 33.7
    a = _at(p, 0.0, 100.0, level=0)
    too_close = _at(p, 0.0, 100.0 + 33.7 + 10.0, level=1)     # 10 mm clear OUT, overlapping ALONG
    with pytest.raises(ContextValidationError):
        validate_context(MEPContext((a, too_close), CEIL, "custom", "x"))
    cleared = _at(p, 0.0, 100.0 + 33.7 + MIN_CLEAR_GAP_MM, level=1)
    validate_context(MEPContext((a, cleared), CEIL, "custom", "y"))


def test_validator_rejects_uncentred_row_and_bad_fields():
    p = lib.make_pipe(25, "sprinkler", "sprinkler")
    with pytest.raises(ContextValidationError, match="not centred"):
        validate_context(MEPContext((_at(p, 40.0, 100.0),), CEIL, "custom", "c"))
    with pytest.raises(ContextValidationError, match="standoff"):
        validate_context(MEPContext((_at(p, 0.0, 0.0),), CEIL, "custom", "s"))
    with pytest.raises(ContextValidationError, match="no elements"):
        validate_context(MEPContext((), CEIL, "custom", "e"))
    bad = Element("pipe", "steam", "heating", "round", 33.7, 33.7, 0.0, 0.1, "DN25", 0.0, 100.0)
    with pytest.raises(ContextValidationError, match="bad kind"):
        validate_context(MEPContext((bad,), CEIL, "custom", "svc"))
    with pytest.raises(ContextValidationError, match="bad surface"):
        validate_context(MEPContext((_at(p, 0.0, 100.0),), MountingSurface("floor", "x", 200.0)))
    with pytest.raises(ContextValidationError, match="span"):
        validate_context(MEPContext((replace(_at(p, 0.0, 100.0), span_m=0.0),), CEIL))


def test_total_load_is_exactly_rounded():
    """5 x 0.021 + 0.49 + 0.06 + 0.30 = 0.955 exactly; the nearest double is below
    0.955, so the released value is 0.95 (naive left-to-right summation on
    Python < 3.12 gives 0.96)."""
    els = [lib.make_conduit(20)] * 5 + [lib.make_pipe(80, "sprinkler", "sprinkler"),
                                       lib.make_pipe(25, "sprinkler", "sprinkler"),
                                       lib.make_pipe(65, "sprinkler", "sprinkler")]
    ctx = MEPContext(tuple(els), CEIL)
    assert ctx.total_load_kN == math.fsum([0.021] * 5 + [0.49, 0.06, 0.30])
    assert ctx.to_dict()["total_load_kN"] == 0.95


def test_round_trip_both_revisions(benchmark, benchmark_v3):
    for d in benchmark:
        ctx = MEPContext.from_dict(d, REV_4_0)
        assert ctx.to_dict() == d
        validate_context(ctx)
    for d in benchmark_v3:
        ctx = MEPContext.from_dict(d, REV_3_0)
        assert ctx.to_dict() == d
        assert ctx.elements[0].span_m is None
        validate_context(ctx)


def test_revision_lookup():
    assert revision_for("4.0") is REV_4_0 and revision_for("4.1") is REV_4_1 and revision_for("4.2") is REV_4_1
    assert revision_for("3.0") is REV_3_0
    with pytest.raises(ValueError):
        revision_for("2.0")


def test_bundle_width_is_physical_and_revision_3_adds_envelopes():
    p = lib.make_pipe(15, "domestic_cold", "domestic")       # OD 21.3
    ctx4 = MEPContext((_at(p, 0.0, 100.0),), CEIL, revision=REV_4_0)
    ctx3 = MEPContext((_at(p, 0.0, 100.0),), CEIL, revision=REV_3_0)
    assert ctx4.bundle_width_mm == ctx3.bundle_width_mm == pytest.approx(21.3)
    assert ctx4.to_dict()["bundle_width_mm"] == 21.3
    assert ctx3.to_dict()["bundle_width_mm"] == 71.3
    assert "span_m" in ctx4.to_dict()["elements"][0] and "span_m" not in ctx3.to_dict()["elements"][0]


def test_pair_clearance_matches_tasks_metric(benchmark):
    import crossmep.tasks as cm
    for d in benchmark[:200]:
        ctx = MEPContext.from_dict(d)
        if len(ctx.elements) < 2:
            continue
        best = min(pair_clearance(a, b, ctx.surface)
                   for i, a in enumerate(ctx.elements) for b in ctx.elements[i + 1:])
        assert best == pytest.approx(cm.min_clear_gap(d))
