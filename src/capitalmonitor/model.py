"""Decimal-based capital arithmetic. All monetary amounts are MXN millions.

The scenario book is hypothetical. Public disclosures anchor its scale, not
its exposures. No inference about the source institution's stress outcomes.
"""

from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation, localcontext

D = Decimal
ZERO = D(0)
ONE = D(1)
BP = D(10000)


def number(value: object) -> Decimal:
    """Reject float coercion, nonfinite values, booleans and missing data."""
    if isinstance(value, (float, bool)) or value is None:
        raise ValueError(f"Expected decimal string, got {type(value).__name__}")
    try:
        result = D(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Invalid decimal") from exc
    if not result.is_finite():
        raise ValueError("Nonfinite decimal")
    return result


@dataclass(frozen=True)
class Capital:
    equity: Decimal
    deductions: Decimal
    tier2: Decimal
    credit_rwa: Decimal
    market_rwa: Decimal
    operational_rwa: Decimal

    def __post_init__(self):
        for f in fields(self):
            value = number(getattr(self, f.name))
            object.__setattr__(self, f.name, value)
            if value < 0:
                raise ValueError(f"Negative baseline {f.name}")
        if self.deductions > self.equity or self.rwa <= 0:
            raise ValueError("Invalid eligible capital or zero RWA")

    @property
    def eligible(self):
        return self.equity - self.deductions + self.tier2

    @property
    def rwa(self):
        return self.credit_rwa + self.market_rwa + self.operational_rwa

    @property
    def ratio(self):
        return self.eligible / self.rwa


@dataclass(frozen=True)
class Book:
    fx_net_mxn: Decimal
    dv01_mxn_m_per_bp: Decimal
    credit_ead: Decimal
    lgd: Decimal
    foreign_credit_share: Decimal

    def __post_init__(self):
        for f in fields(self):
            object.__setattr__(self, f.name, number(getattr(self, f.name)))
        if self.credit_ead < 0:
            raise ValueError("Negative credit exposure")
        if not 0 <= self.lgd <= 1 or not 0 <= self.foreign_credit_share <= 1:
            raise ValueError("LGD and foreign credit share must be in [0,1]")


@dataclass(frozen=True)
class Scenario:
    name: str
    fx_change: Decimal = ZERO
    rate_bps: Decimal = ZERO
    default_fraction: Decimal = ZERO
    credit_migration: Decimal = ZERO
    market_multiplier: Decimal = ONE
    operational_multiplier: Decimal = ONE
    new_credit_rwa: Decimal = ZERO
    distribution: Decimal = ZERO

    def __post_init__(self):
        if not self.name or not self.name.replace("_", "").isalnum():
            raise ValueError("Scenario name must be alphanumeric/underscore")
        for f in fields(self):
            if f.name != "name":
                object.__setattr__(self, f.name, number(getattr(self, f.name)))
        if self.fx_change <= -1 or not 0 <= self.default_fraction <= 1:
            raise ValueError("Invalid FX move or default fraction")
        if self.credit_migration < 0:
            raise ValueError("Migration add-on cannot be negative")
        if min(self.market_multiplier, self.operational_multiplier) <= 0:
            raise ValueError("RWA multipliers must be positive")
        if min(self.new_credit_rwa, self.distribution) < 0:
            raise ValueError("Negative business RWA or distribution")


def stress(capital: Capital, book: Book, scenario: Scenario,
           target: Decimal = D("0.105")) -> dict:
    """One-period static-book scenario; no tax credit or management recovery.

    Credit defaults apply to a separate MXN loan proxy. Its RWA remains in
    the anchor (conservative frozen denominator); migration and FX translation
    apply to aggregate credit RWA. New business adds RWA without assumed profit.
    """
    target = number(target)
    if not 0 < target < 1:
        raise ValueError("Target ratio must be in (0,1)")
    with localcontext() as ctx:
        ctx.prec = 34
        fx_pnl = book.fx_net_mxn * scenario.fx_change
        rates_pnl = -book.dv01_mxn_m_per_bp * scenario.rate_bps
        credit_loss = book.credit_ead * book.lgd * scenario.default_fraction
        delta_capital = fx_pnl + rates_pnl - credit_loss - scenario.distribution
        eligible = capital.eligible + delta_capital
        credit_rwa = (capital.credit_rwa * (ONE + scenario.credit_migration)
                      * (ONE + book.foreign_credit_share * scenario.fx_change)
                      + scenario.new_credit_rwa)
        market_rwa = capital.market_rwa * scenario.market_multiplier
        operational_rwa = capital.operational_rwa * scenario.operational_multiplier
        rwa = credit_rwa + market_rwa + operational_rwa
        ratio = eligible / rwa
        headroom = eligible - target * rwa
        status = ("INSOLVENT_PROXY" if eligible < 0 else
                  "BELOW_MINIMUM" if ratio < D("0.08") else
                  "BELOW_TARGET" if headroom < 0 else "WITHIN_TARGET")
        return dict(scenario=scenario.name, fx_pnl=fx_pnl, rates_pnl=rates_pnl,
                    credit_loss=credit_loss, distribution=scenario.distribution,
                    eligible_capital=eligible, credit_rwa=credit_rwa,
                    market_rwa=market_rwa, operational_rwa=operational_rwa,
                    total_rwa=rwa, icap=ratio, target=target, headroom=headroom,
                    capital_shortfall=max(-headroom, ZERO),
                    rwa_reduction_alternative=max(rwa - max(eligible, ZERO) / target, ZERO),
                    capital_effect_bp=delta_capital / capital.rwa * BP,
                    rwa_effect_bp=eligible * (ONE / rwa - ONE / capital.rwa) * BP,
                    total_change_bp=(ratio - capital.ratio) * BP,
                    status=status)


def reverse_stress(capital: Capital, book: Book, target: Decimal,
                   upper: Decimal = D(5)) -> dict:
    """Find target crossing on a monotone adverse ray by bracketed bisection.

    Unit severity: 20% MXN depreciation, +200bp rates, 10% defaults,
    20% credit migration, 25% market RWA growth. Default fraction caps at 1.
    Only short/flat FX and nonnegative DV01 supported on this adverse ray.
    """
    upper, target = number(upper), number(target)
    if upper <= 0 or not 0 < target < 1:
        raise ValueError("Invalid reverse-stress bounds")
    if book.fx_net_mxn > 0 or book.dv01_mxn_m_per_bp < 0:
        raise ValueError("Reverse stress requires monotone adverse exposures")

    def evaluate(severity):
        scenario = Scenario("REVERSE", D(".20") * severity, D(200) * severity,
                            min(D(".10") * severity, ONE), D(".20") * severity,
                            ONE + D(".25") * severity)
        return stress(capital, book, scenario, target)

    start = evaluate(ZERO)
    if start["headroom"] <= 0:
        return dict(status="ALREADY_AT_OR_BELOW_TARGET", severity=ZERO,
                    lower=ZERO, upper=ZERO, headroom=start["headroom"])
    if evaluate(upper)["headroom"] > 0:
        return dict(status="NOT_BRACKETED", severity=None, lower=ZERO,
                    upper=upper, headroom=evaluate(upper)["headroom"])
    lo, hi = ZERO, upper
    for _ in range(100):
        mid = (lo + hi) / 2
        if evaluate(mid)["headroom"] > 0:
            lo = mid
        else:
            hi = mid
    return dict(status="BRACKETED", severity=hi, lower=lo, upper=hi,
                headroom=evaluate(hi)["headroom"])
