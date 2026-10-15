# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestProductReturn(TransactionCase):
    """Tests for the product return (RMA) workflow."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Return = cls.env["od19.product.return"]
        cls.Wizard = cls.env["od19.product.return.reject.wizard"]
        cls.partner = cls.env["res.partner"].create({"name": "Returning Customer"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Returned Product",
                "type": "consu",
                "is_storable": True,
            }
        )
        # stock.picking.od19_department_code is required (defined by
        # od19_delivery_label) and auto-filled from the current user's department.
        cls.department = cls.env["hr.department"].create(
            {"name": "Return Dept", "code": "RMA"}
        )
        employees = cls.env["hr.employee"].search(
            [("user_id", "=", cls.env.user.id)]
        )
        if employees:
            employees.write({"department_id": cls.department.id})
        else:
            cls.env["hr.employee"].create(
                {
                    "name": "Return Test User",
                    "user_id": cls.env.user.id,
                    "department_id": cls.department.id,
                }
            )

    def _create_return(self, **overrides):
        vals = {
            "partner_id": self.partner.id,
            "product_id": self.product.id,
            "reason": "defective",
            "return_date": fields.Date.today(),
        }
        vals.update(overrides)
        return self.Return.create(vals)

    # ------------------------------------------------------------------
    # Creation / sequence
    # ------------------------------------------------------------------
    def test_name_auto_sequence(self):
        ret = self._create_return()
        self.assertTrue(ret.name)
        self.assertNotEqual(ret.name, "/")
        self.assertTrue(ret.name.startswith("PR-"))

    def test_defaults(self):
        ret = self._create_return()
        self.assertEqual(ret.state, "draft")
        self.assertEqual(ret.quantity, 1.0)
        self.assertEqual(ret.responsible_id, self.env.user)
        self.assertEqual(ret.uom_id, self.product.uom_id)

    def test_currency_follows_company(self):
        ret = self._create_return()
        self.assertEqual(ret.currency_id, ret.company_id.currency_id)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    def test_quantity_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self._create_return(quantity=0)

    def test_quantity_negative_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_return(quantity=-1)

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------
    def test_confirm_and_approve(self):
        ret = self._create_return()
        ret.action_confirm()
        self.assertEqual(ret.state, "confirmed")
        ret.action_approve()
        self.assertEqual(ret.state, "approved")

    def test_reject_wizard_sets_state_and_reason(self):
        ret = self._create_return()
        wizard = self.Wizard.create(
            {
                "return_id": ret.id,
                "rejection_reason": "Out of warranty period",
            }
        )
        wizard.action_reject()
        self.assertEqual(ret.state, "rejected")
        self.assertEqual(ret.rejection_reason, "Out of warranty period")

    # ------------------------------------------------------------------
    # action_return
    # ------------------------------------------------------------------
    def test_action_return_requires_approved_state(self):
        ret = self._create_return()
        self.assertIsNone(ret.action_return())
        self.assertFalse(ret.return_picking_id)

    def test_action_return_creates_picking(self):
        ret = self._create_return()
        ret.action_confirm()
        ret.action_approve()
        ret.action_return()
        self.assertEqual(ret.state, "returned")
        self.assertTrue(ret.return_picking_id)
        self.assertEqual(ret.return_picking_id.origin, ret.name)
        self.assertEqual(
            ret.return_picking_id.move_ids.product_id,
            self.product,
        )

    # ------------------------------------------------------------------
    # action_refund
    # ------------------------------------------------------------------
    def test_action_refund_requires_valid_state(self):
        ret = self._create_return()
        self.assertIsNone(ret.action_refund())
        self.assertFalse(ret.refund_move_id)

    def test_action_refund_creates_credit_note(self):
        ret = self._create_return(refund_amount=500.0)
        ret.action_confirm()
        ret.action_approve()
        ret.action_refund()
        self.assertEqual(ret.state, "refunded")
        self.assertTrue(ret.refund_move_id)
        self.assertEqual(ret.refund_move_id.move_type, "out_refund")
        self.assertEqual(ret.refund_move_id.partner_id, self.partner)
