"""Strict inputs, disclosure reconciliation and explicit model assumptions."""

import csv
import json
from datetime import date
from pathlib import Path

from .model import Book, Capital, D, Scenario, number

DISCLOSURE_COLUMNS = ["as_of", "assets", "liabilities", "equity", "basic_capital",
                      "credit_rwa", "market_rwa", "operational_rwa", "total_rwa",
                      "reported_icap_pct"]
SCENARIO_COLUMNS = ["name", "fx_change", "rate_bps", "default_fraction",
                    "credit_migration", "market_multiplier", "operational_multiplier",
                    "new_credit_rwa", "distribution"]


def read_csv(path: Path, columns: list[str]) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != columns:
            raise ValueError(f"{path.name}: unexpected columns/order")
        rows = list(reader)
    if not rows or len(rows) > 10000:
        raise ValueError(f"{path.name}: empty/oversize input")
    for row in rows:
        if None in row or any(v is None or not v.strip() for v in row.values()):
            raise ValueError(f"{path.name}: missing/extra fields")
    return rows


def _unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_config(path: Path) -> dict:
    cfg = json.loads(path.read_text(), object_pairs_hook=_unique_json)
    expected = {"baseline_date", "target_ratio", "deductions", "tier2", "book", "assumptions"}
    if set(cfg) != expected or not isinstance(cfg["assumptions"], list) or not cfg["assumptions"]:
        raise ValueError("Incomplete or unknown configuration fields")
    date.fromisoformat(cfg["baseline_date"])
    for key in ["target_ratio", "deductions", "tier2"]:
        cfg[key] = number(cfg[key])
    if not 0 < cfg["target_ratio"] < 1 or min(cfg["deductions"], cfg["tier2"]) < 0:
        raise ValueError("Invalid target/deductions/tier2")
    cfg["book"] = Book(**cfg["book"])
    return cfg


def reconcile_disclosures(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    parsed, checks, seen = [], [], set()
    for raw in rows:
        stamp = date.fromisoformat(raw["as_of"]).isoformat()
        if stamp in seen:
            raise ValueError("Duplicate disclosure date")
        seen.add(stamp)
        row = {k: number(v) for k, v in raw.items() if k != "as_of"}
        if any(v < 0 for v in row.values()) or row["total_rwa"] <= 0:
            raise ValueError("Negative disclosure or zero RWA")
        row["as_of"] = stamp
        parsed.append(row)

        def add(control, observed, expected, tolerance, note):
            checks.append(dict(as_of=stamp, control=control, observed=observed,
                               expected=expected, difference=observed - expected,
                               tolerance=tolerance,
                               status="PASS" if abs(observed - expected) <= tolerance else "REVIEW",
                               note=note))

        add("BALANCE_SHEET", row["assets"] - row["liabilities"], row["equity"], D(1),
            "MXN millions; tolerance reflects whole-million presentation")
        add("RWA_COMPONENTS", row["credit_rwa"] + row["market_rwa"] + row["operational_rwa"],
            row["total_rwa"], D(1), "RWA table explicitly unaudited")
        add("BASIC_TO_EQUITY", row["basic_capital"], row["equity"], D(1),
            "Disclosure cross-check; not a regulatory capital eligibility test")
        add("RATIO_PROXY", row["basic_capital"] / row["total_rwa"] * 100,
            row["reported_icap_pct"], D(".055"),
            "Basic capital / RWA proxy versus reported ICAP; missing bridge may explain a difference")
    return parsed, checks


def load_inputs(directory: Path):
    rows, checks = reconcile_disclosures(read_csv(directory / "disclosures.csv", DISCLOSURE_COLUMNS))
    cfg = load_config(directory / "config.json")
    selected = [r for r in rows if r["as_of"] == cfg["baseline_date"]]
    if len(selected) != 1:
        raise ValueError("Configured baseline date absent from disclosures")
    baseline = selected[0]
    capital = Capital(baseline["equity"], cfg["deductions"], cfg["tier2"],
                      baseline["credit_rwa"], baseline["market_rwa"], baseline["operational_rwa"])
    scenarios = [Scenario(**r) for r in read_csv(directory / "scenarios.csv", SCENARIO_COLUMNS)]
    if len({s.name for s in scenarios}) != len(scenarios):
        raise ValueError("Duplicate scenario name")
    if not any(s == Scenario("BASELINE") for s in scenarios):
        raise ValueError("A zero-shock BASELINE scenario is required")
    blocked = any(c["status"] != "PASS" and c["as_of"] == cfg["baseline_date"] for c in checks)
    source = json.loads((directory / "source.json").read_text(), object_pairs_hook=_unique_json)
    if not source.get("url", "").startswith("https://") or not source.get("sha256"):
        raise ValueError("Missing source provenance")
    return capital, cfg, scenarios, checks, blocked, source
