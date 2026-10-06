"""The released files of both data revisions: integrity, byte-exact regeneration,
schema, and the numbers reported in the CIB W78 2026 paper that reproduce."""
import hashlib
import json
import os
from collections import Counter

import numpy as np
import pytest

import crossmep.tasks as cm
from crossmep import generate as G
from crossmep import io
from crossmep.model import MEPContext, revision_for, validate_context

SPLITS = ("train", "val", "test", "benchmark")
VERSIONS = ("4.1", "4.0", "3.0")


def _checksums(root):
    out = {}
    with open(os.path.join(root, "RELEASE_CHECKSUMS.txt")) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                digest, name = line.split()
                out[name] = digest
    return out


def test_released_files_match_checksums(root):
    sums = _checksums(root)
    assert set(sums) == set(io.release_files(root))
    for rel, digest in sums.items():
        assert io.sha256_file(os.path.join(root, rel)) == digest, rel


@pytest.mark.parametrize("version", VERSIONS)
@pytest.mark.parametrize("split", SPLITS)
def test_split_regenerates_byte_for_byte(version, split, root):
    spec = G.CANONICAL_SPLITS[split]
    text = io.dumps(io.build_payload(G.generate_split(split, version), split=split, seed=spec["seed"]))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == io.sha256_file(io.split_path(split, root, version))


@pytest.mark.parametrize("version", VERSIONS)
def test_all_splits_match_schema(version, root):
    jsonschema = pytest.importorskip("jsonschema")
    with open(io.schema_path(version, root)) as f:
        schema = json.load(f)
    for s in SPLITS:
        jsonschema.validate(io.read_payload(io.split_path(s, root, version)), schema)


@pytest.mark.parametrize("version", VERSIONS)
def test_metadata_consistent(version):
    for s in SPLITS:
        payload = io.read_payload(io.split_path(s, version=version))
        spec = G.CANONICAL_SPLITS[s]
        data = payload["contexts"]
        assert payload["seed"] == spec["seed"] and payload["n_contexts"] == spec["n"] == len(data)
        assert payload["version"] == version and payload["split"] == s
        for c in data:
            assert c["n_elements"] == len(c["elements"]) == int(c["tier"][1:])
            assert c["n_levels"] == len({e["level"] for e in c["elements"]})


def test_every_released_context_validates(all_splits, all_splits_v3):
    for data in all_splits.values():
        for d in data:
            validate_context(MEPContext.from_dict(d))
    for data in all_splits_v3.values():
        for d in data:
            validate_context(MEPContext.from_dict(d, revision_for("3.0")))


def test_revisions_differ_only_in_along_positions(all_splits_v40, all_splits_v3):
    """4.0 = 3.0 with the double-counted clearance removed: identical elements,
    loads, levels and standoffs; along-positions and bundle widths change."""
    strip = ("along_mm", "span_m", "load_kN_per_m")
    for s in SPLITS:
        for c4, c3 in zip(all_splits_v40[s], all_splits_v3[s]):
            assert c4["total_load_kN"] == c3["total_load_kN"] and c4["n_levels"] == c3["n_levels"]
            assert c4["surface"] == c3["surface"] and c4["tier"] == c3["tier"]
            assert c4["bundle_width_mm"] <= c3["bundle_width_mm"]
            for e4, e3 in zip(c4["elements"], c3["elements"]):
                assert {k: v for k, v in e4.items() if k not in strip} == {k: v for k, v in e3.items() if k != "along_mm"}


def test_split_sizes_as_reported(all_splits):
    """Paper section 3.4: train 5,000 contexts / 22,500 elements, val 500 / 2,242,
    test 500 / 2,242, benchmark 1,000 / 4,500 (125 per tier)."""
    totals = {s: sum(c["n_elements"] for c in d) for s, d in all_splits.items()}
    assert totals == {"train": 22500, "val": 2242, "test": 2242, "benchmark": 4500}
    assert Counter(c["tier"] for c in all_splits["benchmark"]) == {f"C{n}": 125 for n in range(1, 9)}
    assert Counter(c["tier"] for c in all_splits["train"]) == {f"C{n}": 625 for n in range(1, 9)}


def test_clearance_ordering_as_reported(benchmark_v40, benchmark_v3):
    """Paper section 5.1: median minimum pairwise clearance falls from 120 mm (C2)
    to 61 mm (C8).  In revision 4.0 these are physical clear gaps; in 3.0 the
    same values are envelope clearances (physical minus 50 mm)."""
    s4 = cm.tier_summary(benchmark_v40)
    s3 = cm.tier_summary(benchmark_v3, legacy_envelope=True)
    assert s4["C1"]["clear_gap_mm"] is None
    assert s4["C2"]["clear_gap_mm"] == pytest.approx(120.0, abs=0.5)
    assert s4["C8"]["clear_gap_mm"] == pytest.approx(61.7, abs=0.5)
    for n in range(2, 9):
        assert s4[f"C{n}"]["clear_gap_mm"] == pytest.approx(s3[f"C{n}"]["envelope_clearance_mm"], abs=1e-6)
    assert s4["C8"]["clear_gap_mm"] < s4["C5"]["clear_gap_mm"] < s4["C3"]["clear_gap_mm"] < s4["C2"]["clear_gap_mm"]
    loads = [s4[f"C{n}"]["load_kN"] for n in range(1, 9)]
    assert loads == sorted(loads)                              # monotone in the medians


