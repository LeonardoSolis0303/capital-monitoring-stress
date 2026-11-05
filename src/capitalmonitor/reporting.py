"""Deterministic review pack with input/output integrity and no-clobber writes."""

import csv
import hashlib
import html
import json
import os
from pathlib import Path
import tempfile

from .inputs import load_inputs
from .model import D, Scenario, reverse_stress, stress


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def serialize(value):
    if isinstance(value, D):
        return format(value, "f")
    raise TypeError(type(value).__name__)


def json_file(path, data):
    path.write_text(json.dumps(data, default=serialize, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def csv_file(path, rows):
    if not rows:
        raise ValueError("Cannot write an empty report")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _table(rows, columns):
    def cell(value):
        return html.escape(format(value, ",.3f") if isinstance(value, D) else str(value))
    return ("<table><thead><tr>" + "".join(f"<th>{html.escape(label)}</th>" for _, label in columns)
            + "</tr></thead><tbody>" + "".join("<tr>" + "".join(
                f"<td>{cell(row[key])}</td>" for key, _ in columns) + "</tr>" for row in rows)
            + "</tbody></table>")


def dashboard(path, run_id, cfg, results, checks, reverse, source):
    assumptions = "".join(f"<li>{html.escape(a)}</li>" for a in cfg["assumptions"])
    display = [dict(r, icap_pct=r["icap"] * 100) for r in results]
    worst = min(results, key=lambda r: r["icap"]) if results else None
    base = next((r for r in results if r["scenario"] == "BASELINE"), None)
    cards = (f"<div class='card'>Baseline ICAP proxy<strong>{base['icap'] * 100:.2f}%</strong></div>"
             f"<div class='card'>Lowest scenario ICAP<strong>{worst['icap'] * 100:.2f}%</strong></div>"
             f"<div class='card'>Largest target shortfall<strong>{max(r['capital_shortfall'] for r in results):,.1f}</strong></div>"
             if results else "<div class='card'>BASELINE BLOCKED — reconcile source inputs before stress execution.</div>")
    table = _table(display, [("scenario", "Scenario"), ("eligible_capital", "Capital"),
                            ("total_rwa", "RWA"), ("icap_pct", "ICAP %"), ("headroom", "Headroom"),
                            ("status", "Monitoring status")]) if results else ""
    checktable = _table(checks, [("as_of", "As of"), ("control", "Control"),
                                 ("difference", "Difference"), ("tolerance", "Tolerance"), ("status", "Result")])
    attribution = _table(results, [("scenario", "Scenario"), ("capital_effect_bp", "Capital effect bp"),
                                   ("rwa_effect_bp", "RWA effect bp"), ("total_change_bp", "Total bp")]) if results else ""
    reverse_text = (f"Target crossing at severity {reverse['severity']:.6f} on the documented adverse ray."
                    if reverse and reverse["severity"] is not None else "No crossing result available.")
    content = f"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Capital review | {run_id}</title>
<style>body{{font:15px/1.55 system-ui,sans-serif;background:#f5f6f4;color:#17291f;margin:0}}
main{{max-width:1200px;margin:auto;padding:40px 30px}}h1{{font-size:36px;line-height:1.15}}
h2{{margin-top:36px}}.eyebrow{{letter-spacing:.13em;font-size:12px;text-transform:uppercase}}
.cards{{display:flex;gap:18px;flex-wrap:wrap}}.card{{background:#fff;padding:20px;flex:1;border-top:4px solid #1b4332}}
strong{{display:block;font-size:28px}}table{{border-collapse:collapse;width:100%;background:white}}
td,th{{padding:11px 12px;text-align:right;border-bottom:1px solid #dbe1dc;font-variant-numeric:tabular-nums}}
th:first-child,td:first-child{{text-align:left}}th{{background:#1b4332;color:white;font-size:12px}}
.table{{overflow-x:auto}}footer,.muted{{color:#5c6961;font-size:13px}}a{{color:#1b4332}}
@media print{{body{{background:white}}main{{padding:0}}table{{font-size:10px}}h2{{break-after:avoid}}tr{{break-inside:avoid}}}}
</style><main><div class="eyebrow">Finance / Capital monitoring / Independent analysis</div>
<h1>Capital resilience under stress</h1><p>Historical calibration: {cfg['baseline_date']} · MXN millions ·
Hypothetical portfolio · Run {run_id}</p><div class="cards">{cards}</div>
<h2>Scenario outcomes</h2><p>Monitoring target {cfg['target_ratio'] * 100:.1f}%. Negative headroom is a modeled target shortfall.</p>
<div class="table">{table}</div><h2>Capital ratio attribution</h2>
<p>Exact sequential bridge: capital change at original RWA, then denominator change at stressed capital.</p>
<div class="table">{attribution}</div><h2>Reverse stress</h2><p>{html.escape(reverse_text)}</p>
<h2>Disclosure reconciliation</h2><p>RATIO_PROXY compares basic capital / RWA with disclosed ICAP; it does not independently verify total eligible capital.</p>
<div class="table">{checktable}</div><h2>Model basis</h2><ul>{assumptions}</ul>
<footer>Public calibration source: <a href="{html.escape(source['url'], quote=True)}">issuer financial statements</a>.
Risk-weighted asset disclosures are explicitly unaudited. Independent project; no affiliation or regulatory submission.
Output integrity is recorded in manifest.json.</footer></main></html>"""
    path.write_text(content, encoding="utf-8")


def committee_note(path, run_id, cfg, results, checks, reverse):
    lines = ["# Capital monitoring — committee brief", "", f"Run `{run_id}` · Historical calibration {cfg['baseline_date']} · MXN millions", "",
             "Independent scenario analysis of a hypothetical portfolio; public disclosures establish the scale only.", "",
             "## Executive assessment", ""]
    if results:
        base = next(r for r in results if r["scenario"] == "BASELINE")
        worst = min(results, key=lambda r: r["icap"])
        breaches = [r for r in results if r["headroom"] < 0]
        lines.extend([f"The baseline capital ratio proxy is {base['icap'] * 100:.2f}%, with {base['headroom']:,.2f} of headroom above the {cfg['target_ratio'] * 100:.1f}% monitoring target.", "",
                      f"{len(breaches)} of {len(results)} scenarios fall below target. The lowest ratio is {worst['icap'] * 100:.2f}% in {worst['scenario']}, with a capital shortfall of {worst['capital_shortfall']:,.2f}.", "",
                      f"That scenario changes ICAP by {worst['total_change_bp']:.1f} bp: {worst['capital_effect_bp']:.1f} bp from capital and {worst['rwa_effect_bp']:.1f} bp from the denominator.", "",
                      "## Decision considerations", "",
                      "- Evaluate capital retention and incremental business RWA against stressed headroom before distributions.",
                      "- Capital injection and RWA reduction are separate arithmetic alternatives; feasibility, transaction costs and second-order P&L are outside this model.",
                      "- Reverse stress identifies a threshold on one specified adverse ray, not a probability or a forecast."])
    else:
        lines.extend(["Stress execution blocked: the selected disclosure baseline contains unresolved reconciliation exceptions."])
    lines += ["", "## Data and model review", "",
              f"{sum(c['status'] != 'PASS' for c in checks)} disclosure control(s) require review. See reconciliations.csv; no source value was silently amended.", ""]
    lines += ["- " + a for a in cfg["assumptions"]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(input_dir: Path, output_dir: Path) -> dict:
    input_dir, output_dir = input_dir.resolve(), output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError("Output already exists; use a new run directory")
    if input_dir == output_dir or input_dir in output_dir.parents:
        raise ValueError("Output must be outside input directory")
    capital, cfg, scenarios, checks, blocked, source = load_inputs(input_dir)
    input_hashes = {p.name: sha256(p) for p in sorted(input_dir.glob("*")) if p.is_file()}
    code_hashes = {p.name: sha256(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
    run_id = hashlib.sha256(json.dumps([input_hashes, code_hashes], sort_keys=True).encode()).hexdigest()[:16]
    results, reverse, grid = [], None, []
    if not blocked:
        results = [stress(capital, cfg["book"], s, cfg["target_ratio"]) for s in scenarios]
        reverse = reverse_stress(capital, cfg["book"], cfg["target_ratio"])
        for fx in [D("-.10"), D(0), D(".10"), D(".20"), D(".30")]:
            for rate in [D(-200), D(0), D(100), D(200), D(400)]:
                result = stress(capital, cfg["book"], Scenario("SENSITIVITY", fx, rate), cfg["target_ratio"])
                grid.append(dict(fx_change=fx, rate_bps=rate, icap=result["icap"], headroom=result["headroom"]))
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output_dir.parent, prefix=".capital-") as temporary:
        stage = Path(temporary) / "pack"
        stage.mkdir()
        csv_file(stage / "reconciliations.csv", checks)
        if results:
            csv_file(stage / "scenarios.csv", results)
            csv_file(stage / "sensitivity.csv", grid)
            json_file(stage / "reverse_stress.json", reverse)
            csv_file(stage / "capital_bridge.csv", [dict(component="Equity", amount=capital.equity),
                     dict(component="Regulatory deductions (assumed)", amount=-capital.deductions),
                     dict(component="Eligible Tier 2 (assumed)", amount=capital.tier2),
                     dict(component="Modeled eligible capital", amount=capital.eligible)])
        json_file(stage / "source.json", source)
        dashboard(stage / "report.html", run_id, cfg, results, checks, reverse, source)
        committee_note(stage / "committee_brief.md", run_id, cfg, results, checks, reverse)
        summary = dict(run_id=run_id, baseline_date=cfg["baseline_date"], baseline_blocked=blocked,
                       scenario_count=len(results), reconciliation_review_count=sum(c["status"] != "PASS" for c in checks),
                       target_breach_count=sum(r["headroom"] < 0 for r in results))
        json_file(stage / "summary.json", summary)
        manifest = dict(schema_version=1, run_id=run_id, inputs=input_hashes, code=code_hashes,
                        outputs={p.name: sha256(p) for p in sorted(stage.iterdir())})
        json_file(stage / "manifest.json", manifest)
        # mkdir is the no-clobber reservation. Rename each file only after all
        # content has been successfully generated; another process cannot win it.
        output_dir.mkdir()
        try:
            for p in stage.iterdir():
                os.replace(p, output_dir / p.name)
        except OSError:
            for p in output_dir.iterdir():
                p.unlink()
            output_dir.rmdir()
            raise
    return summary


def verify(output_dir: Path) -> None:
    manifest = json.loads((output_dir / "manifest.json").read_text())
    actual = {p.name for p in output_dir.iterdir() if p.is_file()} - {"manifest.json"}
    if actual != set(manifest["outputs"]):
        raise ValueError("Output inventory differs from manifest")
    for name, digest in manifest["outputs"].items():
        if Path(name).name != name or sha256(output_dir / name) != digest:
            raise ValueError(f"Output integrity failure: {name}")
