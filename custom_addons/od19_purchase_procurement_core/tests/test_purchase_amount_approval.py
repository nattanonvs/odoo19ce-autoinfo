# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestPurchaseAmountApproval(TransactionCase):
    """PO approval is routed by amount: manager below threshold, director at/above."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create(
            {"name": "Approval Vendor", "company_type": "company"}
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Approval Product",
                "purchase_ok": True,
                "type": "consu",
            }
        )
        cls.company = cls.env.company
        cls.company.od19_po_director_approval_threshold = 100000.0
        base_user_group = cls.env.ref("base.group_user")
        purchase_user_group = cls.env.ref("purchase.group_purchase_user")
        purchase_manager_group = cls.env.ref("purchase.group_purchase_manager")
        purchase_director_group = cls.env.ref(
            "od19_purchase_procurement_core.group_purchase_director"
        )
        Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.purchase_user = Users.create(
            {
                "name": "Purchase User",
                "login": "purchase.user.amount@example.com",
                "email": "purchase.user.amount@example.com",
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "group_ids": [(6, 0, [base_user_group.id, purchase_user_group.id])],
            }
        )
        cls.purchase_manager = Users.create(
            {
                "name": "Purchase Manager",
                "login": "purchase.manager.amount@example.com",
                "email": "purchase.manager.amount@example.com",
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
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
        cls.purchase_director = Users.create(
            {
                "name": "Purchase Director",
                "login": "purchase.director.amount@example.com",
                "email": "purchase.director.amount@example.com",
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            base_user_group.id,
                            purchase_user_group.id,
                            purchase_manager_group.id,
                            purchase_director_group.id,
                        ],
                    )
                ],
            }
        )

    def _create_order(self, amount):
        order = self.env["purchase.order"].create(
            {"partner_id": self.vendor.id}
        )
        self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": self.product.display_name,
                "product_id": self.product.id,
                "product_qty": 1.0,
                "price_unit": amount,
                "date_planned": "2026-10-06 00:00:00",
                "product_uom_id": self.product.uom_id.id,
            }
        )
        return order

    def test_low_amount_requires_manager_level(self):
        order = self._create_order(50000.0)
        self.assertEqual(order.od19_approval_level, "manager")

    def test_high_amount_requires_director_level(self):
        order = self._create_order(150000.0)
        self.assertEqual(order.od19_approval_level, "director")

    def test_manager_can_approve_low_amount(self):
        order = self._create_order(50000.0)
        order.action_od19_submit_for_approval()
        order.with_user(self.purchase_manager).action_od19_approve()
        self.assertEqual(order.od19_approval_state, "approved")

    def test_manager_cannot_approve_high_amount(self):
        order = self._create_order(150000.0)
        order.action_od19_submit_for_approval()
        with self.assertRaises(AccessError):
            order.with_user(self.purchase_manager).action_od19_approve()

    def test_director_can_approve_high_amount(self):
        order = self._create_order(150000.0)
        order.action_od19_submit_for_approval()
        order.with_user(self.purchase_director).action_od19_approve()
        self.assertEqual(order.od19_approval_state, "approved")

    def test_user_cannot_approve_low_amount(self):
        order = self._create_order(50000.0)
        order.action_od19_submit_for_approval()
        with self.assertRaises(AccessError):
            order.with_user(self.purchase_user).action_od19_approve()

    def test_threshold_is_company_configurable(self):
        self.company.od19_po_director_approval_threshold = 50000.0
        order = self._create_order(50000.0)
        self.assertEqual(order.od19_approval_level, "director")
