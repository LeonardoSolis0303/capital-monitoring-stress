import csv
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from capitalmonitor.cli import main
from capitalmonitor.inputs import DISCLOSURE_COLUMNS, load_inputs, read_csv, reconcile_disclosures
from capitalmonitor.reporting import run, verify

ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        shutil.copytree(ROOT / "data", self.data)

    def config(self, **updates):
        p = self.data / "config.json"
        cfg = json.loads(p.read_text())
        cfg.update(updates)
        p.write_text(json.dumps(cfg))

    def test_public_disclosures_seven_pass_one_review(self):
        _, _, _, checks, blocked, _ = load_inputs(self.data)
        self.assertFalse(blocked)
        failures = [(c["as_of"], c["control"]) for c in checks if c["status"] == "REVIEW"]
        self.assertEqual(failures, [("2025-12-31", "RATIO_PROXY")])

    def test_blocked_baseline_has_no_stress_outputs(self):
        self.config(baseline_date="2025-12-31")
        summary = run(self.data, self.root / "out")
        self.assertTrue(summary["baseline_blocked"])
        self.assertEqual(summary["scenario_count"], 0)
        self.assertFalse((self.root / "out/scenarios.csv").exists())
        verify(self.root / "out")

    def test_full_pipeline_expected_outcomes(self):
        result = run(self.data, self.root / "out")
        self.assertEqual(result["scenario_count"], 8)
        self.assertEqual(result["target_breach_count"], 2)
        with (self.root / "out/scenarios.csv").open() as stream:
            rows = {r["scenario"]: r for r in csv.DictReader(stream)}
        self.assertEqual(rows["BASELINE"]["eligible_capital"], "6024.00")
        self.assertEqual(rows["COMBINED_SEVERE"]["status"], "BELOW_MINIMUM")
        verify(self.root / "out")

    def test_reproducible_outputs(self):
        run(self.data, self.root / "a")
        run(self.data, self.root / "b")
        for path in (self.root / "a").iterdir():
            self.assertEqual(path.read_bytes(), (self.root / "b" / path.name).read_bytes(), path.name)

    def test_tampering_detected(self):
        run(self.data, self.root / "out")
        (self.root / "out/scenarios.csv").write_text("tampered")
        with self.assertRaises(ValueError):
            verify(self.root / "out")

    def test_untracked_output_detected(self):
        run(self.data, self.root / "out")
        (self.root / "out/extra.txt").write_text("unexpected")
        with self.assertRaises(ValueError):
            verify(self.root / "out")

    def test_existing_output_not_overwritten(self):
        (self.root / "out").mkdir()
        with self.assertRaises(FileExistsError):
            run(self.data, self.root / "out")

    def test_output_inside_inputs_rejected(self):
        with self.assertRaises(ValueError):
            run(self.data, self.data / "out")

    def test_unknown_baseline_rejected(self):
        self.config(baseline_date="2023-12-31")
        with self.assertRaises(ValueError):
            load_inputs(self.data)

    def test_duplicate_dates_rejected(self):
        p = self.data / "disclosures.csv"
        p.write_text(p.read_text() + p.read_text().splitlines()[1] + "\n")
        with self.assertRaises(ValueError):
            load_inputs(self.data)

    def test_missing_field_rejected(self):
        p = self.data / "disclosures.csv"
        p.write_text(p.read_text().replace(",37427,", ",,"))
        with self.assertRaises(ValueError):
            load_inputs(self.data)

    def test_unexpected_column_rejected(self):
        p = self.data / "disclosures.csv"
        p.write_text(p.read_text().replace("assets,", "assetz,", 1))
        with self.assertRaises(ValueError):
            load_inputs(self.data)

    def test_duplicate_scenario_rejected(self):
        p = self.data / "scenarios.csv"
        p.write_text(p.read_text() + p.read_text().splitlines()[1] + "\n")
        with self.assertRaises(ValueError):
            load_inputs(self.data)

    def test_nonzero_baseline_rejected(self):
        p = self.data / "scenarios.csv"
        p.write_text(p.read_text().replace("BASELINE,0,0,", "BASELINE,0,1,"))
        with self.assertRaises(ValueError):
            load_inputs(self.data)

    def test_duplicate_json_key_rejected(self):
        p = self.data / "config.json"
        p.write_text(p.read_text().replace('"tier2": "0",', '"tier2": "0", "tier2": "1",'))
        with self.assertRaises(ValueError):
            load_inputs(self.data)

    def test_rounding_tolerance_boundary(self):
        rows = read_csv(self.data / "disclosures.csv", DISCLOSURE_COLUMNS)
        rows[0]["assets"] = "37428"
        _, checks = reconcile_disclosures(rows)
        self.assertEqual(checks[0]["status"], "PASS")
        rows[0]["assets"] = "37428.01"
        _, checks = reconcile_disclosures(rows)
        self.assertEqual(checks[0]["status"], "REVIEW")

    def test_cli_invalid_input_exit(self):
        self.assertEqual(main(["run", "--input", str(self.root / "missing"), "--output", str(self.root / "out")]), 2)

    def test_cli_blocked_exit(self):
        self.config(baseline_date="2025-12-31")
        self.assertEqual(main(["run", "--input", str(self.data), "--output", str(self.root / "out")]), 1)

    def test_reordered_scenarios_keep_correct_baseline_headline(self):
        p = self.data / "scenarios.csv"
        lines = p.read_text().splitlines()
        p.write_text("\n".join([lines[0], *lines[2:], lines[1]]) + "\n")
        run(self.data, self.root / "out")
        self.assertIn("Baseline ICAP proxy<strong>15.12%", (self.root / "out/report.html").read_text())


if __name__ == "__main__":
    unittest.main()
