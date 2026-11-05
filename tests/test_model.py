import unittest

from capitalmonitor.model import Book, Capital, D, Scenario, number, reverse_stress, stress


class CapitalModelTests(unittest.TestCase):
    def setUp(self):
        self.c = Capital(D(120), D(10), D(5), D(600), D(300), D(100))
        self.b = Book(D(-100), D(".1"), D(200), D(".5"), D(".4"))

    def test_capital_bridge(self):
        self.assertEqual(self.c.eligible, D(115))
        self.assertEqual(self.c.rwa, D(1000))
        self.assertEqual(self.c.ratio, D(".115"))

    def test_zero_shock(self):
        r = stress(self.c, self.b, Scenario("BASELINE"))
        self.assertEqual(r["eligible_capital"], D(115))
        self.assertEqual(r["headroom"], D(10))
        self.assertEqual(r["total_change_bp"], D(0))

    def test_fx_translation_and_signed_pnl(self):
        r = stress(self.c, self.b, Scenario("FX", fx_change=D(".2")))
        self.assertEqual(r["fx_pnl"], D(-20))
        self.assertEqual(r["credit_rwa"], D(648))
        self.assertEqual(r["total_rwa"], D(1048))

    def test_appreciation_reverses_fx_pnl(self):
        r = stress(self.c, self.b, Scenario("FX", fx_change=D("-.2")))
        self.assertEqual(r["fx_pnl"], D(20))
        self.assertEqual(r["credit_rwa"], D(552))

    def test_rate_units(self):
        r = stress(self.c, self.b, Scenario("RATES", rate_bps=D(200)))
        self.assertEqual(r["rates_pnl"], D(-20))
        self.assertEqual(r["total_rwa"], D(1000))

    def test_credit_loss_separate_from_capital_requirement(self):
        r = stress(self.c, self.b, Scenario("CREDIT", default_fraction=D(".1")))
        self.assertEqual(r["credit_loss"], D(10))
        self.assertEqual(r["eligible_capital"], D(105))
        self.assertEqual(r["credit_rwa"], D(600))

    def test_target_equality_not_breach(self):
        r = stress(self.c, self.b, Scenario("EQUAL", distribution=D(10)))
        self.assertEqual(r["status"], "WITHIN_TARGET")
        self.assertEqual(r["capital_shortfall"], 0)

    def test_minimum_equality_is_below_target(self):
        r = stress(self.c, self.b, Scenario("EQUAL", distribution=D(35)))
        self.assertEqual(r["icap"], D(".08"))
        self.assertEqual(r["status"], "BELOW_TARGET")

    def test_below_minimum(self):
        self.assertEqual(stress(self.c, self.b, Scenario("LOSS", distribution=D(36)))["status"], "BELOW_MINIMUM")

    def test_negative_capital_not_clipped(self):
        r = stress(self.c, self.b, Scenario("LOSS", distribution=D(120)))
        self.assertEqual(r["eligible_capital"], D(-5))
        self.assertLess(r["icap"], 0)
        self.assertEqual(r["status"], "INSOLVENT_PROXY")

    def test_exact_sequential_attribution(self):
        r = stress(self.c, self.b, Scenario("MIX", D(".2"), D(200), D(".1"), D(".2"), D("1.3")))
        self.assertLess(abs(r["capital_effect_bp"] + r["rwa_effect_bp"] - r["total_change_bp"]), D("1e-20"))

    def test_new_business_has_no_unearned_profit(self):
        r = stress(self.c, self.b, Scenario("GROWTH", new_credit_rwa=D(500)))
        self.assertEqual(r["eligible_capital"], self.c.eligible)
        self.assertEqual(r["total_rwa"], D(1500))

    def test_shortfall_and_rwa_alternative(self):
        r = stress(self.c, self.b, Scenario("LOSS", distribution=D(15)))
        self.assertEqual(r["capital_shortfall"], D(5))
        self.assertLess(abs((r["total_rwa"] - r["rwa_reduction_alternative"]) * D(".105") - D(100)), D("1e-20"))

    def test_operational_rwa_overlay(self):
        r = stress(self.c, self.b, Scenario("OP", operational_multiplier=D("1.5")))
        self.assertEqual(r["operational_rwa"], D(150))

    def test_reverse_bracket_matches_independent_quadratic(self):
        # For this book: capital=115-50*s; RWA=1000+243*s+9.6*s*s.
        # Target crossing solves 1.008*s^2+75.515*s-10=0.
        expected = (-D("75.515") + (D("75.515") ** 2 + 4 * D("1.008") * 10).sqrt()) / (2 * D("1.008"))
        r = reverse_stress(self.c, self.b, D(".105"))
        self.assertEqual(r["status"], "BRACKETED")
        self.assertLess(abs(r["severity"] - expected), D("1e-20"))
        self.assertLessEqual(r["headroom"], 0)
        self.assertLess(abs(r["headroom"]), D("1e-20"))

    def test_reverse_already_below_target(self):
        self.assertEqual(reverse_stress(self.c, self.b, D(".2"))["status"], "ALREADY_AT_OR_BELOW_TARGET")

    def test_reverse_not_bracketed(self):
        r = reverse_stress(self.c, self.b, D(".105"), D(".001"))
        self.assertEqual(r["status"], "NOT_BRACKETED")
        self.assertIsNone(r["severity"])

    def test_reverse_rejects_nonmonotone_configuration(self):
        b = Book(D(100), D(".1"), D(200), D(".5"), D(".4"))
        with self.assertRaises(ValueError):
            reverse_stress(self.c, b, D(".105"))

    def test_nonfinite_and_lossy_numbers_rejected(self):
        for bad in ["NaN", "Infinity", "-Infinity", "", 0.1, True, None]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                number(bad)

    def test_bad_capital_rejected(self):
        for vals in [(10, 11, 0, 10, 10, 10), (10, 0, 0, 0, 0, 0), (10, 0, 0, -1, 1, 1)]:
            with self.subTest(vals=vals), self.assertRaises(ValueError):
                Capital(*map(D, vals))

    def test_bad_scenario_domains_rejected(self):
        for kw in [dict(fx_change="-1"), dict(default_fraction="1.1"), dict(market_multiplier="0"),
                   dict(operational_multiplier="-1"), dict(credit_migration="-.1"), dict(distribution="-1"), dict(new_credit_rwa="-1")]:
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                Scenario("BAD", **kw)

    def test_bad_book_rejected(self):
        with self.assertRaises(ValueError):
            Book(D(0), D(0), D(1), D("1.01"), D(".5"))

    def test_invalid_target_rejected(self):
        for target in [D(0), D(1), D(-1)]:
            with self.assertRaises(ValueError):
                stress(self.c, self.b, Scenario("BASELINE"), target)


if __name__ == "__main__":
    unittest.main()
