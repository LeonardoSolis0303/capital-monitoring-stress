"""Regenerate committed packs and require byte-for-byte equality."""

import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from capitalmonitor.reporting import run, verify


def main():
    with tempfile.TemporaryDirectory() as name:
        tmp = Path(name)
        data = tmp / "data"
        shutil.copytree(ROOT / "data", data)
        for pack in ["base", "blocked_update"]:
            if pack == "blocked_update":
                cfg = json.loads((data / "config.json").read_text())
                cfg["baseline_date"] = "2025-12-31"
                (data / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
            destination = tmp / pack
            run(data, destination)
            expected = ROOT / "examples" / pack
            verify(expected)
            actual_names = {p.name for p in destination.iterdir()}
            assert actual_names == {p.name for p in expected.iterdir()}, pack
            for p in destination.iterdir():
                assert p.read_bytes() == (expected / p.name).read_bytes(), f"{pack}/{p.name} drift"
    print("Both committed packs reproduce byte-for-byte")


if __name__ == "__main__":
    main()
