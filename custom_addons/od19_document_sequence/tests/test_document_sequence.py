# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase


class TestDocumentSequence(TransactionCase):
    """Basic tests for the Thai document sequence extension."""

    def test_interpolation_dict_has_thai_month_keys(self):
        sequence = self.env["ir.sequence"]
        res = sequence._interpolation_dict()
        for key in (
            "month_th",
            "month_th_short",
            "range_month_th",
            "range_month_th_short",
            "current_month_th",
            "current_month_th_short",
        ):
            self.assertIn(key, res, f"Missing Thai month interpolation key: {key}")

    def test_thai_month_name_for_current_month(self):
        sequence = self.env["ir.sequence"]
        res = sequence._interpolation_dict()
        # The current month should produce a non-empty Thai month name
        self.assertTrue(res["month_th"], "Thai full month name should not be empty")
        self.assertTrue(res["month_th_short"], "Thai short month name should not be empty")
