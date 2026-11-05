"""Supply validated engine evidence to the optional Office artifact builder."""
import csv
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
from capitalmonitor.reporting import verify

verify(root / "examples/base")
data = {}
for name in ["scenarios", "reconciliations"]:
    with (root / "examples/base" / f"{name}.csv").open() as stream:
        data[name] = list(csv.DictReader(stream))
for name, path in {"summary": "examples/base/summary.json", "reverse": "examples/base/reverse_stress.json",
                   "source": "data/source.json", "config": "data/config.json"}.items():
    data[name] = json.loads((root / path).read_text())
print(json.dumps(data))
