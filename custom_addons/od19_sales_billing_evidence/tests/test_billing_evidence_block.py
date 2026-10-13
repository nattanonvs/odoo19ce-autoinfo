from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestBillingEvidenceInvoiceBlock(TransactionCase):
    """Tests for billing evidence and invoice creation blocking."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create(
            {
                "name": "Customer B",
                "is_company": True,
                "email": "customer-b@example.com",
                "od19_is_commercial_customer": True,
            }
        )
        cls.owner = cls.env["res.partner"].create(
            {
                "name": "Owner B",
                "is_company": True,
                "od19_is_project_owner": True,
            }
        )
        cls.project = cls.env["project.project"].create(
            {"name": "Convention Center", "project_owner_id": cls.owner.id}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Service B", "type": "service", "list_price": 100.0}
        )
        cls.evidence_type = cls.env["od19.billing.evidence.type"].create(
            {
                "name": "Delivery Note",
                "trigger_kind": "delivery",
                "required_for_billing": True,
            }
        )

    def _make_order(self):
        return self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": self.project.id,
                "od19_project_owner_id": self.owner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                        },
                    )
                ],
            }
        )

    def test_verified_evidence_requires_attachment(self):
        order = self._make_order()
        evidence = self.env["od19.billing.evidence"].create(
            {
                "name": "DN-001",
                "sale_order_id": order.id,
                "evidence_type_id": self.evidence_type.id,
                "is_verified": False,
            }
        )
        # Not verified -> no attachment required
        self.assertFalse(evidence.attachment_ids)
        # Try to verify without attachment -> should fail
        with self.assertRaises(ValidationError):
            evidence.is_verified = True

    def test_verified_evidence_with_attachment_succeeds(self):
        order = self._make_order()
        attachment = self.env["ir.attachment"].create(
            {
                "name": "test.pdf",
                "datas": "bW9ja2RhdGE=",
                "res_model": "od19.billing.evidence",
            }
        )
        evidence = self.env["od19.billing.evidence"].create(
            {
                "name": "DN-002",
                "sale_order_id": order.id,
                "evidence_type_id": self.evidence_type.id,
                "attachment_ids": [(4, attachment.id)],
            }
        )
        evidence.is_verified = True
        self.assertTrue(evidence.is_verified)
        self.assertEqual(evidence.attachment_count, 1)

    def test_draft_order_readiness_state_is_draft(self):
        order = self._make_order()
        self.assertEqual(order.od19_billing_readiness_state, "draft")

    def test_confirmed_order_without_evidence_is_waiting(self):
        order = self._make_order()
        order.action_confirm()
        order._compute_od19_billing_readiness_state()
        self.assertEqual(order.od19_billing_readiness_state, "waiting")

    def test_confirmed_order_with_verified_evidence_is_ready(self):
        order = self._make_order()
        order.action_confirm()
        attachment = self.env["ir.attachment"].create(
            {
                "name": "test.pdf",
                "datas": "bW9ja2RhdGE=",
                "res_model": "od19.billing.evidence",
            }
        )
        self.env["od19.billing.evidence"].create(
            {
                "name": "DN-003",
                "sale_order_id": order.id,
                "evidence_type_id": self.evidence_type.id,
                "is_verified": True,
                "attachment_ids": [(4, attachment.id)],
            }
        )
        order._compute_od19_billing_readiness_state()
        self.assertEqual(order.od19_billing_readiness_state, "ready")

    def test_create_invoice_blocked_when_not_ready(self):
        order = self._make_order()
        order.action_confirm()
        order._compute_od19_billing_readiness_state()
        self.assertEqual(order.od19_billing_readiness_state, "waiting")
        with self.assertRaises(UserError):
            order._create_invoices(final=True)

    def test_create_invoice_allowed_when_ready(self):
        order = self._make_order()
        order.action_confirm()
        attachment = self.env["ir.attachment"].create(
            {
                "name": "test.pdf",
                "datas": "bW9ja2RhdGE=",
                "res_model": "od19.billing.evidence",
            }
        )
        self.env["od19.billing.evidence"].create(
            {
                "name": "DN-004",
                "sale_order_id": order.id,
                "evidence_type_id": self.evidence_type.id,
                "is_verified": True,
                "attachment_ids": [(4, attachment.id)],
            }
        )
        order._compute_od19_billing_readiness_state()
        self.assertEqual(order.od19_billing_readiness_state, "ready")
        invoices = order._create_invoices(final=True)
        self.assertTrue(invoices)
