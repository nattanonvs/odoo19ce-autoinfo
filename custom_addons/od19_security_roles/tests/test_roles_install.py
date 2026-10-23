# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase


class TestRolesInstall(TransactionCase):
    """ตรวจว่า Layer 1 ติดตั้งแล้วมี privilege และกลุ่มกลางครบตามสัญญากลาง"""

    def _get_group(self, xml_id):
        return self.env.ref("od19_security_roles.%s" % xml_id)

    def test_role_privilege_exists(self):
        """privilege สำหรับจัดกลุ่มบทบาท OD19 ต้องถูกสร้าง"""
        privilege = self.env.ref("od19_security_roles.od19_role_privilege")
        self.assertTrue(privilege)
        self.assertEqual(privilege.name, "OD19 Roles")

    def test_central_groups_exist(self):
        """กลุ่มกลางทั้ง 4 ตัวต้องถูกสร้างและผูกกับ privilege เดียวกัน"""
        privilege = self.env.ref("od19_security_roles.od19_role_privilege")
        for xml_id in (
            "group_od19_department_scope",
            "group_od19_department_all",
            "group_od19_role_manager",
            "group_od19_credit_approver",
        ):
            group = self._get_group(xml_id)
            self.assertTrue(group, "ไม่พบกลุ่ม %s" % xml_id)
            self.assertEqual(
                group.privilege_id,
                privilege,
                "กลุ่ม %s ต้องอยู่ใต้ privilege od19_role_privilege" % xml_id,
            )

    def test_department_scope_implies_internal_user(self):
        """กลุ่มขอบเขตแผนกต้อง imply base.group_user"""
        scope = self._get_group("group_od19_department_scope")
        self.assertIn(self.env.ref("base.group_user"), scope.implied_ids)

    def test_role_manager_implies_erp_manager(self):
        """กลุ่มจัดการบทบาทต้องเข้าถึง Settings ได้ (group_erp_manager)"""
        role_manager = self._get_group("group_od19_role_manager")
        self.assertIn(self.env.ref("base.group_erp_manager"), role_manager.implied_ids)

    def test_department_all_is_out_of_scope(self):
        """กลุ่มเห็นทุกแผนกต้องไม่อยู่ในขอบเขตของ scope rule

        ถ้า department_all imply department_scope เมื่อใด บทบาทที่ได้
        department_all จะถูก scope rule จำกัดทันที ซึ่งผิดเจตนา
        """
        dept_all = self._get_group("group_od19_department_all")
        scope = self._get_group("group_od19_department_scope")
        self.assertNotIn(scope, dept_all.implied_ids)

    def test_system_group_implies_role_manager(self):
        """ผู้ดูแลระบบต้องได้กลุ่มจัดการบทบาทโดยอัตโนมัติ"""
        system = self.env.ref("base.group_system")
        self.assertIn(self._get_group("group_od19_role_manager"), system.implied_ids)
