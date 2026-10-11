from odoo.tests import tagged

from .common import CreditGateCommon


@tagged("post_install", "-at_install")
class TestPaymentTermClassification(CreditGateCommon):
    def test_immediate_term_is_non_credit(self):
        self.assertFalse(self.term_immediate.od19_is_credit_term)

    def test_thirty_days_term_is_credit(self):
        self.assertTrue(self.term_30.od19_is_credit_term)

    def test_accounting_can_override_classification(self):
        self.term_30.od19_is_credit_term = False
        self.assertFalse(self.term_30.od19_is_credit_term)
