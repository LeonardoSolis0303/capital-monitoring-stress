# Scope and regulatory mapping

| Finance responsibility | Implemented evidence | Boundary |
| --- | --- | --- |
| Capital index calculation and monitoring | Capital bridge, category RWA, ICAP proxy, target headroom | Capital eligibility is assumed; no full CNBV schedules |
| Financial information updates | Two disclosed reporting dates and gated baseline selection | Historical annual observations, not a live monthly feed |
| Market sensitivity and new business | FX/rates grid, RWA growth, capital distribution | Hypothetical exposures and multiplier overlays |
| Annual stress scenario exercise | Eight defined scenarios and reverse stress | Static-book one-year planning sensitivity, no earnings projection |
| Finance KPIs | Capital, RWA, ICAP, headroom, shortfall, attribution | Analytical labels, not formal supervisory categories |
| Risk committee and capital meeting materials | HTML, Excel, PowerPoint, committee brief | Independent sample materials; never submitted to a regulator |

This is a financial analytics and controls implementation. It does not produce a CNBV/Banxico filing, implement every capital deduction, derive standardized market-risk charges from positions, validate fundamental/basic capital buffers, model CVA/netting/margin, or measure the source institution's actual risk profile.

No regulatory approval, institutional affiliation, production deployment or review by the source institution is implied. The model is useful precisely because its source facts, assumptions, calculations and unresolved controls are inspectable.

The principal model risks are linear rate P&L, assumed rather than observed portfolio sensitivities, multiplier-based RWA, frozen defaulted-exposure RWA, omission of earnings/taxes/management actions and uncertainty in the public capital bridge. Extending the model requires granular positions, dated eligibility schedules, validated sensitivities and formal policy ownership.
