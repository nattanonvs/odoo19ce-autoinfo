from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestAfterSalesReporting(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create(
            {"name": "After-Sales Report Customer"}
        )
        self.product = self.env["product.product"].create(
            {"name": "After-Sales Report Product", "type": "consu"}
        )

    def test_ticket_kpi_groups_by_team_and_service_type(self):
        team = self.env["helpdesk.ticket.team"].create(
            {"name": "Report Sales Services Team", "team_type": "customer_service"}
        )
        for index in range(2):
            self.env["helpdesk.ticket"].create(
                {
                    "name": f"Report Ticket {index}",
                    "team_id": team.id,
                    "service_type": "repair",
                }
            )

        rows = self.env["od19.report.after.sales.ticket"].search(
            [("team_id", "=", team.id), ("service_type", "=", "repair")]
        )

        self.assertEqual(sum(rows.mapped("ticket_count")), 2)
        self.assertTrue(all(row.team_type == "customer_service" for row in rows))

    def test_warranty_kpi_counts_claims_and_turnaround(self):
        for index in range(2):
            self.env["od19.warranty.claim"].create(
                {
                    "partner_id": self.partner.id,
                    "product_id": self.product.id,
                    "claim_type": "warranty",
                    "description": f"Report claim {index}",
                }
            )
        done_claim = self.env["od19.warranty.claim"].create(
            {
                "partner_id": self.partner.id,
                "product_id": self.product.id,
                "claim_type": "warranty",
                "description": "Report claim done",
            }
        )
        done_claim.write({"state": "done"})

        draft_rows = self.env["od19.report.after.sales.warranty.claim"].search(
            [("claim_type", "=", "warranty"), ("state", "=", "draft")]
        )
        done_rows = self.env["od19.report.after.sales.warranty.claim"].search(
            [("claim_type", "=", "warranty"), ("state", "=", "done")]
        )

        self.assertEqual(sum(draft_rows.mapped("claim_count")), 2)
        self.assertEqual(sum(done_rows.mapped("claim_count")), 1)
        self.assertGreaterEqual(
            sum(done_rows.mapped("avg_turnaround_days")), 0.0
        )

    def test_service_card_kpi_reports_due_and_overdue(self):
        service_date = fields.Date.context_today(self.env["od19.service.card"])
        self.env["od19.service.card"].create(
            {
                "partner_id": self.partner.id,
                "product_id": self.product.id,
                "service_type": "preventive",
                "service_date": service_date - timedelta(days=10),
                "service_interval": 5,
            }
        )

        rows = self.env["od19.report.after.sales.service.card"].search(
            [("service_type", "=", "preventive"), ("state", "=", "draft")]
        )

        self.assertEqual(sum(rows.mapped("card_count")), 1)
        self.assertEqual(sum(rows.mapped("due_count")), 1)
        self.assertEqual(sum(rows.mapped("overdue_count")), 1)
        self.assertEqual(sum(rows.mapped("sla_breach_count")), 0)

    def test_product_return_kpi_reports_reason_and_refund_value(self):
        for _index in range(2):
            self.env["od19.product.return"].create(
                {
                    "partner_id": self.partner.id,
                    "product_id": self.product.id,
                    "reason": "defective",
                    "quantity": 2.0,
                    "refund_amount": 150.0,
                }
            )

        rows = self.env["od19.report.after.sales.product.return"].search(
            [("reason", "=", "defective"), ("state", "=", "draft")]
        )

        self.assertEqual(sum(rows.mapped("return_count")), 2)
        self.assertEqual(sum(rows.mapped("total_quantity")), 4.0)
        self.assertEqual(sum(rows.mapped("total_refund_amount")), 300.0)

    def test_qc_kpi_reports_pass_rate_and_nonconformities(self):
        base_vals = {
            "inspection_type": "incoming",
            "product_id": self.product.id,
            "qty_tested": 10.0,
        }
        self.env["od19.qc.inspection"].create(dict(base_vals, qty_accepted=10.0))
        self.env["od19.qc.inspection"].create(dict(base_vals, qty_accepted=8.0))

        rows = self.env["od19.report.after.sales.qc.inspection"].search(
            [("inspection_type", "=", "incoming")]
        )
        pass_rows = rows.filtered(lambda row: row.result == "pass")
        fail_rows = rows.filtered(lambda row: row.result == "fail")

        self.assertEqual(sum(pass_rows.mapped("inspection_count")), 1)
        self.assertAlmostEqual(pass_rows.pass_rate, 100.0, places=2)
        self.assertEqual(sum(fail_rows.mapped("inspection_count")), 1)
        self.assertAlmostEqual(fail_rows.pass_rate, 0.0, places=2)
        self.assertEqual(sum(fail_rows.mapped("rejected_qty")), 2.0)

    def test_csat_kpi_aggregates_by_period(self):
        for _index in range(2):
            survey = self.env["od19.iso.customer.satisfaction"].create(
                {
                    "partner_id": self.partner.id,
                    "period": "Q1/2569",
                    "overall_csat": "4",
                    "status": "completed",
                    "item_ids": [
                        (
                            0,
                            0,
                            {
                                "name": "Product Quality",
                                "category": "quality",
                                "max_score": 5.0,
                                "score": 4.0,
                            },
                        )
                    ],
                }
            )
            self.assertAlmostEqual(survey.overall_score, 4.0, places=2)

        rows = self.env["od19.report.after.sales.csat.period"].search(
            [("period", "=", "Q1/2569")]
        )

        self.assertEqual(sum(rows.mapped("survey_count")), 2)
        self.assertEqual(sum(rows.mapped("completed_count")), 2)
        self.assertAlmostEqual(rows.avg_score, 4.0, places=2)
        self.assertAlmostEqual(rows.avg_csat, 4.0, places=2)
