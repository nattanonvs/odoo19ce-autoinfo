# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields
from odoo.tests.common import TransactionCase


class TestIsoManagementReview(TransactionCase):
    """Tests for ISO management review meetings."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Review = cls.env["od19.iso.management.review"]
        cls.Input = cls.env["od19.iso.mr.input"]
        cls.Decision = cls.env["od19.iso.mr.decision"]

    def _create_review(self, **overrides):
        vals = {
            "title": "Management Review 2026",
            "date": fields.Date.today(),
            "chairman_id": self.env.user.id,
        }
        vals.update(overrides)
        return self.Review.create(vals)

    def test_review_defaults(self):
        review = self._create_review()
        self.assertEqual(review.state, "draft")
        self.assertTrue(review.name)
        self.assertNotEqual(review.name, "/")
        self.assertEqual(review.chairman_id, self.env.user)

    def test_review_state_flow(self):
        review = self._create_review()

        review.action_plan()
        self.assertEqual(review.state, "planned")

        review.action_start()
        self.assertEqual(review.state, "in_progress")

        review.action_reviewed()
        self.assertEqual(review.state, "reviewed")

        review.action_close()
        self.assertEqual(review.state, "closed")
        self.assertTrue(review.close_date)

        review.action_reset_to_draft()
        self.assertEqual(review.state, "draft")

        review.action_cancel()
        self.assertEqual(review.state, "cancel")


class TestIsoMrInput(TransactionCase):
    """Tests for management review inputs."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Review = cls.env["od19.iso.management.review"]
        cls.Input = cls.env["od19.iso.mr.input"]
        cls.review = cls.Review.create(
            {
                "title": "Review with inputs",
                "date": fields.Date.today(),
                "chairman_id": cls.env.user.id,
            }
        )

    def test_input_creation(self):
        item = self.Input.create(
            {
                "review_id": self.review.id,
                "topic": "audit",
                "summary": "Audit results reviewed",
            }
        )
        self.assertIn(item, self.review.input_ids)
        self.assertEqual(item.topic, "audit")

    def test_input_name_get_uses_topic_label(self):
        item = self.Input.create(
            {
                "review_id": self.review.id,
                "topic": "risk",
                "summary": "Risks reviewed",
            }
        )
        self.assertEqual(item.name_get()[0][1], "ความเสี่ยงและโอกาส")

    def test_input_name_get_uses_topic_other(self):
        item = self.Input.create(
            {
                "review_id": self.review.id,
                "topic": "other",
                "topic_other": "Custom topic",
                "summary": "Custom summary",
            }
        )
        self.assertEqual(item.name_get()[0][1], "Custom topic")


class TestIsoMrDecision(TransactionCase):
    """Tests for management review decisions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Review = cls.env["od19.iso.management.review"]
        cls.Decision = cls.env["od19.iso.mr.decision"]
        cls.review = cls.Review.create(
            {
                "title": "Review with decisions",
                "date": fields.Date.today(),
                "chairman_id": cls.env.user.id,
            }
        )

    def test_decision_defaults(self):
        decision = self.Decision.create(
            {
                "review_id": self.review.id,
                "decision_type": "improvement",
                "decision": "Improve the process",
            }
        )
        self.assertEqual(decision.status, "open")
        self.assertIn(decision, self.review.decision_ids)

    def test_decision_status_flow(self):
        decision = self.Decision.create(
            {
                "review_id": self.review.id,
                "decision_type": "resource",
                "decision": "Allocate more resources",
            }
        )

        decision.action_in_progress()
        self.assertEqual(decision.status, "in_progress")

        decision.action_done()
        self.assertEqual(decision.status, "done")

        decision.action_close()
        self.assertEqual(decision.status, "closed")
        self.assertTrue(decision.close_date)
