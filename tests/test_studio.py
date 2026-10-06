"""docs/studio/index.html shows real generator outputs: the embedded batches equal
fresh runs of the released generator, and every stored call reproduces them."""
import importlib.util
import os
import random

import pytest


@pytest.fixture(scope="module")
def bs(root):
    spec = importlib.util.spec_from_file_location("build_studio", os.path.join(root, "scripts", "build_studio.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def page(root):
    with open(os.path.join(root, "docs", "studio", "index.html"), encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def data(bs, page):
    return bs.decode(bs.extract_blob(page))


def test_page_is_built_and_small(page):
    assert "__DATA_GZ__" not in page and "<title>CrossMEP Generator Studio</title>" in page
    assert len(page.encode()) < 16_000_000


def test_grid_is_complete(bs, data):
    assert set(data["tiers"]) == {f"C{n}" for n in range(1, 9)}
    assert all(len(v) == len(bs.TIER_SEEDS) for v in data["tiers"].values())
    keys = {bs.custom_key(*c, s) for c in bs.compositions() for s in ("ceiling", "wall")}
    assert set(data["custom"]) == keys
    assert data["meta"]["tier_batch"] == bs.TIER_BATCH and data["meta"]["custom_batch"] == bs.CUSTOM_BATCH


@pytest.mark.parametrize("tier", ["C1", "C4", "C8"])
def test_tier_batches_equal_fresh_runs(bs, data, tier):
    for seed in (0, 7):
        assert data["tiers"][tier][str(seed)] == bs.tier_batch(tier, seed)
        assert all(c["tier"] == tier and c["n_elements"] == int(tier[1:]) for c in data["tiers"][tier][str(seed)])


def test_custom_batches_equal_fresh_runs(bs, data):
    rng = random.Random(0)
    combos = list(bs.compositions())
    for p, t, d, c in rng.sample(combos, 12):
        for surface in ("ceiling", "wall"):
            seed = rng.randrange(len(bs.CUSTOM_SEEDS))
            run = data["custom"][bs.custom_key(p, t, d, c, surface)][str(seed)]
            assert run == bs.custom_batch(p, t, d, c, surface, seed)
            counts = {"pipe": 0, "cable_tray": 0, "duct": 0, "conduit": 0}
            for e in run[0]["elements"]:
                counts[e["kind"]] += 1
            assert (counts["pipe"], counts["cable_tray"], counts["duct"], counts["conduit"]) == (p, t, d, c)
            assert all(x["surface"]["kind"] == surface for x in run)


def test_benchmark_medians(data):
    ref = data["benchmark_medians"]
    assert round(ref["C2"]["clear_gap_mm"]) == 130 and ref["C1"]["clear_gap_mm"] is None
    assert round(ref["C8"]["load_kN"], 2) == 2.04
