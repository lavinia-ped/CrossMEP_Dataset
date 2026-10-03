import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import crossmep.tasks as cm  # noqa: E402


@pytest.fixture(scope="session")
def root() -> str:
    return ROOT


@pytest.fixture(scope="session")
def benchmark():
    return cm.load("benchmark")


@pytest.fixture(scope="session")
def all_splits():
    return {s: cm.load(s) for s in ("train", "val", "test", "benchmark")}
