# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDocumentPullPurchaseRequest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({"name": "PR Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "PR Product", "purchase_ok": True, "type": "consu"}
        )

    def _make_request(self, qty=3.0):
        request = self.env["purchase.request"].create(
            {
                "requested_by": self.env.user.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": qty,
                            "product_uom_id": self.product.uom_id.id,
                        },
                    )
                ],
            }
        )
        request.button_approved()
        return request

    def _make_wizard(self, po, request):
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "purchase.order",
                "res_id": po.id,
                "source_ref": "purchase.request,%s" % request.id,
            }
        )
        wizard._onchange_source_ref()
        return wizard

    def test_source_specs_include_purchase_request(self):
        po = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        specs = po._od19_pull_source_specs()
        self.assertEqual([s["model"] for s in specs], ["purchase.request"])

    def test_pull_creates_order_line_and_allocation(self):
        request = self._make_request()
        po = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        wizard = self._make_wizard(po, request)
        self.assertEqual(len(wizard.line_ids), 1)
        wizard.action_pull()
        self.assertEqual(len(po.order_line), 1)
        self.assertEqual(po.order_line.product_id, self.product)
        self.assertAlmostEqual(po.order_line.product_qty, 3.0)
        self.assertEqual(po.order_line.purchase_request_lines, request.line_ids)

    def test_candidate_lines_exclude_already_pulled(self):
        request = self._make_request()
        po = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        self._make_wizard(po, request).action_pull()
        wizard2 = self._make_wizard(po, request)
        self.assertEqual(len(wizard2.line_ids), 0)

    def test_remove_frees_the_request_line(self):
        request = self._make_request()
        po = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        self._make_wizard(po, request).action_pull()
        self.assertTrue(request.line_ids.purchase_lines)
        po._od19_pull_remove(request)
        self.assertFalse(po.order_line)
        self.assertFalse(request.line_ids.purchase_lines)
