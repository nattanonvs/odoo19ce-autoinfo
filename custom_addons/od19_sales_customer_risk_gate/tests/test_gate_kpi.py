from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import CreditGateCommon


@tagged("post_install", "-at_install")
class TestGateKpi(CreditGateCommon):
    def test_log_gate_event_helper(self):
        self.env["sale.order"]._od19_log_gate_event(
            self.customer, "blacklist", "quotation_create"
        )
        event = self.env["od19.credit.gate.event"].search(
            [("partner_id", "=", self.customer.id)]
        )
        self.assertEqual(event.reason_code, "blacklist")
        self.assertEqual(event.stage, "quotation_create")

    def test_kpis(self):
        other = self.env["res.partner"].create(
            {"name": "Rejected Co", "email": "rejected@example.com"}
        )
        self.customer.sudo().write(
            {
                "od19_credit_request_state": "pending",
                "od19_credit_request_date": fields.Datetime.now() - timedelta(days=4),
            }
        )
        other.sudo().od19_credit_request_state = "rejected"
        Event = self.env["od19.credit.gate.event"]
        Event.create(
            {"partner_id": self.customer.id, "reason_code": "blacklist", "stage": "quotation_create"}
        )
        Event.create(
            {"partner_id": self.customer.id, "reason_code": "credit", "stage": "order_confirm"}
        )
        kpi = self.env["res.partner"].od19_credit_gate_kpis()
        self.assertGreaterEqual(kpi["pending_count"], 1)
        self.assertGreaterEqual(kpi["pending_avg_age_days"], 4)
        self.assertGreaterEqual(kpi["rejected_count"], 1)
        self.assertGreaterEqual(kpi["blocked_blacklist_count"], 1)
        self.assertGreaterEqual(kpi["blocked_credit_count"], 1)
