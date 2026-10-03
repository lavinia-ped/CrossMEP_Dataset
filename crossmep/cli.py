"""Command-line interface: ``python -m crossmep <command>``.

    generate   regenerate a canonical split, sample tiers, or build a custom composition
    validate   run the validator and schema check over a dataset file
    results    print the per-tier table, kind totals and catalog coverage (RESULTS.md)
    gallery    render the interactive HTML gallery for a dataset file
    checksums  print SHA-256 digests of the released files
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from . import __version__
from .io import (DATA_VERSION, RELEASE_SPLITS, ROOT, build_payload, read_payload, sha256_file,
                 split_path, write_payload)
from .model import MEPContext, validate_context

RELEASED_CLAMP_BINS = [(48.0, 54.0, 2.5), (108.0, 114.0, 4.0)]
"""The two-bin clamp catalog of the companion SSA code base used for the catalog
stress test (paper section 5.3): (lo_mm, hi_mm, capacity_kN)."""


def _env_line() -> str:
    import platform
    try:
        import numpy
        np_v = numpy.__version__
    except ImportError:                      # pragma: no cover
        np_v = "not installed"
    return f"crossmep {__version__} | data {DATA_VERSION} | python {platform.python_version()} | numpy {np_v}"


# --------------------------------------------------------------------------- #

def cmd_generate(a: argparse.Namespace) -> int:
    from .generate import CANONICAL_SPLITS, TIERS, generate_custom, generate_dataset, generate_split
    custom = any(v is not None for v in (a.pipes, a.trays, a.ducts, a.conduits))
    if a.split:
        if custom or a.tier or a.n is not None or a.seed is not None:
            raise SystemExit("--split regenerates a canonical file; do not combine with other options")
        ctxs = generate_split(a.split)
        split, seed = a.split, CANONICAL_SPLITS[a.split]["seed"]
    elif custom:
        seed = 0 if a.seed is None else a.seed
        ctxs = generate_custom(a.n or 100, pipes=a.pipes or 0, trays=a.trays or 0,
                               ducts=a.ducts or 0, conduits=a.conduits or 0,
                               surface=a.surface, seed=seed)
        split = "custom"
    else:
        if a.tier and a.tier not in TIERS:
            raise SystemExit(f"--tier must be one of {list(TIERS)}")
        seed = 0 if a.seed is None else a.seed
        ctxs = generate_dataset(a.n or 320, seed=seed, tier=a.tier)
        split = "adhoc"
    out = a.out or (f"mep_contexts_v{DATA_VERSION}_{split}.regenerated.json" if a.split
                    else f"mep_contexts_{split}.json")
    write_payload(build_payload(ctxs, split=split, seed=seed), out)
    print(f"wrote {len(ctxs)} contexts -> {out}  [{_env_line()}]", file=sys.stderr)
    if a.split:
        print(f"sha256 {sha256_file(out)}  {os.path.basename(out)}")
    if a.gallery:
        from .render import render_gallery_html
        render_gallery_html(ctxs, a.gallery)
        print(f"gallery -> {a.gallery}", file=sys.stderr)
    return 0


def cmd_validate(a: argparse.Namespace) -> int:
    paths = a.files or [split_path(s) for s in RELEASE_SPLITS]
    rc = 0
    for path in paths:
        payload = read_payload(path)
        n_bad = 0
        for d in payload["contexts"]:
            try:
                validate_context(MEPContext.from_dict(d))
            except ValueError as exc:
                n_bad += 1
                if n_bad <= 5:
                    print(f"  {exc}")
        schema_msg = ""
        try:
            import jsonschema
            with open(os.path.join(ROOT, "schema", "context-v3.schema.json")) as f:
                jsonschema.validate(payload, json.load(f))
            schema_msg = "schema OK"
        except ImportError:
            schema_msg = "schema not checked (pip install jsonschema)"
        except Exception as exc:                      # jsonschema.ValidationError
            schema_msg = f"SCHEMA ERROR: {str(exc).splitlines()[0]}"
            rc = 1
        print(f"{os.path.basename(path)}: {len(payload['contexts'])} contexts, "
              f"{n_bad} invalid; {schema_msg}")
        rc |= int(n_bad > 0)
    return rc


def cmd_results(a: argparse.Namespace) -> int:
    from . import tasks as cm
    data = read_payload(a.file)["contexts"] if a.file else cm.load(a.split)
    name = os.path.basename(a.file) if a.file else f"{a.split} split"
    lines: List[str] = [f"## {name} ({len(data)} contexts)", "",
                        "Per-tier medians (envelope clearance = paper section 5.1 definition; "
                        "clear gap = physical, insulation surface to surface):", "",
                        "```", cm.per_tier_table(data), "```", "",
                        "Per-tier ranges (layout of the paper's Table 1):", "",
                        "```", cm.tier_ranges_table(data), "```", ""]
    kt = cm.kind_totals(data)
    lines += ["Element kinds: " + ", ".join(f"{k} {v}" for k, v in kt.items()) + f" (total {sum(kt.values())})", ""]
    cov = cm.catalog_coverage(data, RELEASED_CLAMP_BINS)
    lines += ["Catalog coverage, released two-bin clamp catalog "
              f"{RELEASED_CLAMP_BINS}: " + ", ".join(f"{k} {v}" for k, v in cov.items()), ""]
    text = "\n".join(lines)
    print(text)
    return 0


def cmd_gallery(a: argparse.Namespace) -> int:
    from .render import render_gallery_html
    ctxs = [MEPContext.from_dict(d) for d in read_payload(a.file)["contexts"]]
    render_gallery_html(ctxs, a.out)
    print(f"gallery of {len(ctxs)} contexts -> {a.out}")
    return 0


def cmd_checksums(a: argparse.Namespace) -> int:
    for s in RELEASE_SPLITS:
        p = split_path(s)
        print(f"{sha256_file(p)}  {os.path.basename(p)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m crossmep", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=_env_line())
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="regenerate a canonical split, sample tiers, or build a custom composition")
    g.add_argument("--split", choices=list(RELEASE_SPLITS), help="regenerate this canonical split (byte-identical)")
    g.add_argument("--n", type=int, help="number of contexts (default 320 tiers / 100 custom)")
    g.add_argument("--seed", type=int, help="generator seed (default 0)")
    g.add_argument("--tier", help="fix a single tier C1..C8 (default: round-robin C1..C8)")
    g.add_argument("--pipes", type=int, help="custom mode: exact pipe count")
    g.add_argument("--trays", type=int, help="custom mode: exact tray count")
    g.add_argument("--ducts", type=int, help="custom mode: exact duct count")
    g.add_argument("--conduits", type=int, help="custom mode: exact conduit count")
    g.add_argument("--surface", choices=["ceiling", "wall"])
    g.add_argument("--out", help="output JSON path")
    g.add_argument("--gallery", help="also write an HTML gallery to this path")
    g.set_defaults(func=cmd_generate)

    v = sub.add_parser("validate", help="validator + JSON Schema over dataset files (default: the four released splits)")
    v.add_argument("files", nargs="*")
    v.set_defaults(func=cmd_validate)

    r = sub.add_parser("results", help="per-tier table, kind totals, catalog coverage")
    r.add_argument("--split", default="benchmark", choices=list(RELEASE_SPLITS))
    r.add_argument("--file", help="any dataset file instead of a released split")
    r.set_defaults(func=cmd_results)

    ga = sub.add_parser("gallery", help="render the interactive HTML gallery")
    ga.add_argument("file")
    ga.add_argument("--out", default="mep_contexts_gallery.html")
    ga.set_defaults(func=cmd_gallery)

    c = sub.add_parser("checksums", help="SHA-256 of the released files")
    c.set_defaults(func=cmd_checksums)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    a = build_parser().parse_args(argv)
    return a.func(a)


if __name__ == "__main__":                        # pragma: no cover
    sys.exit(main())
