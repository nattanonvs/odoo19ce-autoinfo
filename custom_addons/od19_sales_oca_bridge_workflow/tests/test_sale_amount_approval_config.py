# -*- coding: utf-8 -*-
import ast

from odoo import Command
from odoo.tests.common import TransactionCase

OD19_SALE_TIER_MANAGER = "Sale Order Approval (Sales Manager)"
OD19_SALE_TIER_DIRECTOR = "Sale Order Approval (Sales Director)"


class TestSaleAmountApprovalConfig(TransactionCase):
    """วงเงินอนุมัติ SO ตั้งค่าได้ที่บริษัท และผลักไปที่ tier definition ให้อัตโนมัติ"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.od19_so_manager_approval_threshold = 1000000.0
        cls.company.od19_so_director_approval_threshold = 10000000.0
        cls.customer = cls.env["res.partner"].create({"name": "Config Tier Customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "Config Tier Product", "type": "service", "list_price": 100.0}
        )

    def _create_order(self, amount):
        qty = max(1, int(amount // 100))
        price_unit = amount / qty if qty else amount
        return self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": qty,
                            "price_unit": price_unit,
                        }
                    )
                ],
            }
        )

    def _company_tiers(self):
        return self.env["tier.definition"].search(
            [
                ("model", "=", "sale.order"),
                ("company_id", "=", self.company.id),
                ("name", "in", [OD19_SALE_TIER_MANAGER, OD19_SALE_TIER_DIRECTOR]),
            ]
        )

    def _tier_domains(self):
        return {
            tier.name: ast.literal_eval(tier.definition_domain)
            for tier in self._company_tiers()
        }

    def test_thresholds_are_company_fields(self):
        self.assertIn(
            "od19_so_manager_approval_threshold", self.env["res.company"]._fields
        )
        self.assertIn(
            "od19_so_director_approval_threshold", self.env["res.company"]._fields
        )

    def test_tiers_are_company_scoped(self):
        self.assertEqual(len(self._company_tiers()), 2)
        self.assertFalse(
            self.env["tier.definition"].search(
                [
                    ("model", "=", "sale.order"),
                    ("company_id", "=", False),
                    ("name", "in", [OD19_SALE_TIER_MANAGER, OD19_SALE_TIER_DIRECTOR]),
                ]
            )
        )

    def test_default_domains_match_configured_thresholds(self):
        domains = self._tier_domains()
        self.assertEqual(
            domains[OD19_SALE_TIER_MANAGER],
            [("amount_total", ">=", 1000000.0), ("amount_total", "<", 10000000.0)],
        )
        self.assertEqual(
            domains[OD19_SALE_TIER_DIRECTOR],
            [("amount_total", ">=", 10000000.0)],
        )

    def test_changing_threshold_updates_tier_domain(self):
        self.company.od19_so_director_approval_threshold = 20000000.0
        domains = self._tier_domains()
        self.assertEqual(
            domains[OD19_SALE_TIER_MANAGER],
            [("amount_total", ">=", 1000000.0), ("amount_total", "<", 20000000.0)],
        )
        self.assertEqual(
            domains[OD19_SALE_TIER_DIRECTOR],
            [("amount_total", ">=", 20000000.0)],
        )

    def test_order_follows_updated_threshold(self):
        self.company.od19_so_manager_approval_threshold = 2000000.0
        self.company.od19_so_director_approval_threshold = 20000000.0

        below = self._create_order(1500000)
        self.assertFalse(below.need_validation)

        manager_band = self._create_order(6000000)
        self.assertTrue(manager_band.need_validation)

        director_band = self._create_order(25000000)
        self.assertTrue(director_band.need_validation)
