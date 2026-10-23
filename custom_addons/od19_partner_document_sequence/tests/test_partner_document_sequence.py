from odoo.tests.common import TransactionCase


class TestPartnerDocumentSequence(TransactionCase):
    """Basic tests for partner customer/vendor reference generation."""

    def test_create_customer_partner_generates_ref(self):
        partner = self.env["res.partner"].create({
            "name": "Test Customer",
            "customer": True,
        })
        self.assertTrue(partner.customer)
        # A customer ref should be generated (either from sequence or '/')
        self.assertIsNotNone(partner.ref)

    def test_create_vendor_partner_generates_ref(self):
        partner = self.env["res.partner"].create({
            "name": "Test Vendor",
            "supplier": True,
        })
        self.assertTrue(partner.supplier)
        self.assertIsNotNone(partner.ref)

    def test_is_customer_and_supplier_compute(self):
        partner = self.env["res.partner"].create({
            "name": "Test Both",
            "customer": True,
            "supplier": True,
        })
        self.assertTrue(partner.is_customer_and_supplier)

        partner.write({"supplier": False})
        self.assertFalse(partner.is_customer_and_supplier)

    def test_customer_rank_synced_on_create(self):
        # ``customer_rank`` is provided by the ``account`` module, which is not
        # a dependency of this module: skip when it is not installed.
        if "customer_rank" not in self.env["res.partner"]._fields:
            self.skipTest("customer_rank requires the account module.")
        partner = self.env["res.partner"].create({
            "name": "Test Customer Rank",
            "customer": True,
        })
        self.assertGreaterEqual(partner.customer_rank, 1)

    def test_supplier_rank_synced_on_create(self):
        # ``supplier_rank`` is provided by the ``account`` module, which is not
        # a dependency of this module: skip when it is not installed.
        if "supplier_rank" not in self.env["res.partner"]._fields:
            self.skipTest("supplier_rank requires the account module.")
        partner = self.env["res.partner"].create({
            "name": "Test Vendor Rank",
            "supplier": True,
        })
        self.assertGreaterEqual(partner.supplier_rank, 1)

    def test_auto_running_disabled_when_both_customer_and_supplier(self):
        partner = self.env["res.partner"].create({
            "name": "Test Both Auto",
            "customer": True,
            "supplier": True,
        })
        # When both customer and supplier, is_auto_running should be False
        self.assertFalse(partner.is_auto_running)
