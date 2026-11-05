# Data contract and source provenance

## Public calibration

Source: [Morgan Stanley México, Casa de Bolsa — 2025 and 2024 financial statements](https://www.morganstanley.com/content/dam/msdotcom/global-offices/pdf/latin-america/Morgan-Stanley-Casa-de-Bolsa-EEFF-dictamen-Diciembre-2025.pdf), auditor's report dated 25 March 2026. The file's retrieval date and SHA-256 are in [source.json](../data/source.json). The PDF is referenced rather than redistributed.

| Fields | Source location | Treatment |
| --- | --- | --- |
| Assets, liabilities, equity | Printed p. 5 / PDF p. 7 | Transcribed, MXN millions |
| Basic capital, RWA categories/total, reported ICAP | Note 19, printed p. 40 / PDF p. 42 | Transcribed; RWA table marked unaudited |
| Total, basic and fundamental minimum ratios | Printed p. 9 / PDF p. 11 | Context only: 8%, 6%, 4.5% |

The source table labels its aggregate “Total requerimiento de capital,” although its components are risk-weighted assets/exposures. The model maps the 39,836 / 35,923 aggregates to the ratio denominator and does not interpret them as an 8% capital charge. This mapping is explicit and reproducible from the surrounding disclosure.

## Reconciliation interpretation

- Balance sheet: assets − liabilities versus equity; tolerance 1 million.
- RWA: category sum versus stated total; tolerance 1 million.
- Basic capital: versus stated equity; tolerance 1 million. This is a source cross-check, not a universal identity.
- Ratio proxy: basic capital / stated RWA × 100 versus reported percentage; tolerance **0.055 percentage points (5.5bp)**. This permits 0.05 percentage-point displayed-ratio rounding plus a small allowance for whole-million inputs at the example's scale. It is not a universal materiality policy.

2024: 6,024 / 39,836 = 15.122001…%, compared with reported 15.1%: within tolerance.

2025: 6,183 / 35,923 = 17.211812…%, compared with reported 17.1%: outside tolerance. The numerator is disclosed **basic capital**, whereas reported ICAP refers to net eligible capital. The project therefore raises `RATIO_PROXY` for review rather than asserting the financial statements contain an error. A verified regulatory capital bridge would be required to resolve it.

The reference model deliberately uses the reconciled historical calibration, not the latest available date. Its zero deductions and zero Tier 2 are explicit hypothetical assumptions; even a passing proxy check does not verify regulatory eligibility.

## Files

`disclosures.csv` has one row per date and the exact ordered header documented in `inputs.py`. Dates must be ISO dates; amounts must be finite, nonnegative decimal strings; total RWA must be positive. Duplicate dates, missing/extra fields and unexpected headers fail.

`config.json` selects one existing date, target ratio, deductions, Tier 2 and a hypothetical book. Unknown root fields, duplicate JSON keys, invalid numeric domains or absent assumptions fail. The bundled reverse-stress routine requires short/flat FX and nonnegative DV01.

`scenarios.csv` contains uniquely named scenarios and explicit numerical shocks. A zero-shock `BASELINE` record is mandatory. Default fraction and LGD lie in [0,1]; FX must exceed −100%; RWA multipliers are positive. Source data, exposures, assumptions and outputs are never combined into a single editable table.

## Regulatory reference

[CNBV's June 2026 broker-dealer ICAP release](https://www.gob.mx/cnbv/prensa/indice-de-capitalizacion-de-casas-de-bolsa-al-cierre-de-junio-de-2026?idiom=es-MX) describes an 8% minimum plus a 2.5% conservation supplement constituted with fundamental capital. This motivates the example's 10.5% monitoring target, but the implementation does not test fundamental/basic composition or assign a supervisory category. Regulatory interpretation and production reporting require the effective rules and institution-specific capital schedules.
