# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


# ``res.partner`` carries fields made required by other installed modules (for
# instance ``group_rfq`` from ``purchase_stock``). While this module is being
# installed the registry does not carry them yet, so the class runs during
# ``post_install`` where the registry is complete.
@tagged("post_install", "-at_install")
class TestDepartmentSync(TransactionCase):
    """ตรวจกลไก mirror แผนกจาก hr.employee ไปยัง res.users.od19_department_id"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.department_a = cls.env["hr.department"].create(
            {"name": "OD19 Dept A", "code": "ODA"}
        )
        cls.department_b = cls.env["hr.department"].create(
            {"name": "OD19 Dept B", "code": "ODB"}
        )

    def _create_user(self, login):
        return self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )

    def _create_employee(self, user, department):
        return self.env["hr.employee"].create(
            {
                "name": "Employee of %s" % user.login,
                "user_id": user.id,
                "department_id": department.id,
            }
        )

    def test_user_without_employee_has_no_department(self):
        user = self._create_user("od19_sync_no_emp")
        self.assertFalse(user.od19_department_id)

    def test_linking_employee_sets_department(self):
        user = self._create_user("od19_sync_link")
        self._create_employee(user, self.department_a)
        self.assertEqual(user.od19_department_id, self.department_a)

    def test_moving_employee_department_follows(self):
        user = self._create_user("od19_sync_move")
        employee = self._create_employee(user, self.department_a)
        employee.write({"department_id": self.department_b.id})
        self.assertEqual(user.od19_department_id, self.department_b)

    def test_unlinking_employee_clears_department(self):
        user = self._create_user("od19_sync_unlink")
        employee = self._create_employee(user, self.department_a)
        employee.write({"user_id": False})
        self.assertFalse(user.od19_department_id)

    def test_department_code_is_related(self):
        user = self._create_user("od19_sync_code")
        self._create_employee(user, self.department_a)
        self.assertEqual(user.od19_department_code, "ODA")

    def test_cron_repairs_drift(self):
        user = self._create_user("od19_sync_cron")
        self._create_employee(user, self.department_a)
        # จำลองข้อมูลเพี้ยน: เขียนค่าแผนกผิดโดยข้าม hook ของโมดูล
        user.with_context(od19_skip_department_sync=True).write(
            {"od19_department_id": self.department_b.id}
        )
        self.assertEqual(user.od19_department_id, self.department_b)

        self.env["res.users"]._od19_cron_sync_all_departments()
        self.assertEqual(user.od19_department_id, self.department_a)

    def test_department_backlink_counts_users(self):
        user = self._create_user("od19_sync_backlink")
        self._create_employee(user, self.department_a)
        self.assertIn(user, self.department_a.od19_member_user_ids)

    def test_department_mirror_cron_exists(self):
        """cron ซ่อม mirror แผนกต้องถูกสร้างและใช้งานได้"""
        cron = self.env.ref(
            "od19_security_roles.cron_od19_department_mirror",
            raise_if_not_found=False,
        )
        self.assertTrue(cron, "ไม่พบ cron ซ่อม mirror แผนก")
        self.assertTrue(cron.active)
        self.assertEqual(cron.model_id.model, "res.users")
        self.assertIn("_od19_cron_sync_all_departments", cron.code)
