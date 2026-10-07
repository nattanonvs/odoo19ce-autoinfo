from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAccountingARClosure(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create(
            {
                "name": "AR Closure Customer",
                "company_type": "company",
                "is_company": True,
                "email": "ar@example.com",
                "od19_is_commercial_customer": True,
            }
        )
        cls.owner = cls.env["res.partner"].create(
            {
                "name": "AR Closure Owner",
                "company_type": "company",
                "is_company": True,
                "od19_is_project_owner": True,
            }
        )
        cls.project = cls.env["od19.sales.project"].create(
            {
                "name": "AR Closure Project",
                "project_owner_id": cls.owner.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "AR Closure Product",
                "type": "consu",
                "sale_ok": True,
                "list_price": 100.0,
            }
        )
        cls.evidence_type = cls.env["od19.billing.evidence.type"].create(
            {
                "name": "Signed Delivery",
                "trigger_kind": "delivery",
                "required_for_billing": True,
            }
        )

    def _create_ready_sale_order(self):
        sale_order_model = self.env["sale.order"].sudo()
        sale_order_line_model = self.env["sale.order.line"].sudo()
        billing_evidence_model = self.env["od19.billing.evidence"].sudo()
        order = sale_order_model.create(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": self.project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )
        sale_order_line_model.create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": 1.0,
                "product_uom_id": self.product.uom_id.id,
                "price_unit": 100.0,
            }
        )
        billing_evidence_model.create(
            {
                "name": "DEL-001",
                "sale_order_id": order.id,
                "evidence_type_id": self.evidence_type.id,
                "is_verified": True,
            }
        )
        order.action_confirm()
        order.invalidate_recordset(
            ["od19_billing_readiness_state", "od19_invoice_closure_state"]
        )
        return order

    def test_ready_sale_order_is_marked_ready_to_invoice(self):
        order = self._create_ready_sale_order()
        self.assertEqual(order.od19_billing_readiness_state, "ready")
        self.assertEqual(order.od19_invoice_closure_state, "ready_to_invoice")

    def test_sale_order_with_posted_invoice_is_marked_invoiced(self):
        order = self._create_ready_sale_order()
        invoice = order._create_invoices()
        invoice.action_post()
        order.invalidate_recordset(["od19_invoice_closure_state"])
        self.assertEqual(order.od19_invoice_closure_state, "invoiced")
