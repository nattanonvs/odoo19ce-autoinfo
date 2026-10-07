from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase


class TestProcurementApproval(TransactionCase):
    def setUp(self):
        super().setUp()
        self.vendor = self.env["res.partner"].create(
            {"name": "Approved Vendor", "company_type": "company"}
        )
        self.other_vendor = self.env["res.partner"].create(
            {"name": "Other Approved Vendor", "company_type": "company"}
        )
        self.product = self.env["product.product"].create(
            {
                "name": "Approval Product",
                "purchase_ok": True,
                "type": "consu",
            }
        )
        self.company = self.env.company
        purchase_user_group = self.env.ref("purchase.group_purchase_user")
        purchase_manager_group = self.env.ref("purchase.group_purchase_manager")
        base_user_group = self.env.ref("base.group_user")
        Users = self.env["res.users"].with_context(no_reset_password=True)
        self.purchase_user = Users.create(
            {
                "name": "Purchase User",
                "login": "purchase.user.approval@example.com",
                "email": "purchase.user.approval@example.com",
                "company_id": self.company.id,
                "company_ids": [(6, 0, [self.company.id])],
                "group_ids": [(6, 0, [base_user_group.id, purchase_user_group.id])],
            }
        )
        self.purchase_manager = Users.create(
            {
                "name": "Purchase Manager",
                "login": "purchase.manager.approval@example.com",
                "email": "purchase.manager.approval@example.com",
                "company_id": self.company.id,
                "company_ids": [(6, 0, [self.company.id])],
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            base_user_group.id,
                            purchase_user_group.id,
                            purchase_manager_group.id,
                        ],
                    )
                ],
            }
        )

    def _create_order(self):
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
            }
        )
        self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": self.product.display_name,
                "product_id": self.product.id,
                "product_qty": 1,
                "price_unit": 100,
                "date_planned": "2026-10-06 00:00:00",
                "product_uom_id": self.product.uom_id.id,
            }
        )
        return order

    def _create_confirmed_order(self):
        order = self._create_order()
        order.action_od19_submit_for_approval()
        order.with_user(self.purchase_manager).action_od19_approve()
        order.button_confirm()
        self.assertEqual(order.state, "purchase")
        return order

    def _create_requisition(self):
        return self.env["purchase.requisition"].create(
            {
                "vendor_id": self.vendor.id,
                "requisition_type": "blanket_order",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 2,
                            "product_uom_id": self.product.uom_id.id,
                            "price_unit": 50,
                        },
                    )
                ],
            }
        )

    def test_direct_po_requires_explicit_approval_before_confirm(self):
        order = self._create_order()
        with self.assertRaises(UserError):
            order.button_confirm()
        order.action_od19_submit_for_approval()
        order.with_user(self.purchase_manager).action_od19_approve()
        order.button_confirm()
        self.assertEqual(order.od19_approval_state, "approved")

    def test_requisition_requires_explicit_approval_before_confirm(self):
        requisition = self._create_requisition()
        with self.assertRaises(UserError):
            requisition.action_confirm()
        requisition.action_od19_submit_for_approval()
        requisition.with_user(self.purchase_manager).action_od19_approve()
        requisition.action_confirm()
        self.assertEqual(requisition.od19_approval_state, "approved")

    def test_po_material_changes_invalidate_approval(self):
        order = self._create_order()
        order.action_od19_submit_for_approval()
        order.with_user(self.purchase_manager).action_od19_approve()
        self.assertEqual(order.od19_approval_state, "approved")
        order.write({"partner_id": self.other_vendor.id})
        self.assertEqual(order.od19_approval_state, "draft")
        order.action_od19_submit_for_approval()
        order.with_user(self.purchase_manager).action_od19_approve()
        order.order_line.write({"price_unit": 120})
        self.assertEqual(order.od19_approval_state, "draft")

    def test_requisition_material_changes_invalidate_approval(self):
        requisition = self._create_requisition()
        requisition.action_od19_submit_for_approval()
        requisition.with_user(self.purchase_manager).action_od19_approve()
        self.assertEqual(requisition.od19_approval_state, "approved")
        requisition.write({"vendor_id": self.other_vendor.id})
        self.assertEqual(requisition.od19_approval_state, "draft")
        requisition.action_od19_submit_for_approval()
        requisition.with_user(self.purchase_manager).action_od19_approve()
        requisition.line_ids.write({"price_unit": 75})
        self.assertEqual(requisition.od19_approval_state, "draft")

    def test_unauthorized_user_cannot_approve(self):
        order = self._create_order()
        order.action_od19_submit_for_approval()
        with self.assertRaises(AccessError):
            order.with_user(self.purchase_user).action_od19_approve()
        requisition = self._create_requisition()
        requisition.action_od19_submit_for_approval()
        with self.assertRaises(AccessError):
            requisition.with_user(self.purchase_user).action_od19_approve()

    def test_direct_write_of_approval_state_is_rejected(self):
        order = self._create_order()
        with self.assertRaises(UserError):
            order.write({"od19_approval_state": "approved"})
        requisition = self._create_requisition()
        with self.assertRaises(UserError):
            requisition.write({"od19_approval_state": "approved"})

    def test_custom_approval_still_respects_native_double_validation(self):
        order = self._create_order()
        company = order.company_id
        original_validation = company.po_double_validation
        original_threshold = company.po_double_validation_amount
        company.po_double_validation = "two_step"
        company.po_double_validation_amount = 0
        try:
            order.action_od19_submit_for_approval()
            order.with_user(self.purchase_manager).action_od19_approve()
            order.with_user(self.purchase_user).button_confirm()
            self.assertEqual(order.state, "to approve")
            self.assertEqual(order.od19_approval_state, "approved")
            order.with_user(self.purchase_manager).button_approve()
            self.assertEqual(order.state, "purchase")
        finally:
            company.po_double_validation = original_validation
            company.po_double_validation_amount = original_threshold

    def test_unlock_confirmed_order_blocks_material_header_edit(self):
        order = self._create_confirmed_order()
        order.button_unlock()
        self.assertFalse(order.locked)
        with self.assertRaises(UserError):
            order.write({"partner_id": self.other_vendor.id})

    def test_unlock_confirmed_order_blocks_line_write_create_and_unlink(self):
        order = self._create_confirmed_order()
        order.button_unlock()
        line = order.order_line[:1]
        with self.assertRaises(UserError):
            line.write({"price_unit": 140})
        with self.assertRaises(UserError):
            self.env["purchase.order.line"].create(
                {
                    "order_id": order.id,
                    "name": self.product.display_name,
                    "product_id": self.product.id,
                    "product_qty": 1,
                    "price_unit": 80,
                    "date_planned": "2026-10-06 00:00:00",
                    "product_uom_id": self.product.uom_id.id,
                }
            )
        with self.assertRaises(UserError):
            line.unlink()
