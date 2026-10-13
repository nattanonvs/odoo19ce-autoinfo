# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestIsoCustomerSatisfaction(TransactionCase):
    """Basic tests for ISO Customer Satisfaction surveys."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "CSAT Customer"})

    def _create_survey(self, **overrides):
        vals = {
            "partner_id": self.partner.id,
            "date": fields.Date.today(),
            "method": "questionnaire",
        }
        vals.update(overrides)
        return self.env["od19.iso.customer.satisfaction"].create(vals)

    def test_create_survey_with_minimal_fields(self):
        survey = self._create_survey()
        self.assertTrue(survey)
        self.assertEqual(survey.partner_id, self.partner)
        self.assertEqual(survey.status, "draft")
        self.assertEqual(survey.method, "questionnaire")

    def test_overall_score_computation(self):
        survey = self._create_survey()
        self.env["od19.iso.csat.item"].create({
            "survey_id": survey.id,
            "name": "Quality",
            "category": "quality",
            "max_score": 5,
            "score": 4,
        })
        self.env["od19.iso.csat.item"].create({
            "survey_id": survey.id,
            "name": "Delivery",
            "category": "delivery",
            "max_score": 5,
            "score": 5,
        })
        # (4 + 5) / (5 + 5) * 5 = 4.5
        self.assertAlmostEqual(survey.overall_score, 4.5, places=2)

    def test_overall_score_zero_when_no_items(self):
        survey = self._create_survey()
        self.assertEqual(survey.overall_score, 0)

    def test_score_constraint(self):
        survey = self._create_survey()
        with self.assertRaises(ValidationError):
            self.env["od19.iso.csat.item"].create({
                "survey_id": survey.id,
                "name": "Bad Item",
                "category": "quality",
                "max_score": 5,
                "score": 10,
            })

    def test_score_negative_constraint(self):
        survey = self._create_survey()
        with self.assertRaises(ValidationError):
            self.env["od19.iso.csat.item"].create({
                "survey_id": survey.id,
                "name": "Negative Item",
                "category": "quality",
                "max_score": 5,
                "score": -1,
            })

    def test_survey_state_transitions(self):
        survey = self._create_survey()
        self.assertEqual(survey.status, "draft")

        survey.action_sent()
        self.assertEqual(survey.status, "sent")

        survey.action_complete()
        self.assertEqual(survey.status, "completed")

        survey.action_reset_to_draft()
        self.assertEqual(survey.status, "draft")

        survey.action_cancel()
        self.assertEqual(survey.status, "cancelled")

    def test_survey_close_sets_date(self):
        survey = self._create_survey()
        survey.action_close()
        self.assertEqual(survey.status, "completed")
        self.assertTrue(survey.close_date)

    def test_period_report_computation(self):
        survey = self._create_survey()
        self.env["od19.iso.csat.item"].create({
            "survey_id": survey.id,
            "name": "Item",
            "category": "quality",
            "max_score": 5,
            "score": 5,
        })
        report = self.env["od19.iso.csat.period.report"].create({
            "name": "Q1 Report",
            "period": "Q1",
            "survey_ids": [(6, 0, [survey.id])],
        })
        self.assertEqual(report.survey_count, 1)
        self.assertAlmostEqual(report.avg_score, 5.0, places=2)

        report.action_done()
        self.assertEqual(report.state, "done")
