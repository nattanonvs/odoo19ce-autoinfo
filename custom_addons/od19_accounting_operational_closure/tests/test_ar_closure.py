from lxml import etree

from odoo import api
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
        cls.sale_form_view = cls.env.ref("sale.view_order_form")

    def _fresh_sale_order(self, order):
        fresh_env = api.Environment(self.env.cr, self.env.uid, dict(self.env.context))
        return fresh_env["sale.order"].browse(order.id)

    def _get_sale_form_arch(self):
        view_data = self.env["sale.order"].get_view(
            view_id=self.sale_form_view.id, view_type="form"
        )
        return etree.fromstring(view_data["arch"])

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
        return order

    def test_ready_sale_order_is_marked_ready_to_invoice(self):
        order = self._fresh_sale_order(self._create_ready_sale_order())
        self.assertEqual(order.od19_billing_readiness_state, "ready")
        self.assertEqual(order.od19_invoice_closure_state, "ready_to_invoice")

    def test_sale_order_with_draft_invoice_stays_ready_to_invoice(self):
        order = self._create_ready_sale_order()
        invoice = order._create_invoices()
        order = self._fresh_sale_order(order)
        self.assertEqual(invoice.state, "draft")
        self.assertEqual(order.od19_customer_invoice_count, 1)
        self.assertEqual(order.od19_invoice_closure_state, "ready_to_invoice")

    def test_sale_order_with_posted_invoice_is_marked_invoiced(self):
        order = self._create_ready_sale_order()
        invoice = order._create_invoices()
        invoice.action_post()
        order = self._fresh_sale_order(order)
        self.assertEqual(order.od19_customer_invoice_count, 1)
        self.assertEqual(order.od19_invoice_closure_state, "invoiced")

    def test_sale_order_partial_blocked_invoice_stays_partially_paid(self):
        order = self._create_ready_sale_order()
        invoice = order._create_invoices()
        invoice.action_post()

        self._register_payment(invoice, amount=invoice.amount_total / 2)
        invoice.action_toggle_block_payment()

        order = self._fresh_sale_order(order)
        invoice = invoice.browse(invoice.id)
        self.assertEqual(invoice.payment_state, "blocked")
        self.assertEqual(invoice.od19_operational_closure_state, "partially_paid")
        self.assertEqual(order.od19_invoice_closure_state, "partially_paid")

    def test_sale_order_form_places_closure_fields_once(self):
        arch = self._get_sale_form_arch()
        closure_state_fields = arch.xpath(
            "//group[@name='sale_info']//field[@name='od19_invoice_closure_state']"
        )
        customer_invoice_count_fields = arch.xpath(
            "//group[@name='sale_info']//field[@name='od19_customer_invoice_count']"
        )
        self.assertEqual(
            len(closure_state_fields),
            1,
            "Invoice closure state should be injected once on the Invoicing group.",
        )
        self.assertEqual(
            len(customer_invoice_count_fields),
            1,
            "Customer invoice count should be injected once on the Invoicing group.",
        )
