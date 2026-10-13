# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestSupplierQualityBlock(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.PO = cls.env["purchase.order"]
        cls.Partner = cls.env["res.partner"]

        cls.approved_supplier = cls.Partner.create(
            {"name": "Approved Supplier", "company_type": "company"}
        )
        cls.approved_supplier.od19_iso_supplier_status = "approved"

        cls.suspended_supplier = cls.Partner.create(
            {"name": "Suspended Supplier", "company_type": "company"}
        )
        cls.suspended_supplier.od19_iso_supplier_status = "suspended"

        cls.disqualified_supplier = cls.Partner.create(
            {"name": "Disqualified Supplier", "company_type": "company"}
        )
        cls.disqualified_supplier.od19_iso_supplier_status = "disqualified"

        cls.env.company.enable_supplier_quality_block = True

    def test_po_create_with_approved_supplier_ok(self):
        order = self.PO.create({"partner_id": self.approved_supplier.id})
        self.assertTrue(order.id)

    def test_po_create_with_suspended_supplier_blocked(self):
        with self.assertRaises(UserError):
            self.PO.create({"partner_id": self.suspended_supplier.id})

    def test_po_create_with_disqualified_supplier_blocked(self):
        with self.assertRaises(UserError):
            self.PO.create({"partner_id": self.disqualified_supplier.id})

    def test_po_write_to_suspended_supplier_blocked(self):
        order = self.PO.create({"partner_id": self.approved_supplier.id})
        with self.assertRaises(UserError):
            order.write({"partner_id": self.suspended_supplier.id})

    def test_po_override_allowed_with_reason(self):
        # As admin/system, override should work with a reason.
        order = self.PO.create(
            {
                "partner_id": self.suspended_supplier.id,
                "override_supplier_block": True,
                "override_supplier_block_reason": "Urgent procurement",
            }
        )
        self.assertTrue(order.id)

    def test_po_override_without_reason_blocked(self):
        with self.assertRaises(UserError):
            self.PO.create(
                {
                    "partner_id": self.suspended_supplier.id,
                    "override_supplier_block": True,
                }
            )

    def test_block_disabled_allows_po(self):
        self.env.company.enable_supplier_quality_block = False
        order = self.PO.create({"partner_id": self.suspended_supplier.id})
        self.assertTrue(order.id)
