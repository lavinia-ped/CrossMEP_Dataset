"""Element library: derived constants equal the frozen release tables; sources hold."""
import pytest

from crossmep import library as lib

# Frozen tables of the data release (identical in revisions 3.0 and 4.0): the
# oracle for the derivations.
V30_DN_LOAD_KN = {15: 0.03, 20: 0.04, 25: 0.06, 32: 0.08, 40: 0.10, 50: 0.21,
                  65: 0.30, 80: 0.49, 100: 0.88}
V30_TRAY_LOAD_KN = {150: 0.54, 225: 0.81, 300: 1.08, 450: 1.62, 600: 2.16}
V30_RECT_DUCT_LOAD_KN = {(250, 200): 0.16, (400, 250): 0.28, (500, 400): 0.38,
                         (800, 400): 0.58, (1000, 500): 0.72}
V30_ROUND_DUCT_LOAD_KN = {160: 0.056, 200: 0.070, 250: 0.087, 315: 0.110, 400: 0.139, 500: 0.174}
V30_CONDUIT_LOAD_KN = {20: 0.021, 25: 0.029, 32: 0.044, 40: 0.063, 50: 0.092}


def _all_elements():
    els = [lib.make_pipe(dn, s, t) for dn in lib.DN_SERIES
           for s, t in (("heating", "heating"), ("chilled", "chilled"), ("sprinkler", "sprinkler"),
                        ("domestic_hot", "domestic"), ("domestic_cold", "domestic"))]
    els += [lib.make_tray(w) for w in lib.TRAY_WIDTHS_MM]
    els += [lib.make_rect_duct(*wh) for wh in lib.RECT_DUCT_SIZES_MM]
    els += [lib.make_round_duct(d) for d in lib.ROUND_DUCT_D_MM]
    els += [lib.make_conduit(od) for od in lib.CONDUIT_OD_MM]
    return els


def test_pipe_loads_derive_from_primitives():
    assert lib.DN_LOAD_KN == V30_DN_LOAD_KN


def test_tray_loads_derive_from_datum():
    assert lib.TRAY_LOAD_KN == V30_TRAY_LOAD_KN


def test_rect_duct_loads_are_walraven_cells_times_span():
    assert lib.RECT_DUCT_LOAD_KN == V30_RECT_DUCT_LOAD_KN
    assert set(lib.WALRAVEN_RECT_DUCT_KG_M) == set(lib.RECT_DUCT_SIZES_MM)


def test_round_duct_and_conduit_loads():
    assert lib.ROUND_DUCT_LOAD_KN == V30_ROUND_DUCT_LOAD_KN
    assert lib.CONDUIT_LOAD_KN == V30_CONDUIT_LOAD_KN


def test_pipe_mass_matches_log_values():
    # VERIFICATION_LOG section 2: 1.40-20.89 kg/m water-filled; DN50 = 7.25 kg/m
    assert lib.pipe_mass_kg_m(15) == pytest.approx(1.40, abs=0.01)
    assert lib.pipe_mass_kg_m(50) == pytest.approx(7.25, abs=0.01)
    assert lib.pipe_mass_kg_m(100) == pytest.approx(20.89, abs=0.01)


def test_span_floor_rule_uses_published_points_only():
    published = set(lib.ASME_B311_WATER_SPAN_M.values())
    for dn in lib.DN_SERIES:
        assert lib.support_span_m(dn) in published
    assert lib.support_span_m(15) == 2.1 and lib.support_span_m(32) == 2.1
    assert lib.support_span_m(65) == 3.0 and lib.support_span_m(80) == 3.7
    assert lib.support_span_m(100) == 4.3


def test_recorded_span_and_load_per_metre_reproduce_load():
    """load_kN == round(load_kN_per_m x span_m) for every library element, at the
    precision recorded in the files (so a reader can check the loads by hand)."""
    for e in _all_elements():
        assert e.span_m > 0 and e.load_kN_per_m > 0
        decimals = 3 if (e.kind == "conduit" or (e.kind == "duct" and e.shape == "round")) else 2
        assert round(e.load_kN_per_m * e.span_m, decimals) == e.load_kN, e.label
    assert lib.make_pipe(50, "chilled", "chilled").load_kN_per_m == pytest.approx(0.0711, abs=1e-4)
    assert lib.make_tray(300).load_kN_per_m == pytest.approx(0.5396, abs=1e-4)


def test_cable_density_back_derivation():
    assert lib.CABLE_BULK_DENSITY_KG_M3 == pytest.approx(
        lib.TRAY_FULL_CABLE_KG_M_AT_300 / (lib.CABLE_FILL_FRACTION * 0.300 * 0.100), rel=1e-3)


