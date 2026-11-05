"""Verify committed Office snapshots against analytical evidence using stdlib."""
import csv
import hashlib
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
OFFICE = ROOT / "examples/office"
SHEET_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
DRAW_NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


def main():
    manifest = json.loads((OFFICE / "office_manifest.json").read_text())
    summary = json.loads((ROOT / "examples/base/summary.json").read_text())
    assert manifest["run_id"] == summary["run_id"], "Stale Office run ID"
    for name, digest in manifest["files"].items():
        assert Path(name).name == name
        assert hashlib.sha256((OFFICE / name).read_bytes()).hexdigest() == digest, name
    with (ROOT / "examples/base/scenarios.csv").open() as stream:
        scenarios = list(csv.DictReader(stream))
    with ZipFile(OFFICE / "capital_review.xlsx") as archive:
        assert archive.testzip() is None
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        cells = {c.attrib["r"]: c for c in root.findall(".//m:c", SHEET_NS)}
        for i, row in enumerate(scenarios, 7):
            for column, key in [("G", "icap"), ("H", "headroom")]:
                cell = cells[f"{column}{i}"]
                assert cell.find("m:f", SHEET_NS) is not None, "Missing live formula"
                assert abs(float(cell.find("m:v", SHEET_NS).text) - float(row[key])) < 1e-7, key
        assert not root.findall(".//m:c[@t='e']", SHEET_NS), "Cached formula error"
    with ZipFile(OFFICE / "capital_committee.pptx") as archive:
        assert archive.testzip() is None
        slides = sorted(n for n in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n))
        assert len(slides) == 6
        for name in slides:
            root = ET.fromstring(archive.read(name))
            text = " ".join(x.text or "" for x in root.findall(".//a:t", DRAW_NS))
            assert summary["run_id"] in text, "Missing run lineage"
        for index in [2, 3, 5, 6]:
            root = ET.fromstring(archive.read(f"ppt/slides/slide{index}.xml"))
            assert root.find(".//a:tbl", DRAW_NS) is not None, "Missing native table"
    print("Office hashes, run lineage, live workbook formulas and native slide tables verified")


if __name__ == "__main__":
    main()
