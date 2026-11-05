# Engineering

## Package boundaries

`model.py` owns Decimal arithmetic, scenario effects, capital attribution and reverse stress. `inputs.py` owns schemas, numerical domains, disclosure reconciliation and configuration. `reporting.py` owns deterministic serialization and review packs. `cli.py` maps execution states to stable exit codes.

No network access occurs during analytical execution. The source PDF was manually reviewed once; the committed numeric observations and provenance record are the runtime inputs. There are no credentials, private issuer records or scraped personal data in this repository.

## Output lifecycle

Inputs are validated before report generation. Files are built in a temporary staging directory; the output directory is then reserved with a no-clobber `mkdir`. Files move only after generation succeeds. A concurrent reader must wait for `manifest.json` and verify the complete inventory before treating a directory as committed; directory visibility itself is not a transaction boundary. Failed moves are cleaned up. Input/output nesting and existing outputs are rejected.

Run IDs hash input-file and Python engine hashes. The manifest includes exact output hashes. Outputs omit execution timestamps and machine paths so the same source and engine reproduce the same evidence across supported Python versions. A change to any engine module changes the run ID even when financial calculations are unchanged.

## Office evidence

`scripts/build_office.mjs` creates the reference Excel and PowerPoint snapshots with `@oai/artifact-tool`; this optional artifact builder is separate from the dependency-free Python engine. The committed files can be reviewed without that authoring environment. The builder consumes the same output CSVs and manifest as the HTML/committee brief; it does not contain a second stress engine.

The workbook recomputes ICAP and headroom from imported capital/RWA values, making arithmetic editable and inspectable. Scenario positions and shocks are changed in the versioned engine inputs, then regenerated. The presentation includes native text/tables, source notes and the reference run ID. `office_manifest.json` ties both files to the analytical run and records their hashes; CI checks hashes and package structure, not desktop Office execution.

For reference replay use `scripts/verify_examples.py`. The two packs exercise a reconciled historical baseline and a blocked financial-data update. To reproduce a new run, use the CLI with a fresh output directory; no manual changes to generated evidence are needed.
