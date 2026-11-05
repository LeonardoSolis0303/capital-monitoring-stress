# Methodology

All monetary amounts use **MXN millions**. Ratios and shocks are decimals; rate shocks are basis points. The engine uses `Decimal`; CSVs retain unrounded calculations and presentation outputs round only for display.

## Capital and denominator

Modeled eligible capital is equity less configured deductions plus assumed eligible Tier 2. Baseline credit, market and operational RWA are separate inputs. ICAP proxy = modeled eligible capital / total RWA. This reconstructs a transparent analytical ratio, not a complete legal eligibility determination.

For a scenario, let x be the proportional USD/MXN change; a positive x is MXN depreciation. Let b be the interest-rate move in basis points, d the defaulted fraction, m the credit migration add-on, f the foreign-currency share of credit RWA, and g the new-business credit RWA.

```
FX P&L          = net FX exposure in MXN millions × x
Rates P&L       = −DV01 in MXN millions per bp × b
Credit loss     = credit EAD × LGD × d
Stressed capital = opening eligible capital + FX P&L + rates P&L
                   − credit loss − capital distribution

Credit RWA      = opening credit RWA × (1 + m) × (1 + f × x) + g
Market RWA      = opening market RWA × scenario market multiplier
Operational RWA = opening operational RWA × scenario operational multiplier
```

The credit-default proxy is a separate MXN exposure pool. It is not the FX trading position or the rates book; no double credit loss is applied to either. Defaulted exposures remain in the starting aggregate RWA, with no assumed default-related RWA relief. This is a conservative denominator convention, not a claim about regulatory treatment after default. FX translation and migration interact multiplicatively. Operational RWA is an explicit overlay rather than a regulatory income-based recomputation.

The planning horizon is one year, implemented as instantaneous shocks to a static book. There is no intervening coupon accrual, income forecast, tax credit or recovery of future earnings. Linear DV01 is appropriate only as a first-order approximation; the severe rate shock is a sensitivity exercise with material convexity/model risk.

## Monitoring

Headroom = stressed capital − target × stressed RWA. Capital shortfall = max(−headroom, 0).

For nonnegative capital, the alternative RWA reduction is max(stressed RWA − capital / target, 0). It assumes unchanged capital and is not simultaneous with the capital-injection alternative. With negative capital, the displayed reduction is the entire denominator: RWA reduction alone cannot restore solvency, and the status remains `INSOLVENT_PROXY`.

Monitoring labels distinguish negative capital, ICAP below 8%, ICAP below the configured target and ICAP at/above target. Exact equality is not a breach. The 10.5% target is a model monitoring setting; total capital alone cannot establish compliance with fundamental/basic capital composition requirements or a supervisory early-warning category.

## Exact sequential ICAP bridge

Let C0,R0 denote baseline capital/RWA and C1,R1 the stressed values.

```
Capital effect (bp) = (C1 − C0) / R0 × 10,000
RWA effect (bp)     = C1 × (1/R1 − 1/R0) × 10,000
Total change (bp)   = (C1/R1 − C0/R0) × 10,000
```

The components add to the total without a residual. Ordering is explicit: apply capital first, then denominator. Reversing the sequence would redistribute interaction effects.

## Reverse stress

Severity s applies: FX depreciation 20% × s; rate increase 200bp × s; default fraction min(10% × s, 100%); credit migration 20% × s; market RWA multiplier 1 + 25% × s. Operational RWA is unchanged. Capital distributions and new-business RWA are excluded from this ray.

The engine requires short/flat net FX and nonnegative DV01 for this routine. On this adverse ray, capital is nonincreasing and RWA is increasing, so target headroom is monotone decreasing. Bisection returns a bracketed crossing over [0,5]; already-breached and unbracketed states are explicit. The crossing is scenario severity, **not default probability, VaR, expected shortfall or a forecast**.

## Sensitivity surface

The 25-point grid varies FX moves from −10% to +30% and rate moves from −200bp to +400bp, retaining all other shocks at baseline. It isolates two-factor sensitivity rather than mixing it with credit migration/default assumptions.
