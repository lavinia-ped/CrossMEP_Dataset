"""Release file format: read and write CrossMEP JSON files.

A dataset file is a JSON object with exactly these keys, in this order::

    dataset      "CrossMEP"
    version      data revision ("4.0" current; "3.0" = the paper release)
    split        train | val | test | benchmark | custom | adhoc
    seed         integer seed of the generator stream
    n_contexts   number of contexts
    units        "mm, kN"
    contexts     list of context objects (schema/context-v<major>.schema.json)

Files live under ``data/v<revision>/mep_contexts_v<revision>_<split>.json`` and
are written with ``json.dumps(payload)`` -- compact, ASCII-escaped, default
separators, no trailing newline.  Regenerating a canonical split reproduces the
released file byte-for-byte; ``RELEASE_CHECKSUMS.txt`` lists the SHA-256 digests.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Iterable, List, Optional

from .model import CURRENT_REVISION, MEPContext, revision_for

DATASET_NAME = "CrossMEP"
DATA_VERSION = CURRENT_REVISION.version
DATA_VERSIONS = ("4.0", "3.0")
UNITS = "mm, kN"
RELEASE_SPLITS = ("train", "val", "test", "benchmark")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_dir(version: str = DATA_VERSION, root: str = ROOT) -> str:
    return os.path.join(root, "data", f"v{version}")


def split_path(split: str, root: str = ROOT, version: str = DATA_VERSION) -> str:
    return os.path.join(data_dir(version, root), f"mep_contexts_v{version}_{split}.json")


def release_files(root: str = ROOT) -> List[str]:
    """Every released data file, newest revision first (relative to ``root``)."""
    return [os.path.relpath(split_path(s, root, v), root)
            for v in DATA_VERSIONS for s in RELEASE_SPLITS]


def schema_path(version: str = DATA_VERSION, root: str = ROOT) -> str:
    major = version.split(".")[0]
    return os.path.join(root, "schema", f"context-v{major}.schema.json")


def build_payload(contexts: Iterable[MEPContext], *, split: str, seed: int,
                  version: Optional[str] = None) -> dict:
    ctxs = list(contexts)
    if version is None:
        version = ctxs[0].revision.version if ctxs else DATA_VERSION
    return {"dataset": DATASET_NAME, "version": version, "split": split,
            "seed": int(seed), "n_contexts": len(ctxs), "units": UNITS,
            "contexts": [c.to_dict() for c in ctxs]}


def dumps(payload: dict) -> str:
    """Serialise exactly as the released files were written (compact, ASCII-escaped)."""
    return json.dumps(payload)


def write_payload(payload: dict, path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(dumps(payload))
    return path


def read_payload(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if payload.get("dataset") != DATASET_NAME:
        raise ValueError(f"{path}: not a {DATASET_NAME} file")
    return payload


def contexts_from_payload(payload: dict) -> List[MEPContext]:
    rev = revision_for(payload["version"])
    return [MEPContext.from_dict(d, rev) for d in payload["contexts"]]


def load_contexts(split: str = "benchmark", root: str = ROOT,
                  version: str = DATA_VERSION) -> List[MEPContext]:
    """Load a released split as dataclasses (revision taken from the file)."""
    return contexts_from_payload(read_payload(split_path(split, root, version)))


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
