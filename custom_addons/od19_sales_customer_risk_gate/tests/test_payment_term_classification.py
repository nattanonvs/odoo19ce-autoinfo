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

    def _create_term(self, name, nb_days, delay_type):
        return self.env["account.payment.term"].create(
            {
                "name": name,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "value": "percent",
                            "value_amount": 100.0,
                            "nb_days": nb_days,
                            "delay_type": delay_type,
                        },
                    )
                ],
            }
        )

    def test_zero_day_term_is_non_credit(self):
        term = self._create_term("On Receipt", 0, "days_after")
        self.assertFalse(term.od19_is_credit_term)

    def test_end_of_month_term_is_credit(self):
        # No extra days but the due date is deferred to month end -> credit.
        term = self._create_term("End of Month", 0, "days_after_end_of_month")
        self.assertTrue(term.od19_is_credit_term)

    def test_end_of_next_month_term_is_credit(self):
        term = self._create_term("End of Next Month", 0, "days_after_end_of_next_month")
        self.assertTrue(term.od19_is_credit_term)
