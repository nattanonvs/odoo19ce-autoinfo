# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


# ``res.users.create`` มี constraint จากโมดูลอื่นที่ติดตั้งอยู่ (เช่น hr, mail)
# จึงรันเป็น ``post_install`` เพื่อให้ registry ครบก่อนสร้างผู้ใช้จริง
@tagged("post_install", "-at_install")
class TestExplicitGroupsWin(TransactionCase):
    """ผู้เรียกที่ระบุ ``group_ids`` เองต้องได้กลุ่มตามที่ระบุ ไม่ถูก default role ทับ"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_model = cls.env["res.users"]
        cls.group_user = cls.env.ref("base.group_user")
        cls.group_portal = cls.env.ref("base.group_portal")

    def _create_user(self, login, group_ids=None):
        vals = {"name": login, "login": login}
        if group_ids is not None:
            vals["group_ids"] = [Command.set(group_ids)]
        return self.user_model.create(vals)

    def test_portal_user_is_not_promoted_to_employee(self):
        """ผู้ใช้ที่สร้างเป็น portal ต้องอยู่กลุ่ม portal และไม่กลายเป็นพนักงานภายใน"""
        user = self._create_user("od19_guard_portal", self.group_portal.ids)
        self.assertIn(self.group_portal, user.group_ids)
        self.assertNotIn(self.group_user, user.group_ids)
        self.assertTrue(user.share, "portal user ต้องไม่ถูกยกระดับเป็น internal user")

    def test_explicit_groups_are_preserved(self):
        """กลุ่มที่ระบุมาตรง ๆ (เช่น base.group_system) ต้องไม่ถูกลบทิ้ง"""
        group_system = self.env.ref("base.group_system")
        user = self._create_user(
            "od19_guard_internal", (self.group_user | group_system).ids
        )
        self.assertIn(group_system, user.group_ids)
        self.assertIn(self.group_user, user.group_ids)

    def test_explicit_groups_keep_no_default_role_line(self):
        """เมื่อระบุกลุ่มเอง ต้องไม่มีการผูก default role ให้ผู้ใช้รายนั้น"""
        user = self._create_user("od19_guard_no_role", self.group_user.ids)
        self.assertFalse(user.role_line_ids)

    def test_default_role_still_applies_without_explicit_groups(self):
        """ไม่ระบุกลุ่ม (หรือระบุเป็นเซตว่าง) => ยังได้ default role ตามเดิม"""
        default_role = self.env["res.users.role"].search(
            [("is_default", "=", True)], limit=1
        )
        if not default_role:
            self.skipTest("ยังไม่มี role ที่ตั้ง is_default=True ในฐานข้อมูลนี้")

        for login, group_ids in (("od19_guard_default", None), ("od19_guard_empty", [])):
            with self.subTest(login=login):
                user = self._create_user(login, group_ids)
                self.assertIn(default_role, user.role_line_ids.mapped("role_id"))
