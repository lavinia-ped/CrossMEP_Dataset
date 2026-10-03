"""Release file format: read and write CrossMEP JSON files.

A dataset file is a JSON object with exactly these keys, in this order::

    dataset      "CrossMEP"
    version      data revision ("3.0": the count-stratified v3 schema and element library)
    split        train | val | test | benchmark | custom | adhoc
    seed         integer seed of the generator stream
    n_contexts   number of contexts
    units        "mm, kN"
    contexts     list of context objects (schema/context-v3.schema.json)

Files are written with ``json.dumps(payload)`` -- compact, ASCII-escaped, default
separators, no trailing newline.  Regenerating a canonical split reproduces the
released file byte-for-byte; ``RELEASE_CHECKSUMS.txt`` lists the SHA-256 digests.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Iterable, List, Optional

from .model import MEPContext

DATASET_NAME = "CrossMEP"
DATA_VERSION = "3.0"
UNITS = "mm, kN"
RELEASE_SPLITS = ("train", "val", "test", "benchmark")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def split_path(split: str, root: str = ROOT, version: str = DATA_VERSION) -> str:
    return os.path.join(root, f"mep_contexts_v{version}_{split}.json")


def build_payload(contexts: Iterable[MEPContext], *, split: str, seed: int) -> dict:
    ctxs = [c.to_dict() for c in contexts]
    return {"dataset": DATASET_NAME, "version": DATA_VERSION, "split": split,
            "seed": int(seed), "n_contexts": len(ctxs), "units": UNITS, "contexts": ctxs}


def dumps(payload: dict) -> str:
    """Serialise exactly as the released files were written (compact, ASCII-escaped)."""
    return json.dumps(payload)


def write_payload(payload: dict, path: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(dumps(payload))
    return path


def read_payload(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if payload.get("dataset") != DATASET_NAME:
        raise ValueError(f"{path}: not a {DATASET_NAME} file")
    return payload


def load_contexts(split: str = "benchmark", root: str = ROOT,
                  version: str = DATA_VERSION) -> List[MEPContext]:
    """Load a released split as dataclasses."""
    return [MEPContext.from_dict(d) for d in read_payload(split_path(split, root, version))["contexts"]]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
