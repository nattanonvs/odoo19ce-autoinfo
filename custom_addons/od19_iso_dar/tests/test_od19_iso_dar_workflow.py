# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

# ประเภทคำขอที่ต้องอ้างอิงเอกสารเดิม / ต้องระบุจำนวนพิมพ์ (ต้องตรงกับโมดูล)
DOCUMENT_REQUIRED_TYPES = (
    "revise",
    "obsolete",
    "copy_controlled",
    "copy_uncontrolled",
    "change_distribution",
    "print",
    "broad_distribution",
    "revise_with_print",
)
PRINT_REQUIRED_TYPES = ("print", "new_with_print", "revise_with_print")
EXPECTED_TYPES = {
    "new",
    "revise",
    "obsolete",
    "copy_controlled",
    "copy_uncontrolled",
    "change_distribution",
    "print",
    "broad_distribution",
    "new_with_print",
    "revise_with_print",
    "other",
}


@tagged("post_install", "-at_install")
class TestIsoDarWorkflow(TransactionCase):
    """WP1 — ทดสอบ workflow ขยายของ od19.iso.dar (effect ทุก type + idempotency)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.category = cls.env["od19.iso.document.category"].search([], limit=1)
        cls.users = cls.env["res.users"].create([
            {"name": "WF Req", "login": "wf_req"},
            {"name": "WF Rev", "login": "wf_rev"},
            {"name": "WF App", "login": "wf_app"},
            {"name": "WF Fin", "login": "wf_fin"},
        ])

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _doc(self, revision="00", status="approved", **kw):
        vals = {
            "document_title": "เอกสาร WF",
            "category_id": self.category.id,
            "revision": revision,
            "status": status,
        }
        vals.update(kw)
        return self.env["od19.iso.document"].create(vals)

    def _dar(self, **kw):
        vals = {
            "request_type": "other",
            "reason": "test",
            "requester_id": self.users[0].id,
            "reviewer_id": self.users[1].id,
            "approver_id": self.users[2].id,
            "final_approver_id": self.users[3].id,
        }
        vals.update(kw)
        return self.env["od19.iso.dar"].create(vals)

    def _approve(self, dar):
        """เดินครบ 4 ขั้นอนุมัติด้วยผู้ใช้ที่กำหนด."""
        dar.action_submit_for_review()
        dar.with_user(self.users[1]).action_review_approve()
        dar.with_user(self.users[2]).action_approve()
        dar.with_user(self.users[3]).action_final_approve()
        return dar

    def _issued_copies(self, doc, copies=1):
        """สร้างสำเนาที่จ่ายแล้ว (state=issued) ของเอกสาร."""
        request = self.env["od19.iso.print.request"].create({
            "document_id": doc.id,
            "copies_count": copies,
            "request_type": "new_print",
            "requester_id": self.users[0].id,
        })
        request.action_submit()
        request.action_approve()
        request.copy_ids.action_issue()
        return request.copy_ids

    def _active_distribution(self, doc, recipient):
        dist = self.env["od19.iso.distribution.list"].create({
            "document_id": doc.id,
            "line_ids": [(0, 0, {
                "recipient_id": recipient.id,
                "copies_required": 1,
                "copy_type": "controlled",
            })],
        })
        dist.action_activate()
        return dist

    # ------------------------------------------------------------------
    # 1. completeness ของ request_type
    # ------------------------------------------------------------------
    def test_request_type_selection_complete(self):
        selection = dict(self.env["od19.iso.dar"]._fields["request_type"].selection)
        self.assertTrue(EXPECTED_TYPES.issubset(set(selection)))

    def test_new_print_fields_exist(self):
        fields_map = self.env["od19.iso.dar"]._fields
        for name in (
            "print_request_id",
            "distribution_list_id",
            "target_holder_ids",
            "copies_count",
            "print_scope",
        ):
            self.assertIn(name, fields_map, "ขาดฟิลด์ %s" % name)

    # ------------------------------------------------------------------
    # 2. required field ตาม type
    # ------------------------------------------------------------------
    def test_document_required_by_type(self):
        for rtype in DOCUMENT_REQUIRED_TYPES:
            with self.assertRaises(UserError, msg="type=%s ควรบังคับเอกสาร" % rtype):
                self._dar(request_type=rtype)

    def test_print_requires_copies(self):
        doc = self._doc()
        for rtype in PRINT_REQUIRED_TYPES:
            with self.assertRaises(UserError, msg="type=%s ควรบังคับจำนวนสำเนา" % rtype):
                self._dar(request_type=rtype, document_id=doc.id, copies_count=0)

    # ------------------------------------------------------------------
    # 3. print (PDR) — effect + idempotency
    # ------------------------------------------------------------------
    def test_effect_print_creates_request(self):
        doc = self._doc()
        dar = self._dar(
            request_type="print", document_id=doc.id,
            copies_count=3, print_scope="controlled",
        )
        self._approve(dar)
        self.assertTrue(dar.effect_applied)
        self.assertTrue(dar.print_request_id)
        request = dar.print_request_id
        self.assertEqual(request.copies_count, 3)
        self.assertEqual(request.copy_type, "controlled")
        self.assertEqual(request.request_type, "new_print")
        self.assertEqual(request.state, "review")
        self.assertEqual(
            len(self.env["od19.iso.print.request"].search([
                ("document_id", "=", doc.id),
            ])),
            1,
        )

    def test_effect_print_idempotent(self):
        doc = self._doc()
        dar = self._dar(
            request_type="print", document_id=doc.id, copies_count=2
        )
        self._approve(dar)
        request_id = dar.print_request_id.id
        # อนุมัติ/ทำ effect ซ้ำ ต้องไม่เกิดผลซ้ำ
        dar._apply_approval_effect()
        dar._create_print_request()
        self.assertEqual(dar.print_request_id.id, request_id)
        self.assertEqual(dar.print_request_id.copy_count, 0)  # ยังไม่ approve พิมพ์
        self.assertEqual(
            len(self.env["od19.iso.print.request"].search([
                ("document_id", "=", doc.id),
            ])),
            1,
        )

    # ------------------------------------------------------------------
    # 4. change_distribution (CDL)
    # ------------------------------------------------------------------
    def test_effect_change_distribution_supersedes(self):
        doc = self._doc()
        old = self._active_distribution(doc, self.users[0])
        dar = self._dar(
            request_type="change_distribution",
            document_id=doc.id,
            distribution_list_id=old.id,
        )
        self._approve(dar)
        old.invalidate_recordset()
        self.assertEqual(old.state, "superseded")
        new_lists = self.env["od19.iso.distribution.list"].search([
            ("document_id", "=", doc.id),
            ("id", "!=", old.id),
        ])
        self.assertEqual(len(new_lists), 1)
        self.assertEqual(new_lists.state, "active")
        self.assertEqual(new_lists.line_count, old.line_count)

    # ------------------------------------------------------------------
    # 5. revise (EDR) + ส่งผลกับสำเนาที่จ่ายแล้ว
    # ------------------------------------------------------------------
    def test_effect_revise_bumps_revision(self):
        doc = self._doc()
        dar = self._dar(request_type="revise", document_id=doc.id)
        self._approve(dar)
        doc.invalidate_recordset()
        self.assertEqual(doc.revision, "01")
        self.assertEqual(doc.status, "approved")

    def test_effect_revise_replaces_issued_copies(self):
        doc = self._doc(revision="00")
        copies = self._issued_copies(doc, copies=2)
        self.assertEqual(set(copies.mapped("state")), {"issued"})
        dar = self._dar(request_type="revise", document_id=doc.id)
        self._approve(dar)
        doc.invalidate_recordset()
        copies.invalidate_recordset()
        self.assertEqual(doc.revision, "01")
        self.assertEqual(set(copies.mapped("state")), {"replaced"})
        replace_requests = self.env["od19.iso.print.request"].search([
            ("document_id", "=", doc.id),
            ("request_type", "=", "replace_revision"),
        ])
        self.assertEqual(len(replace_requests), 1)
        self.assertEqual(replace_requests.copies_count, 2)

    # ------------------------------------------------------------------
    # 6. obsolete (CDR) — เรียกคืนสำเนา
    # ------------------------------------------------------------------
    def test_effect_obsolete_recalls_copies(self):
        doc = self._doc()
        issued = self._issued_copies(doc, copies=1)
        # สร้างสำเนาสำรอง (reserved) เพิ่มอีก 1 ใบ
        reserved_request = self.env["od19.iso.print.request"].create({
            "document_id": doc.id,
            "copies_count": 1,
            "request_type": "new_print",
            "requester_id": self.users[0].id,
        })
        reserved_request.action_submit()
        reserved_request.action_approve()
        reserved = reserved_request.copy_ids

        dar = self._dar(request_type="obsolete", document_id=doc.id)
        self._approve(dar)
        doc.invalidate_recordset()
        issued.invalidate_recordset()
        reserved.invalidate_recordset()
        self.assertEqual(doc.status, "obsolete")
        self.assertFalse(doc.active)
        self.assertEqual(issued.state, "returned")
        self.assertEqual(reserved.state, "destroyed")

    # ------------------------------------------------------------------
    # 7. broad_distribution (BDR)
    # ------------------------------------------------------------------
    def test_effect_broad_distribution(self):
        doc = self._doc()
        dar = self._dar(
            request_type="broad_distribution",
            document_id=doc.id,
            copies_count=1,
            target_holder_ids=[(6, 0, [self.users[0].id, self.users[1].id])],
        )
        self._approve(dar)
        new_lists = self.env["od19.iso.distribution.list"].search([
            ("document_id", "=", doc.id),
        ])
        self.assertEqual(len(new_lists), 1)
        self.assertEqual(new_lists.state, "active")
        self.assertEqual(new_lists.line_count, 2)
        self.assertTrue(dar.print_request_id)
        self.assertEqual(dar.print_request_id.copy_type, "uncontrolled")

    # ------------------------------------------------------------------
    # 8. new_with_print (NDRP) ผ่าน wizard
    # ------------------------------------------------------------------
    def test_effect_new_with_print_via_wizard(self):
        dar = self._dar(
            request_type="new_with_print",
            category_id=self.category.id,
            copies_count=2,
        )
        self._approve(dar)
        self.assertEqual(dar.status, "approved")
        wizard = self.env["od19.iso.dar.create.document"].with_context(
            active_id=dar.id, active_model="od19.iso.dar"
        ).create({"document_title": "เอกสารใหม่ + พิมพ์"})
        wizard.action_create_document()
        self.assertTrue(dar.document_id)
        self.assertTrue(dar.print_request_id)
        self.assertEqual(dar.print_request_id.copies_count, 2)

    # ------------------------------------------------------------------
    # 9. revise_with_print (EDRP)
    # ------------------------------------------------------------------
    def test_effect_revise_with_print(self):
        doc = self._doc()
        dar = self._dar(
            request_type="revise_with_print",
            document_id=doc.id,
            copies_count=2,
        )
        self._approve(dar)
        doc.invalidate_recordset()
        self.assertEqual(doc.revision, "01")
        self.assertTrue(dar.print_request_id)
        self.assertEqual(dar.print_request_id.copies_count, 2)

    # ------------------------------------------------------------------
    # 10. ตัวช่วยเปิดใบขอพิมพ์
    # ------------------------------------------------------------------
    def test_action_view_print_request(self):
        doc = self._doc()
        dar = self._dar(
            request_type="print", document_id=doc.id, copies_count=1
        )
        self._approve(dar)
        action = dar.action_view_print_request()
        self.assertEqual(action["res_id"], dar.print_request_id.id)
        self.assertEqual(action["res_model"], "od19.iso.print.request")

    # ------------------------------------------------------------------
    # 11. อื่น ๆ (other) ไม่มีผลอัตโนมัติ
    # ------------------------------------------------------------------
    def test_effect_other_no_side_effect(self):
        doc = self._doc()
        dar = self._dar(request_type="other", document_id=doc.id)
        self._approve(dar)
        self.assertTrue(dar.effect_applied)
        self.assertFalse(dar.print_request_id)
        self.assertEqual(doc.revision, "00")
