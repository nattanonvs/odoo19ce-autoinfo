from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestIsoDar(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.users = cls.env["res.users"].create([
            {"name": "DAR Req", "login": "dar_req"},
            {"name": "DAR Rev", "login": "dar_rev"},
            {"name": "DAR App", "login": "dar_app"},
            {"name": "DAR Fin", "login": "dar_fin"},
        ])

    def _new_dar(self, **kw):
        vals = {"request_type": "other", "reason": "test"}
        vals.update(kw)
        return self.env["od19.iso.dar"].create(vals)

    def test_number_format(self):
        dar = self._new_dar()
        year2 = fields.Date.today().strftime("%y")
        self.assertTrue(dar.name.startswith(f"DC{year2}-"))
        self.assertEqual(len(dar.name), len(f"DC{year2}-") + 3)

    def test_number_sequence_increments(self):
        a = self._new_dar()
        b = self._new_dar()
        self.assertNotEqual(a.name, b.name)
        self.assertEqual(int(b.name[-3:]), int(a.name[-3:]) + 1)

    def test_workflow_happy_path(self):
        dar = self._new_dar(
            requester_id=self.users[0].id,
            reviewer_id=self.users[1].id,
            approver_id=self.users[2].id,
            final_approver_id=self.users[3].id,
        )
        self.assertEqual(dar.status, "draft")
        dar.action_submit_for_review()
        self.assertEqual(dar.status, "review")
        dar.with_user(self.users[1]).action_review_approve()
        self.assertEqual(dar.status, "approval")
        dar.with_user(self.users[2]).action_approve()
        self.assertEqual(dar.status, "final_approval")
        dar.with_user(self.users[3]).action_final_approve()
        self.assertEqual(dar.status, "approved")

    def test_wrong_user_cannot_approve(self):
        dar = self._new_dar(
            reviewer_id=self.users[1].id,
            approver_id=self.users[2].id,
            final_approver_id=self.users[3].id,
        )
        dar.action_submit_for_review()
        with self.assertRaises(UserError):
            dar.with_user(self.users[0]).action_review_approve()

    def test_reject_returns_to_draft(self):
        dar = self._new_dar(reviewer_id=self.users[1].id)
        dar.action_submit_for_review()
        dar.with_user(self.users[1]).action_review_reject()
        self.assertEqual(dar.status, "draft")

    def test_document_required_for_revise(self):
        with self.assertRaises(Exception):
            self._new_dar(request_type="revise")

    def test_security_groups_exist(self):
        for xmlid in (
            "od19_iso_dar.group_iso_dar_user",
            "od19_iso_dar.group_iso_dar_controller",
            "od19_iso_dar.group_iso_dar_manager",
        ):
            self.assertTrue(self.env.ref(xmlid))

    def test_department_rule_exists(self):
        rule = self.env.ref("od19_iso_dar.rule_od19_iso_dar_department")
        self.assertIn("department_id", rule.domain_force)

    def test_approval_source_registered(self):
        source = self.env["od19.approval.source"].search(
            [("model_name", "=", "od19.iso.dar")], limit=1
        )
        self.assertTrue(source)
        self.assertEqual(source.sla_days, 5)
        self.assertEqual(len(source.step_ids), 3)
