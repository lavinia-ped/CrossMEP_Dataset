"""Data model: geometry helpers, validator, serialisation round trip."""
import math

import pytest

from crossmep import library as lib
from crossmep.model import (CLEARANCE_MM, ContextValidationError, Element, MEPContext,
                            MountingSurface, depth_out, is_valid, pair_clearance, span_along,
                            validate_context)

CEIL = MountingSurface("ceiling", "concrete_C25", 200.0)
WALL = MountingSurface("wall", "concrete_C25", 200.0)


def _at(e: Element, along: float, out: float, level: int = 0) -> Element:
    from dataclasses import replace
    return replace(e, position_along_mm=along, position_out_mm=out, level=level)


def test_surface_axis_mapping():
    """On ceilings span = width; on walls span = height (the section rotates)."""
    duct = lib.make_rect_duct(400, 250)
    assert span_along(duct, CEIL) == 400 + 2 * CLEARANCE_MM
    assert span_along(duct, WALL) == 250 + 2 * CLEARANCE_MM
    assert depth_out(duct, CEIL) == 250 and depth_out(duct, WALL) == 400
    pipe = lib.make_pipe(50, "chilled", "chilled")          # 60.3 bare + 50 insulation per side
    assert span_along(pipe, CEIL) == pytest.approx(60.3 + 100 + 50)
    assert depth_out(pipe, CEIL) == pytest.approx(60.3 + 100)


def test_validator_accepts_cleared_pair_and_rejects_overlap():
    p = lib.make_pipe(25, "sprinkler", "sprinkler")           # OD 33.7, bare
    half = span_along(p, CEIL) / 2                             # 16.85 + 25
    gap = 30.0
    a = _at(p, -(half + gap / 2), 100.0)
    b = _at(p, +(half + gap / 2), 100.0)
    validate_context(MEPContext((a, b), CEIL, "custom", "ok"))
    c = _at(p, +(half + gap / 2) - 60.0, 100.0)               # envelopes overlap, same standoff
    with pytest.raises(ContextValidationError, match="not cleared"):
        validate_context(MEPContext((a, c), CEIL, "custom", "bad"))
    assert not is_valid(MEPContext((a, c), CEIL))


def test_validator_out_direction_needs_clearance_floor():
    p = lib.make_pipe(25, "sprinkler", "sprinkler")           # depth 33.7
    a = _at(p, 0.0, 100.0, level=0)
    touching = _at(p, 0.0, 100.0 + 33.7 + 10.0, level=1)      # 10 mm clear OUT, overlapping ALONG
    with pytest.raises(ContextValidationError):
        validate_context(MEPContext((a, touching), CEIL, "custom", "x"))
    cleared = _at(p, 0.0, 100.0 + 33.7 + 2 * CLEARANCE_MM, level=1)
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


def test_round_trip_benchmark(benchmark):
    for d in benchmark:
        ctx = MEPContext.from_dict(d)
        assert ctx.to_dict() == d
        validate_context(ctx)


def test_pair_clearance_matches_tasks_metric(benchmark):
    import crossmep.tasks as cm
    for d in benchmark[:200]:
        ctx = MEPContext.from_dict(d)
        if len(ctx.elements) < 2:
            continue
        best = min(pair_clearance(a, b, ctx.surface)
                   for i, a in enumerate(ctx.elements) for b in ctx.elements[i + 1:])
        assert best == pytest.approx(cm.envelope_clearance(d))


def test_bundle_width_includes_envelopes():
    p = lib.make_pipe(15, "domestic_cold", "domestic")       # OD 21.3
    ctx = MEPContext((_at(p, 0.0, 100.0),), CEIL)
    assert ctx.bundle_width_mm == pytest.approx(21.3 + 2 * CLEARANCE_MM)
