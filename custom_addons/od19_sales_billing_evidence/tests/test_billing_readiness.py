from odoo.tests.common import TransactionCase


class TestBillingReadiness(TransactionCase):
    def setUp(self):
        super().setUp()
        self.contractor = self.env["res.partner"].create({"name": "Contractor B"})
        self.owner = self.env["res.partner"].create({"name": "Owner B"})
        self.project = self.env["od19.sales.project"].create(
            {"name": "Convention Center", "project_owner_id": self.owner.id}
        )
        self.order = self.env["sale.order"].create(
            {
                "partner_id": self.contractor.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": self.project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )

    def test_delivery_evidence_marks_order_ready(self):
        evidence_type = self.env["od19.billing.evidence.type"].create(
            {
                "name": "Delivery Note",
                "trigger_kind": "delivery",
                "required_for_billing": True,
            }
        )
        self.env["od19.billing.evidence"].create(
            {
                "name": "DN-001",
                "sale_order_id": self.order.id,
                "evidence_type_id": evidence_type.id,
                "is_verified": True,
            }
        )
        self.order._compute_od19_billing_readiness_state()
        self.assertEqual(self.order.od19_billing_readiness_state, "ready")
