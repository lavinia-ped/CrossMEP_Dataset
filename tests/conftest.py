import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import crossmep.tasks as cm  # noqa: E402

SPLITS = ("train", "val", "test", "benchmark")


@pytest.fixture(scope="session")
def root() -> str:
    return ROOT


@pytest.fixture(scope="session")
def benchmark():
    """Released benchmark split, current data revision (4.1)."""
    return cm.load("benchmark")


@pytest.fixture(scope="session")
def benchmark_v40():
    """Released benchmark split of revision 4.0 (the geometry of the paper's numbers)."""
    return cm.load("benchmark", "4.0")


@pytest.fixture(scope="session")
def benchmark_v3():
    """Released benchmark split of revision 3.0 (the paper release)."""
    return cm.load("benchmark", "3.0")


@pytest.fixture(scope="session")
def all_splits():
    return {s: cm.load(s) for s in SPLITS}


@pytest.fixture(scope="session")
def all_splits_v40():
    return {s: cm.load(s, "4.0") for s in SPLITS}


@pytest.fixture(scope="session")
def all_splits_v3():
    return {s: cm.load(s, "3.0") for s in SPLITS}
