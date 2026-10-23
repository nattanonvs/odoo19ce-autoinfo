# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


# ``res.partner`` carries fields made required by other installed modules (for
# instance ``group_rfq`` from ``purchase_stock``). While this module is being
# installed the registry does not carry them yet, so the class runs during
# ``post_install`` where the registry is complete.
@tagged("post_install", "-at_install")
class TestRoleAssignment(TransactionCase):
    """ตรวจการเข้าถึง res.users.role และการมอบ/ถอนบทบาทให้ผู้ใช้"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.role_model = cls.env["res.users.role"]
        cls.group_user = cls.env.ref("base.group_user")

    def _create_internal_user(self, login, extra_groups=None):
        groups = self.group_user
        if extra_groups:
            groups |= extra_groups
        return self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "group_ids": [Command.set(groups.ids)],
            }
        )

    def test_role_manager_can_create_and_write_role(self):
        """ผู้จัดการบทบาทต้องสร้างและแก้ res.users.role ได้"""
        manager = self._create_internal_user(
            "od19_role_mgr",
            self.env.ref("od19_security_roles.group_od19_role_manager"),
        )
        role = self.role_model.with_user(manager).create(
            {"name": "OD19 Role Manager Probe"}
        )
        role.with_user(manager).write({"name": "OD19 Role Manager Probe (edited)"})
        self.assertEqual(role.name, "OD19 Role Manager Probe (edited)")

    def test_plain_user_cannot_create_role(self):
        """พนักงานทั่วไปที่ไม่มีกลุ่มจัดการบทบาทต้องสร้าง role ไม่ได้"""
        plain_user = self._create_internal_user("od19_plain_user")
        with self.assertRaises(AccessError):
            self.role_model.with_user(plain_user).create(
                {"name": "OD19 Forbidden Role"}
            )

    def test_assigning_role_grants_implied_groups(self):
        """มอบบทบาทแล้วผู้ใช้ได้ implied groups; ถอนแล้วถูกลบออก"""
        partner_manager = self.env.ref("base.group_partner_manager")
        role = self.role_model.create(
            {
                "name": "OD19 Assignment Probe",
                "implied_ids": [
                    Command.set([self.group_user.id, partner_manager.id]),
                ],
            }
        )
        user = self._create_internal_user("od19_role_assignee")
        self.assertNotIn(partner_manager, user.group_ids)

        user.write({"role_line_ids": [Command.create({"role_id": role.id})]})
        self.assertIn(partner_manager, user.group_ids)

        user.role_line_ids.filtered(lambda line: line.role_id == role).unlink()
        self.assertNotIn(partner_manager, user.group_ids)

    def test_role_menu_is_available(self):
        """เมนูจัดการบทบาทต้องอยู่ใต้ Users & Companies (มาจาก OCA base_user_role)"""
        menu = self.env.ref(
            "base_user_role.menu_action_res_users_role_tree",
            raise_if_not_found=False,
        )
        self.assertTrue(menu, "ไม่พบเมนูจัดการบทบาทจาก base_user_role")
        self.assertEqual(menu.parent_id, self.env.ref("base.menu_users"))
