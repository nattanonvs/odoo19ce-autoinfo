from odoo.tests.common import TransactionCase


class TestPurchaseDocumentSequence(TransactionCase):
    """Basic tests for purchase document sequence fields."""

    def test_department_has_purchase_sequence_fields(self):
        department = self.env["hr.department"].create({
            "name": "Test Purchase Dept",
            "od19_dept_code": "T",
        })
        self.assertEqual(department.od19_dept_code, "T")
        self.assertFalse(department.pr_sequence_id)
        self.assertFalse(department.po_sequence_id)
        self.assertFalse(department.po_indent_sequence_id)

    def test_purchase_order_has_type_and_department(self):
        partner = self.env["res.partner"].create({"name": "Test Vendor"})
        order = self.env["purchase.order"].create({
            "partner_id": partner.id,
            "od19_purchase_type": "local",
        })
        self.assertEqual(order.od19_purchase_type, "local")

    def test_purchase_order_indent_type(self):
        partner = self.env["res.partner"].create({"name": "Test Indent Vendor"})
        order = self.env["purchase.order"].create({
            "partner_id": partner.id,
            "od19_purchase_type": "indent",
        })
        self.assertEqual(order.od19_purchase_type, "indent")

    def test_purchase_order_bulk_type(self):
        partner = self.env["res.partner"].create({"name": "Test Bulk Vendor"})
        order = self.env["purchase.order"].create({
            "partner_id": partner.id,
            "od19_purchase_type": "bulk",
        })
        self.assertEqual(order.od19_purchase_type, "bulk")

    def test_get_purchase_sequence_no_department(self):
        partner = self.env["res.partner"].create({"name": "Test No Dept Vendor"})
        order = self.env["purchase.order"].create({
            "partner_id": partner.id,
            "od19_purchase_type": "local",
        })
        # No department set, should return False
        self.assertFalse(order._get_purchase_sequence())