def test_drip_rule_zero_violations(benchmark):
    from crossmep.model import ELECTRICAL_KINDS, WET_TRADES
    bad = 0
    for c in benchmark:
        sk = c["surface"]["kind"]
        pipes = [e for e in c["elements"] if e["kind"] == "pipe" and e["trade"] in WET_TRADES]
        elec = [e for e in c["elements"] if e["kind"] in ELECTRICAL_KINDS]
        for p in pipes:
            for t in elec:
                if sk == "ceiling":
                    ov = abs(p["along_mm"] - t["along_mm"]) < (cm._span(p, sk) + cm._span(t, sk)) / 2
                    bad += p["out_mm"] < t["out_mm"] and ov
                else:
                    oo = abs(p["out_mm"] - t["out_mm"]) < (cm._depth(p, sk) + cm._depth(t, sk)) / 2
                    bad += p["along_mm"] < t["along_mm"] and oo
    assert bad == 0


def test_benchmark_composition_pinned(benchmark_v40, benchmark_v3):
    """Composition of the RELEASED benchmark (same in both revisions).  NOTE: the
    paper's Figure 3a reports 2,668 pipes / 962 conduits / 576 trays / 294 ducts,
    computed on an internal v3.4 build with a different pipe library; the public
    files give the values below (README.md, 'Versions and relation to the paper')."""
    expect = {"pipe": 2529, "cable_tray": 569, "duct": 261, "conduit": 1141}
    assert cm.kind_totals(benchmark_v40) == cm.kind_totals(benchmark_v3) == expect


def test_catalog_coverage_pinned(benchmark_v40):
    cov = cm.catalog_coverage(benchmark_v40, [(48, 54, 2.5), (108, 114, 4.0)])
    assert cov["overall"] == 11.6 and cov["non_pipe_elements"] == 1971
    assert all(8.0 <= cov[f"C{n}"] <= 14.0 for n in range(1, 9))


def test_bundle_widths_pinned(benchmark_v40):
    s = cm.tier_summary(benchmark_v40)
    assert s["C1"]["bundle_width_mm"] == pytest.approx(102, abs=1)
    assert s["C8"]["bundle_width_mm"] == pytest.approx(1448, abs=1)
    r = cm.tier_ranges(benchmark_v40)
    assert r["C1"]["width_min"] == pytest.approx(21.3) and r["C1"]["width_max"] == pytest.approx(1000.0)


def test_distribution_drift_against_release(benchmark):
    """An unseen seed must stay within sampling noise of the released benchmark."""
    rel_gaps = [g for c in benchmark for g in cm.neighbour_gaps(c)]
    rel_share = cm.kind_totals(benchmark)["pipe"] / 4500
    d = [c.to_dict() for c in G.generate_dataset(1000, seed=777)]
    gaps = [g for c in d for g in cm.neighbour_gaps(c)]
    share = cm.kind_totals(d)["pipe"] / sum(c["n_elements"] for c in d)
    assert abs(np.median(gaps) - np.median(rel_gaps)) < 20
    assert abs(share - rel_share) < 0.04


# --------------------------------------------------------------------------- revision 4.1 (composition adjusted)

def test_revision_4_1_benchmark_pinned(benchmark):
    """The 4.1 benchmark: composition after the comparison with the open buildings
    (fewer stacked rows, fewer mixed bundles, duct pairs, DN bands to DN150)."""
    assert cm.kind_totals(benchmark) == {"pipe": 2488, "cable_tray": 559, "duct": 485, "conduit": 968}
    assert Counter(c["n_levels"] for c in benchmark) == {1: 807, 2: 180, 3: 13}
    s = cm.tier_summary(benchmark)
    assert s["C1"]["clear_gap_mm"] is None
    assert s["C2"]["clear_gap_mm"] == pytest.approx(130.3, abs=0.1) and s["C8"]["clear_gap_mm"] == pytest.approx(51.2, abs=0.1)
    assert s["C1"]["bundle_width_mm"] == pytest.approx(139.7, abs=0.1) and s["C8"]["bundle_width_mm"] == pytest.approx(2225.1, abs=0.1)
    assert s["C8"]["clear_gap_mm"] < s["C5"]["clear_gap_mm"] < s["C3"]["clear_gap_mm"] < s["C2"]["clear_gap_mm"]
    cov = cm.catalog_coverage(benchmark, [(48, 54, 2.5), (108, 114, 4.0)])
    assert cov["overall"] == 14.5 and cov["non_pipe_elements"] == 2012
    labels = Counter(e["label"] for c in benchmark for e in c["elements"] if e["kind"] == "pipe")
    assert labels["DN125"] > 0 and labels["DN150"] > 0
    assert max(e["load_kN"] for c in benchmark for e in c["elements"] if e["kind"] == "pipe") == pytest.approx(1.97)


def test_revision_4_1_keeps_4_0_library_and_layout(benchmark, benchmark_v40):
    """Same element library (every 4.0 element occurs unchanged in 4.1), same
    layout rules (gap floor and cap, drip rule tested elsewhere)."""
    def table(ctxs):
        out = {}
        for c in ctxs:
            for e in c["elements"]:
                key, val = (e["label"], e["service"]), (e["width_mm"], e["height_mm"], e["insulation_mm"], e["load_kN"], e["span_m"])
                assert out.setdefault(key, val) == val
        return out
    t40, t41 = table(benchmark_v40), table(benchmark)
    for key in set(t40) & set(t41):
        assert t40[key] == t41[key], key
    from crossmep.library import DN_OD_MM
    for (label, service), (w, h, ins, load, span) in t41.items():
        if label.startswith("DN"):
            assert w == h == DN_OD_MM[int(label[2:])]
