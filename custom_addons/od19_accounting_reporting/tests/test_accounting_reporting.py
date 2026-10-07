from odoo import api
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAccountingReporting(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()
        cls.company_2 = cls.company_data_2["company"]
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
        base_user_group = cls.env.ref("base.group_user")
        account_user_group = cls.env.ref("account.group_account_user")
        Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.account_user = Users.create(
            {
                "name": "Accounting Reporting User",
                "login": "account.reporting.user@example.com",
                "email": "account.reporting.user@example.com",
                "company_id": cls.env.company.id,
                "company_ids": [(6, 0, [cls.env.company.id])],
                "group_ids": [(6, 0, [base_user_group.id, account_user_group.id])],
            }
        )

    def _fresh_report(self, *, user=None, allowed_company_ids=None):
        uid = user.id if user else self.env.uid
        context = dict(self.env.context)
        if allowed_company_ids is not None:
            context["allowed_company_ids"] = allowed_company_ids
        fresh_env = api.Environment(self.env.cr, uid, context)
        return fresh_env["od19.report.accounting.operational.closure"]

    def _fresh_sale_order(self, order):
        fresh_env = api.Environment(self.env.cr, self.env.uid, dict(self.env.context))
        return fresh_env["sale.order"].browse(order.id)

    def _metric_snapshot(self, *, company=None, user=None, allowed_company_ids=None):
        company = company or self.env.company
        report_row = self._fresh_report(
            user=user,
            allowed_company_ids=allowed_company_ids,
        ).search(
            [("company_id", "=", company.id)],
            limit=1,
        )
        return {
            "billable_backlog": report_row.billable_backlog,
            "open_receivable": report_row.open_receivable,
            "open_payable": report_row.open_payable,
        }

    def _create_ready_sale_order(self, *, company=None):
        company = company or self.env.company
        allowed_company_ids = [company.id]
        sale_order = (
            self.env["sale.order"]
            .with_company(company)
            .with_context(allowed_company_ids=allowed_company_ids)
            .sudo()
            .create(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": self.project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )
        )
        (
            self.env["sale.order.line"]
            .with_company(company)
            .with_context(allowed_company_ids=allowed_company_ids)
            .sudo()
            .create(
            {
                "order_id": sale_order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": 1.0,
                "product_uom_id": self.product.uom_id.id,
                "price_unit": 120.0,
            }
        )
        )
        (
            self.env["od19.billing.evidence"]
            .with_company(company)
            .with_context(allowed_company_ids=allowed_company_ids)
            .sudo()
            .create(
            {
                "name": "BILL-READY",
                "sale_order_id": sale_order.id,
                "evidence_type_id": self.evidence_type.id,
                "is_verified": True,
            }
        )
        )
        sale_order.action_confirm()
        return sale_order

    def _create_billable_quotation(self, *, state="draft", company=None):
        company = company or self.env.company
        allowed_company_ids = [company.id]
        quotation = (
            self.env["sale.order"]
            .with_company(company)
            .with_context(allowed_company_ids=allowed_company_ids)
            .sudo()
            .create(
                {
                    "partner_id": self.customer.id,
                    "od19_sale_mode": "one_time",
                    "od19_project_id": self.project.id,
                    "od19_project_owner_id": self.owner.id,
                }
            )
        )
        (
            self.env["sale.order.line"]
            .with_company(company)
            .with_context(allowed_company_ids=allowed_company_ids)
            .sudo()
            .create(
                {
                    "order_id": quotation.id,
                    "product_id": self.product.id,
                    "name": self.product.display_name,
                    "product_uom_qty": 1.0,
                    "product_uom_id": self.product.uom_id.id,
                    "price_unit": 120.0,
                }
            )
        )
        (
            self.env["od19.billing.evidence"]
            .with_company(company)
            .with_context(allowed_company_ids=allowed_company_ids)
            .sudo()
            .create(
                {
                    "name": f"BILLABLE-{state.upper()}",
                    "sale_order_id": quotation.id,
                    "evidence_type_id": self.evidence_type.id,
                    "is_verified": True,
                }
            )
        )
        if state == "sent":
            quotation.action_quotation_sent()
        return quotation

    def _create_posted_invoice_for_order(self, order):
        invoice = order._create_invoices()
        invoice.action_post()
        return invoice

    def test_company_report_excludes_invoiced_and_partially_paid_orders_from_backlog(self):
        before = self._metric_snapshot()

        ready_order = self._create_ready_sale_order()
        invoiced_order = self._create_ready_sale_order()
        partial_order = self._create_ready_sale_order()
        invoiced_invoice = self._create_posted_invoice_for_order(invoiced_order)
        partial_invoice = self._create_posted_invoice_for_order(partial_order)
        self._register_payment(partial_invoice, amount=partial_invoice.amount_total / 2)
        vendor_bill = self._create_invoice(
            move_type="in_invoice",
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=80.0)
            ],
        )

        ready_order = self._fresh_sale_order(ready_order)
        invoiced_order = self._fresh_sale_order(invoiced_order)
        partial_order = self._fresh_sale_order(partial_order)
        partial_invoice = partial_invoice.browse(partial_invoice.id)
        after = self._metric_snapshot()

        self.assertEqual(ready_order.od19_invoice_closure_state, "ready_to_invoice")
        self.assertEqual(invoiced_order.od19_invoice_closure_state, "invoiced")
        self.assertEqual(partial_order.od19_invoice_closure_state, "partially_paid")
        self.assertEqual(
            after["billable_backlog"] - before["billable_backlog"],
            ready_order.amount_total,
        )
        self.assertEqual(
            after["open_receivable"] - before["open_receivable"],
            invoiced_invoice.amount_residual + partial_invoice.amount_residual,
        )
        self.assertEqual(
            after["open_payable"] - before["open_payable"],
            vendor_bill.amount_residual,
        )

    def test_company_report_excludes_draft_and_sent_quotations_from_backlog(self):
        before = self._metric_snapshot()

        draft_quotation = self._create_billable_quotation(state="draft")
        sent_quotation = self._create_billable_quotation(state="sent")
        ready_order = self._create_ready_sale_order()

        draft_quotation = self._fresh_sale_order(draft_quotation)
        sent_quotation = self._fresh_sale_order(sent_quotation)
        ready_order = self._fresh_sale_order(ready_order)
        after = self._metric_snapshot()

        self.assertEqual(draft_quotation.state, "draft")
        self.assertEqual(sent_quotation.state, "sent")
        self.assertEqual(draft_quotation.od19_billing_readiness_state, "ready")
        self.assertEqual(sent_quotation.od19_billing_readiness_state, "ready")
        self.assertEqual(ready_order.state, "sale")
        self.assertEqual(
            after["billable_backlog"] - before["billable_backlog"],
            ready_order.amount_total,
        )

    def test_company_report_visibility_is_limited_to_allowed_companies(self):
        self._create_ready_sale_order()
        self._create_ready_sale_order(company=self.company_2)

        visible_rows = self._fresh_report(
            user=self.account_user,
            allowed_company_ids=self.account_user.company_ids.ids,
        ).search([])

        self.assertEqual(visible_rows.company_id, self.env.company)
        self.assertNotIn(self.company_2, visible_rows.mapped("company_id"))
        self.assertEqual(
            self._metric_snapshot(
                company=self.company_2,
                user=self.account_user,
                allowed_company_ids=self.account_user.company_ids.ids,
            ),
            {
                "billable_backlog": 0.0,
                "open_receivable": 0.0,
                "open_payable": 0.0,
            },
        )
