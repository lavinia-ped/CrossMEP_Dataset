"""The released files: integrity, byte-exact regeneration, schema, and the
numbers reported in the CIB W78 2026 paper that reproduce from them."""
import hashlib
import json
import os
from collections import Counter

import numpy as np
import pytest

import crossmep.tasks as cm
from crossmep import generate as G
from crossmep import io
from crossmep.model import MEPContext, validate_context

SPLITS = ("train", "val", "test", "benchmark")


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
    for s in SPLITS:
        path = io.split_path(s, root)
        assert sums[os.path.basename(path)] == io.sha256_file(path)


@pytest.mark.parametrize("split", SPLITS)
def test_split_regenerates_byte_for_byte(split, root):
    spec = G.CANONICAL_SPLITS[split]
    text = io.dumps(io.build_payload(G.generate_split(split), split=split, seed=spec["seed"]))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == io.sha256_file(io.split_path(split, root))


def test_all_splits_match_schema(root, all_splits):
    jsonschema = pytest.importorskip("jsonschema")
    with open(os.path.join(root, "schema", "context-v3.schema.json")) as f:
        schema = json.load(f)
    for s in SPLITS:
        jsonschema.validate(io.read_payload(io.split_path(s, root)), schema)


def test_metadata_consistent(all_splits):
    for s, data in all_splits.items():
        payload = io.read_payload(io.split_path(s))
        spec = G.CANONICAL_SPLITS[s]
        assert payload["seed"] == spec["seed"] and payload["n_contexts"] == spec["n"] == len(data)
        assert payload["version"] == io.DATA_VERSION and payload["split"] == s
        for c in data:
            assert c["n_elements"] == len(c["elements"]) == int(c["tier"][1:])
            assert c["n_levels"] == len({e["level"] for e in c["elements"]})


def test_every_released_context_validates(all_splits):
    for data in all_splits.values():
        for d in data:
            validate_context(MEPContext.from_dict(d))


def test_split_sizes_as_reported(all_splits):
    """Paper section 3.4: train 5,000 contexts / 22,500 elements, val 500 / 2,242,
    test 500 / 2,242, benchmark 1,000 / 4,500 (125 per tier)."""
    totals = {s: sum(c["n_elements"] for c in d) for s, d in all_splits.items()}
    assert totals == {"train": 22500, "val": 2242, "test": 2242, "benchmark": 4500}
    assert Counter(c["tier"] for c in all_splits["benchmark"]) == {f"C{n}": 125 for n in range(1, 9)}
    assert Counter(c["tier"] for c in all_splits["train"]) == {f"C{n}": 625 for n in range(1, 9)}


def test_clearance_ordering_as_reported(benchmark):
    """Paper section 5.1: median minimum pairwise clearance falls from 120 mm (C2)
    to 61 mm (C8).  (Envelope definition; C1 has no pairs.)"""
    s = cm.tier_summary(benchmark)
    assert s["C1"]["envelope_clearance_mm"] is None
    assert s["C2"]["envelope_clearance_mm"] == pytest.approx(120.0, abs=0.5)
    assert s["C8"]["envelope_clearance_mm"] == pytest.approx(61.7, abs=0.5)
    assert s["C8"]["envelope_clearance_mm"] < s["C5"]["envelope_clearance_mm"] < s["C3"]["envelope_clearance_mm"] < s["C2"]["envelope_clearance_mm"]
    loads = [s[f"C{n}"]["load_kN"] for n in range(1, 9)]
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


def test_benchmark_composition_pinned(benchmark):
    """Composition of the RELEASED benchmark.  NOTE: the paper's Figure 3a reports
    2,668 pipes / 962 conduits / 576 trays / 294 ducts, which were computed on an
    internal v3.4 build with a different pipe library; the public v3.0 files give
    the values below (README.md, 'Known discrepancies')."""
    assert cm.kind_totals(benchmark) == {"pipe": 2529, "cable_tray": 569, "duct": 261, "conduit": 1141}


def test_catalog_coverage_pinned(benchmark):
    cov = cm.catalog_coverage(benchmark, [(48, 54, 2.5), (108, 114, 4.0)])
    assert cov["overall"] == 11.6 and cov["non_pipe_elements"] == 1971
    assert all(8.0 <= cov[f"C{n}"] <= 14.0 for n in range(1, 9))


def test_distribution_drift_against_release(benchmark):
    """An unseen seed must stay within sampling noise of the released benchmark."""
    rel_gaps = [g for c in benchmark for g in cm.neighbour_gaps(c, "envelope")]
    rel_share = cm.kind_totals(benchmark)["pipe"] / 4500
    d = [c.to_dict() for c in G.generate_dataset(1000, seed=777)]
    gaps = [g for c in d for g in cm.neighbour_gaps(c, "envelope")]
    share = cm.kind_totals(d)["pipe"] / sum(c["n_elements"] for c in d)
    assert abs(np.median(gaps) - np.median(rel_gaps)) < 20
    assert abs(share - rel_share) < 0.04
