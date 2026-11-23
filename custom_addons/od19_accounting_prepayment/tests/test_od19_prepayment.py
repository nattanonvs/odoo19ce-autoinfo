# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOd19PrepaymentField(TransactionCase):
    """Coverage for the Prepare Payment link added to ``account.payment``."""

    def test_prepayment_field_definition(self):
        field = self.env["account.payment"]._fields["od19_prepayment_id"]
        self.assertEqual(field.comodel_name, "account.billing")
        self.assertTrue(field.groups)

    def test_bill_type_follows_partner_type(self):
        payment = self.env["account.payment"].new({"partner_type": "supplier"})
        self.assertEqual(payment.od19_prepayment_bill_type, "in_invoice")
        payment.partner_type = "customer"
        self.assertEqual(payment.od19_prepayment_bill_type, "out_invoice")

    def test_register_payment_requires_prepayment(self):
        payment = self.env["account.payment"].new({"partner_type": "supplier"})
        with self.assertRaises(UserError):
            payment.action_od19_register_payment()