def test_loads_positive_and_monotone_in_size():
    for table in (lib.DN_LOAD_KN, lib.TRAY_LOAD_KN, lib.ROUND_DUCT_LOAD_KN, lib.CONDUIT_LOAD_KN):
        keys = sorted(table)
        assert all(table[k] > 0 for k in keys)
        assert all(table[a] < table[b] for a, b in zip(keys, keys[1:]))
    rect = [lib.RECT_DUCT_LOAD_KN[s] for s in lib.RECT_DUCT_SIZES_MM]
    assert rect == sorted(rect)


def test_size_series_are_standard_subsets():
    assert set(lib.CONDUIT_OD_MM) <= {16, 20, 25, 32, 40, 50, 63}          # IEC 61386-1
    assert set(lib.ROUND_DUCT_D_MM) <= {100, 125, 160, 200, 250, 315, 400, 500, 630}  # EN 1506
    assert list(lib.DN_OD_MM) == list(lib.DN_SERIES)
    assert lib.DN_OD_MM[15] == 21.3 and lib.DN_OD_MM[100] == 114.3          # EN 10220/10255


def test_insulation_schedule():
    assert lib.insulation_mm("heating", 15) == 20.0
    assert lib.insulation_mm("domestic_hot", 25) == 30.0
    assert lib.insulation_mm("heating", 65) == 65.0
    assert lib.insulation_mm("heating", 100) == 100.0
    assert lib.insulation_mm("chilled", 25) == 30.0       # UNOG schedule
    assert lib.insulation_mm("chilled", 65) == 50.0
    assert lib.insulation_mm("sprinkler", 50) == 0.0
    assert lib.insulation_mm("domestic_cold", 25) == 0.0


def test_constructors():
    p = lib.make_pipe(50, "chilled", "chilled")
    assert (p.kind, p.shape, p.width_mm, p.height_mm, p.insulation_mm, p.load_kN, p.label, p.span_m) == \
        ("pipe", "round", 60.3, 60.3, 50.0, 0.21, "DN50", 3.0)
    t = lib.make_tray(300)
    assert (t.kind, t.trade, t.width_mm, t.height_mm, t.load_kN, t.span_m) == ("cable_tray", "electrical", 300.0, 60.0, 1.08, 2.0)
    d = lib.make_rect_duct(800, 400)
    assert (d.kind, d.shape, d.load_kN, d.label, d.span_m) == ("duct", "rect", 0.58, "800x400 duct", 2.4)
    r = lib.make_round_duct(315)
    assert (r.shape, r.width_mm, r.load_kN) == ("round", 315.0, 0.110)
    c = lib.make_conduit(25)
    assert (c.kind, c.load_kN, c.label, c.span_m) == ("conduit", 0.029, "Ø25 conduit", 2.0)


def test_trade_bands():
    assert lib.dn_band("domestic") == [15, 20, 25, 32]
    assert lib.dn_band("heating") == [20, 25, 32, 40, 50, 65]
    assert lib.dn_band("chilled") == lib.dn_band("sprinkler") == [25, 32, 40, 50, 65, 80, 100]


def _reference(e: dict):
    if e["kind"] == "pipe":
        return lib.make_pipe(int(e["label"][2:]), e["service"], e["trade"])
    if e["kind"] == "cable_tray":
        return lib.make_tray(int(e["width_mm"]))
    if e["kind"] == "conduit":
        return lib.make_conduit(int(e["width_mm"]))
    if e["shape"] == "round":
        return lib.make_round_duct(int(e["width_mm"]))
    return lib.make_rect_duct(int(e["width_mm"]), int(e["height_mm"]))


def test_released_elements_use_library_values(benchmark, benchmark_v3):
    """Every element in both released benchmarks carries exactly the library's
    size, insulation, load (and, in 4.0, span and load per metre) for its
    label/service -- no hand-edited data."""
    for c in benchmark_v3:
        for e in c["elements"]:
            ref = _reference(e)
            assert (e["width_mm"], e["height_mm"], e["insulation_mm"], e["load_kN"], e["label"]) == \
                (ref.width_mm, ref.height_mm, ref.insulation_mm, ref.load_kN, ref.label), c["context_id"]
    for c in benchmark:
        for e in c["elements"]:
            ref = _reference(e)
            assert (e["width_mm"], e["height_mm"], e["insulation_mm"], e["load_kN"], e["label"],
                    e["span_m"], e["load_kN_per_m"]) == \
                (ref.width_mm, ref.height_mm, ref.insulation_mm, ref.load_kN, ref.label,
                 ref.span_m, ref.load_kN_per_m), c["context_id"]
