from odoo import api
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAccountingReporting(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create(
            {
                "name": "Reporting Customer",
                "company_type": "company",
                "is_company": True,
                "email": "reporting.customer@example.com",
                "od19_is_commercial_customer": True,
            }
        )
        cls.owner = cls.env["res.partner"].create(
            {
                "name": "Reporting Owner",
                "company_type": "company",
                "is_company": True,
                "od19_is_project_owner": True,
            }
        )
        cls.project = cls.env["od19.sales.project"].create(
            {
                "name": "Reporting Project",
                "project_owner_id": cls.owner.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Reporting Product",
                "type": "consu",
                "sale_ok": True,
                "purchase_ok": True,
                "list_price": 120.0,
                "standard_price": 80.0,
            }
        )
        cls.evidence_type = cls.env["od19.billing.evidence.type"].create(
            {
                "name": "Delivery Proof",
                "trigger_kind": "delivery",
                "required_for_billing": True,
            }
        )

    def _fresh_report(self):
        fresh_env = api.Environment(self.env.cr, self.env.uid, dict(self.env.context))
        return fresh_env["od19.report.accounting.operational.closure"]

    def _metric_snapshot(self):
        report_row = self._fresh_report().search(
            [("company_id", "=", self.env.company.id)],
            limit=1,
        )
        return {
            "billable_backlog": report_row.billable_backlog,
            "open_receivable": report_row.open_receivable,
            "open_payable": report_row.open_payable,
        }

    def _create_ready_sale_order(self):
        sale_order = self.env["sale.order"].sudo().create(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": self.project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )
        self.env["sale.order.line"].sudo().create(
            {
                "order_id": sale_order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": 1.0,
                "product_uom_id": self.product.uom_id.id,
                "price_unit": 120.0,
            }
        )
        self.env["od19.billing.evidence"].sudo().create(
            {
                "name": "BILL-READY",
                "sale_order_id": sale_order.id,
                "evidence_type_id": self.evidence_type.id,
                "is_verified": True,
            }
        )
        sale_order.action_confirm()
        return sale_order

    def test_company_report_summarizes_billable_backlog_and_open_items(self):
        before = self._metric_snapshot()

        order = self._create_ready_sale_order()
        customer_invoice = self._create_invoice(
            move_type="out_invoice",
            partner_id=self.customer,
            post=True,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product, price_unit=200.0)
            ],
        )
        vendor_bill = self._create_invoice(
            move_type="in_invoice",
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=80.0)
            ],
        )

        after = self._metric_snapshot()

        self.assertEqual(order.od19_billing_readiness_state, "ready")
        self.assertEqual(order.od19_invoice_closure_state, "ready_to_invoice")
        self.assertEqual(
            after["billable_backlog"] - before["billable_backlog"],
            order.amount_total,
        )
        self.assertEqual(
            after["open_receivable"] - before["open_receivable"],
            customer_invoice.amount_residual,
        )
        self.assertEqual(
            after["open_payable"] - before["open_payable"],
            vendor_bill.amount_residual,
        )
