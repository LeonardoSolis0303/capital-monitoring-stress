# Validation evidence

The suite contains 42 analytical and pipeline tests. It checks business invariants and failure behavior rather than merely asserting that the engine runs.

## Independent analytical benchmarks

- Capital bridge and zero-shock preservation.
- Signed FX P&L, foreign credit-RWA translation and rate-shock unit conversion.
- EAD × LGD × defaulted fraction, without treating capital requirements as P&L losses.
- Exact equality at target/minimum thresholds; negative capital remains visible.
- New business adds RWA without creating assumed profit.
- Exact sequential capital/denominator attribution.
- Reverse stress compared with an independently derived quadratic root for a small analytical book, plus already-breached, unbracketed and nonmonotone configurations.

## Controls and reproducibility

Source reconciliation produces seven PASS results and one REVIEW. Selecting the unresolved 2025 date blocks scenario outputs. Duplicate dates/scenarios/JSON keys, missing fields, unknown headers, nonfinite numbers, invalid domains and a nonzero baseline scenario fail explicitly. Boundary tests exercise the reconciliation tolerance and reordered scenario presentation.

Committed examples regenerate byte-for-byte. The integrity verifier detects modified and unexpected files. Existing output directories are never overwritten. CI installs the package and runs the suite, example replay and Office package evidence checks on Python 3.11, 3.12 and 3.13.

The Office workbook is a review snapshot with live ratio/headroom formulas; the Python engine is authoritative for regenerating stress outcomes. The PowerPoint is a generated snapshot. Export validation and rendered previews do not establish execution in desktop Excel or PowerPoint; native desktop applications were not available in the build environment.

SHA-256 records provide reproducibility and accidental-corruption checks, not digital signatures or protection against an adversary who can replace both files and manifests.
