from odoo.tests import TransactionCase, new_test_user


class CreditGateCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.term_immediate = cls.env.ref("account.account_payment_term_immediate")
        cls.term_30 = cls.env.ref("account.account_payment_term_30days")
        cls.sales_user = new_test_user(
            cls.env,
            login="od19_gate_sales",
            groups="sales_team.group_sale_salesman,base.group_partner_manager",
        )
        cls.reviewer = new_test_user(
            cls.env,
            login="od19_gate_reviewer",
            groups="sales_team.group_sale_salesman,"
            "od19_sales_customer_risk_gate.group_od19_credit_reviewer",
        )
        cls.customer = cls.env["res.partner"].create(
            {
                "name": "Gate Customer",
                "company_type": "company",
                "email": "gate.customer@example.com",
                "od19_is_commercial_customer": True,
            }
        )
        cls.contact = cls.env["res.partner"].create(
            {
                "name": "Gate Contact",
                "parent_id": cls.customer.id,
                "email": "gate.contact@example.com",
                "od19_is_commercial_customer": True,
            }
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Gate Service", "type": "service", "list_price": 100.0}
        )

    def _quotation_vals(self, partner=None, term=None):
        return {
            "partner_id": (partner or self.customer).id,
            "payment_term_id": term.id if term else False,
            "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 1})],
        }
