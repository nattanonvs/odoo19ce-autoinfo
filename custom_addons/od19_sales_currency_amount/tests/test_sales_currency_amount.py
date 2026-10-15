from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSalesCurrencyAmount(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.company_currency = cls.company.currency_id
        cls.usd = cls.env.ref("base.USD")
        cls.eur = cls.env.ref("base.EUR")
        # Pick a currency that is always foreign for this company.
        cls.foreign_currency = (
            cls.eur if cls.company_currency != cls.eur else cls.usd
        )
        # 1 unit of company currency = 0.8 unit of the foreign currency.
        cls.env["res.currency.rate"].create(
            {
                "currency_id": cls.foreign_currency.id,
                "company_id": cls.company.id,
                "name": "2020-01-01",
                "rate": 0.8,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Currency Test Partner"}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Currency Test Product", "type": "consu", "list_price": 100.0}
        )
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "company_id": cls.company.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_uom_qty": 2,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )
        cls.order.currency_id = cls.foreign_currency
        cls.order._compute_currency_rate()
        cls.order._compute_amounts()
        cls.order._compute_amount_company()

    def test_company_currency_amounts_use_inverse_rate(self):
        """Company amounts must divide by currency_rate (order -> company)."""
        self.assertNotEqual(self.order.currency_id, self.company_currency)
        rate = self.order.currency_rate
        self.assertTrue(rate)
        self.assertAlmostEqual(
            self.order.amount_untaxed_curr,
            self.company_currency.round(self.order.amount_untaxed / rate),
            places=2,
        )
        self.assertAlmostEqual(
            self.order.amount_total_curr,
            self.company_currency.round(self.order.amount_total / rate),
            places=2,
        )

    def test_matches_standard_conversion(self):
        """Company amount must equal res.currency._convert on the order date."""
        self.assertAlmostEqual(
            self.order.amount_total_curr,
            self.order.currency_id._convert(
                self.order.amount_total,
                self.company_currency,
                self.company,
                self.order.date_order.date(),
            ),
            places=2,
        )

    def test_same_currency_keeps_amount(self):
        """When the order currency is the company currency, amounts are unchanged."""
        self.order.currency_id = self.company_currency
        self.order._compute_amount_company()
        self.assertAlmostEqual(
            self.order.amount_untaxed_curr, self.order.amount_untaxed, places=2
        )
        self.assertAlmostEqual(
            self.order.amount_total_curr, self.order.amount_total, places=2
        )
