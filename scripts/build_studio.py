#!/usr/bin/env python3
"""Build the CrossMEP Generator Studio: docs/studio/index.html.

The studio shows what the generator produces for a given set of parameters.  It
does not re-implement the generator in JavaScript: every section on the page is
an output of the released Python generator (current data revision), embedded as
gzip + base64 JSON, together with the call that reproduces it.

    python scripts/build_studio.py              # writes docs/studio/index.html
    python scripts/build_studio.py --fragment F # also writes the page body only (for hosting as an artifact)

Parameter grid
--------------
* By tier: tiers C1-C8 x seeds 0-9, each a batch of ``generate_dataset(12, seed, tier)``.
* By composition: pipes 0-6, trays 0-2, ducts 0-2, conduits 0-6 (1 to 8 elements in
  total) x surface ceiling | wall x seeds 0-2, each a batch of
  ``generate_custom(4, pipes=..., trays=..., ducts=..., conduits=..., surface=..., seed=...)``.

``tests/test_studio.py`` decodes the embedded data and checks it against fresh
generator runs.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import itertools
import json
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import crossmep.tasks as cm  # noqa: E402
from crossmep import __version__  # noqa: E402
from crossmep.generate import TIERS, generate_custom, generate_dataset  # noqa: E402
from crossmep.io import DATA_VERSION  # noqa: E402
from crossmep.layout import GAP_CAP_MM, GAP_FLOOR_MM, GAP_LOGNORMAL_MU, GAP_LOGNORMAL_SIGMA  # noqa: E402

TEMPLATE = os.path.join(ROOT, "docs", "studio", "studio.template.html")
OUT = os.path.join(ROOT, "docs", "studio", "index.html")
TIER_SEEDS = range(10)
TIER_BATCH = 12
CUSTOM_SEEDS = range(3)
CUSTOM_BATCH = 4
MAX = {"pipes": 6, "trays": 2, "ducts": 2, "conduits": 6}
MAX_TOTAL = 8


def _strip(ctx: dict) -> dict:
    return {k: v for k, v in ctx.items() if k != "context_id"}


def tier_batch(tier: str, seed: int) -> list:
    return [_strip(c.to_dict()) for c in generate_dataset(TIER_BATCH, seed=seed, tier=tier)]


def custom_key(p: int, t: int, d: int, c: int, surface: str) -> str:
    return f"p{p}t{t}d{d}c{c}|{surface}"


def custom_batch(p: int, t: int, d: int, c: int, surface: str, seed: int) -> list:
    return [_strip(x.to_dict()) for x in generate_custom(CUSTOM_BATCH, pipes=p, trays=t, ducts=d, conduits=c,
                                                          surface=surface, seed=seed)]


def compositions():
    for p, t, d, c in itertools.product(range(MAX["pipes"] + 1), range(MAX["trays"] + 1),
                                        range(MAX["ducts"] + 1), range(MAX["conduits"] + 1)):
        if 1 <= p + t + d + c <= MAX_TOTAL:
            yield p, t, d, c


def build_data() -> dict:
    bench = cm.load("benchmark")
    ref = {}
    for t in TIERS:
        cs = [c for c in bench if c["tier"] == t]
        gaps = [g for g in (cm.min_clear_gap(c) for c in cs) if g is not None]
        ref[t] = {"load_kN": statistics.median(c["total_load_kN"] for c in cs),
                  "clear_gap_mm": statistics.median(gaps) if gaps else None,
                  "bundle_width_mm": statistics.median(c["bundle_width_mm"] for c in cs)}
    return {
        "meta": {"package": __version__, "data_revision": DATA_VERSION, "tier_batch": TIER_BATCH,
                 "custom_batch": CUSTOM_BATCH, "tier_seeds": len(TIER_SEEDS), "custom_seeds": len(CUSTOM_SEEDS),
                 "max": MAX, "max_total": MAX_TOTAL,
                 "gap": {"mu": GAP_LOGNORMAL_MU, "sigma": GAP_LOGNORMAL_SIGMA, "floor_mm": GAP_FLOOR_MM, "cap_mm": GAP_CAP_MM}},
        "benchmark_medians": ref,
        "tiers": {t: {str(s): tier_batch(t, s) for s in TIER_SEEDS} for t in TIERS},
        "custom": {custom_key(p, t, d, c, surf): {str(s): custom_batch(p, t, d, c, surf, s) for s in CUSTOM_SEEDS}
                   for p, t, d, c in compositions() for surf in ("ceiling", "wall")},
    }


def encode(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0)).decode()


def decode(blob: str) -> dict:
    return json.loads(gzip.decompress(base64.b64decode(blob)))


def extract_blob(html: str) -> str:
    start = html.index('const DATA_GZ = "') + len('const DATA_GZ = "')
    return html[start:html.index('"', start)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fragment", help="also write the page without the document wrapper (artifact hosting)")
    a = ap.parse_args(argv)
    with open(TEMPLATE, encoding="utf-8") as f:
        template = f.read()
    blob = encode(build_data())
    fragment = template.replace("__DATA_GZ__", blob)
    page = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">\n"
            "</head>\n<body>\n" + fragment + "\n</body>\n</html>\n")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    if a.fragment:
        with open(a.fragment, "w", encoding="utf-8") as f:
            f.write(fragment)
    print(f"wrote {os.path.relpath(OUT, ROOT)} ({len(page) / 1e6:.2f} MB; data {len(blob) / 1e6:.2f} MB base64)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
