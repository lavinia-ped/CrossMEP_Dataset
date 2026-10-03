"""CLI and backward-compatible shims."""
import json
import os
import subprocess
import sys

import pytest

from crossmep import io


def _run(args, cwd):
    return subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True)


def test_generate_split_cli_is_byte_identical(root, tmp_path):
    out = tmp_path / "val.json"
    r = _run(["-m", "crossmep", "generate", "--split", "val", "--out", str(out)], root)
    assert r.returncode == 0, r.stderr
    assert io.sha256_file(str(out)) == io.sha256_file(io.split_path("val", root))
    assert io.sha256_file(str(out)) in r.stdout


def test_generate_adhoc_and_custom_validate_against_schema(root, tmp_path):
    jsonschema = pytest.importorskip("jsonschema")
    with open(os.path.join(root, "schema", "context-v3.schema.json")) as f:
        schema = json.load(f)
    a = tmp_path / "a.json"
    assert _run(["-m", "crossmep", "generate", "--n", "16", "--seed", "3", "--out", str(a)], root).returncode == 0
    c = tmp_path / "c.json"
    assert _run(["-m", "crossmep", "generate", "--n", "5", "--pipes", "2", "--trays", "1",
                 "--surface", "wall", "--out", str(c), "--gallery", str(tmp_path / "g.html")], root).returncode == 0
    for p, split in ((a, "adhoc"), (c, "custom")):
        payload = io.read_payload(str(p))
        jsonschema.validate(payload, schema)
        assert payload["split"] == split and payload["n_contexts"] == len(payload["contexts"])
    assert (tmp_path / "g.html").stat().st_size > 1000
    assert _run(["-m", "crossmep", "validate", str(a), str(c)], root).returncode == 0


def test_results_and_checksums(root):
    r = _run(["-m", "crossmep", "results"], root)
    assert r.returncode == 0 and "C8" in r.stdout and "overall 11.6" in r.stdout
    r = _run(["-m", "crossmep", "checksums"], root)
    assert r.returncode == 0 and len(r.stdout.splitlines()) == 4


def test_validate_released(root):
    r = _run(["-m", "crossmep", "validate"], root)
    assert r.returncode == 0 and "0 invalid" in r.stdout


def test_legacy_shims(root, tmp_path):
    import crossmep_tasks as old
    import mep_context_sampler as M
    assert old.load("benchmark")[0]["tier"] == "C1"
    assert M.DN_LOAD_KN[50] == 0.21 and M.DUCT_LOAD_KN[800] == 0.58 and M.TRAY_WIDTHS == [150, 225, 300, 450, 600]
    for c in M.generate_custom(5, pipes=2, seed=1):
        M.validate_context(c)
    out = tmp_path / "legacy.json"
    r = _run(["mep_context_sampler.py", "--n", "8", "--seed", "1", "--json", str(out),
              "--gallery", str(tmp_path / "legacy.html")], root)
    assert r.returncode == 0, r.stderr
    assert io.read_payload(str(out))["n_contexts"] == 8
