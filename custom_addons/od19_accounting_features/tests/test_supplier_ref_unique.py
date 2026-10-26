# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from psycopg2.errors import UniqueViolation

from odoo.tests import tagged
from odoo.tools import mute_logger
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestSupplierRefUnique(AccountTestInvoicingCommon):
    """ห้ามเลขที่อ้างอิงใบกำกับซื้อ (ref) ซ้ำสำหรับคู่ค้าเดิมในบริษัทเดียวกัน."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor_b = cls.env["res.partner"].create({"name": "Other Vendor"})

    def _create_bill(self, partner, ref, move_type="in_invoice"):
        return self.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": partner.id,
                "ref": ref,
                "invoice_date": "2026-01-01",
            }
        )

    def test_duplicate_ref_same_partner_is_blocked(self):
        self._create_bill(self.partner_a, "SUP-INV-001")
        with mute_logger("odoo.sql_db"), self.assertRaises(UniqueViolation):
            self._create_bill(self.partner_a, "SUP-INV-001")
            self.env.flush_all()

    def test_duplicate_ref_other_contact_same_vendor_is_blocked(self):
        vendor = self.env["res.partner"].create(
            {"name": "Vendor Co", "is_company": True}
        )
        contact = self.env["res.partner"].create(
            {"name": "Vendor Co - Branch", "parent_id": vendor.id}
        )
        self._create_bill(vendor, "SUP-INV-777")
        with mute_logger("odoo.sql_db"), self.assertRaises(UniqueViolation):
            self._create_bill(contact, "SUP-INV-777")
            self.env.flush_all()

    def test_duplicate_ref_on_vendor_refund_is_blocked(self):
        self._create_bill(self.partner_a, "SUP-INV-900")
        with mute_logger("odoo.sql_db"), self.assertRaises(UniqueViolation):
            self._create_bill(self.partner_a, "SUP-INV-900", move_type="in_refund")
            self.env.flush_all()

    def test_same_ref_other_partner_is_allowed(self):
        self._create_bill(self.partner_a, "SUP-INV-002")
        # Must not raise: the guard is per vendor.
        self._create_bill(self.vendor_b, "SUP-INV-002")
        self.env.flush_all()

    def test_empty_ref_can_repeat(self):
        # Must not raise: draft bills without a reference are not guarded.
        self._create_bill(self.partner_a, False)
        self._create_bill(self.partner_a, False)
        self.env.flush_all()

    def test_duplicate_ref_on_write_is_blocked(self):
        self._create_bill(self.partner_a, "SUP-INV-003")
        other = self._create_bill(self.partner_a, "SUP-INV-004")
        with mute_logger("odoo.sql_db"), self.assertRaises(UniqueViolation):
            other.ref = "SUP-INV-003"
            self.env.flush_all()
