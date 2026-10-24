# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import Command
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase


# แผนที่ โมเดล -> ฟิลด์แผนก ที่เฟส B ติดตั้ง department record rule ไว้
# ใช้ตรวจว่า rule ถูกโหลดจริงครบทุกโมดูล (ข้ามโมเดลที่โมดูลเจ้าของไม่ได้ติดตั้งในฐานนี้)
DEPARTMENT_RULE_FIELDS = {
    "stock.request.order": "department_id",
    "project.project": "od19_department_id",
    "od19.iso.document": "department_id",
    "od19.iso.nonconformity": "department_id",
    "od19.iso.risk": "department_id",
    "od19.iso.training.participant": "department_id",
    "od19.iso.calibration.equipment": "department_id",
    "od19.iso.audit": "auditee_department_id",
    "helpdesk.ticket": "department_id",
    "announcement": "department_id",
    "fleet.vehicle": "department_id",
}

SCOPE_GROUP_XMLID = "od19_security_roles.group_od19_department_scope"
ALL_GROUP_XMLID = "od19_security_roles.group_od19_department_all"


# เทสต์นี้ต้องรันหลัง registry ครบ (post_install) เพราะตรวจ rule ที่อ้างกลุ่มกลาง
# จาก od19_security_roles และฟิลด์แผนกที่กระจายอยู่หลายโมดูลธุรกิจ
@tagged("post_install", "-at_install")
class TestDepartmentScope(TransactionCase):
    """เทสต์รวมเฟส B: ขอบเขตการมองเห็นข้อมูลตามแผนก (department record rule)

    กติกา:
    - ผู้ใช้ใน ``group_od19_department_scope`` เห็นเฉพาะเอกสารของแผนกตัวเอง
      และเอกสารที่ยังไม่ระบุแผนก (Fail-safe)
    - ผู้ใช้ใน ``group_od19_department_all`` ไม่ถูกจำกัดด้วย scope rule จึงเห็นทุกแผนก
      แม้จะยังมี scope group จากการเป็นพนักงานทั่วไป (role_employee_base) ก็ตาม
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.scope_group = cls.env.ref(SCOPE_GROUP_XMLID)
        cls.all_group = cls.env.ref(ALL_GROUP_XMLID)
        cls.dept_a = cls.env["hr.department"].create(
            {"name": "Scope Dept A", "code": "SDA"}
        )
        cls.dept_b = cls.env["hr.department"].create(
            {"name": "Scope Dept B", "code": "SDB"}
        )
        # สามเอกสารอ้างอิงบนโมเดลที่มี department rule (fleet.vehicle):
        # แผนก A, แผนก B และไม่ระบุแผนก
        cls.vehicle_a = cls._create_vehicle("SCOPE-A", cls.dept_a)
        cls.vehicle_b = cls._create_vehicle("SCOPE-B", cls.dept_b)
        cls.vehicle_none = cls._create_vehicle("SCOPE-N", None)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @classmethod
    def _create_vehicle(cls, plate, department):
        model = cls.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = cls.env["fleet.vehicle.model.brand"].search(
                [], limit=1
            ) or cls.env["fleet.vehicle.model.brand"].create(
                {"name": "Scope Brand"}
            )
            model = cls.env["fleet.vehicle.model"].create(
                {"name": "Scope Model", "brand_id": brand.id}
            )
        return cls.env["fleet.vehicle"].create(
            {
                "license_plate": plate,
                "model_id": model.id,
                "department_id": department.id if department else False,
            }
        )

    def _create_user(self, login, group_xmlids, department):
        """สร้างผู้ใช้พร้อมกลุ่มที่กำหนดแบบคงที่ (deterministic)

        ``base_user_role`` override ``create()``/``write()`` ให้เรียก
        ``set_groups_from_roles()`` ซึ่งจะเขียนทับ ``group_ids`` ด้วยกลุ่มของ
        default role (``role_employee_base``) จึงต้องล้าง role line ก่อน แล้ว
        กำหนดกลุ่ม/แผนกที่ต้องการหลังสุด เพื่อไม่ให้ค่าที่ตั้งไว้ถูกเขียนทับ
        """
        user = new_test_user(self.env, login=login, groups=",".join(group_xmlids))
        user.write({"role_line_ids": [Command.clear()]})
        groups = self.env["res.groups"].browse()
        for xmlid in group_xmlids:
            groups |= self.env.ref(xmlid)
        user.write(
            {
                "group_ids": [Command.set(groups.ids)],
                "od19_department_id": department.id if department else False,
            }
        )
        return user

    def _make_scoped_user(self, login, department):
        """ผู้ใช้ที่ถูกจำกัดขอบเขตด้วยแผนก (มีเฉพาะ scope group)"""
        return self._create_user(
            login,
            ["base.group_user", "fleet.fleet_group_user", SCOPE_GROUP_XMLID],
            department,
        )

    def _make_all_department_user(self, login):
        """ผู้ใช้ที่เห็นทุกแผนก

        จำลองสภาพจริง: ผู้ใช้ทุกคนได้ ``role_employee_base`` (scope) มาโดยค่าเริ่มต้น
        และบทบาทระดับบริหาร/บัญชี/คลังเพิ่ม ``group_od19_department_all`` เข้าไป
        """
        return self._create_user(
            login,
            [
                "base.group_user",
                "fleet.fleet_group_user",
                SCOPE_GROUP_XMLID,
                ALL_GROUP_XMLID,
            ],
            None,
        )

    # ------------------------------------------------------------------
    # การลงทะเบียน rule (ข้อมูล)
    # ------------------------------------------------------------------
    def test_department_rules_registered(self):
        """ทุกโมเดลในเฟส B ต้องมี rule ครบทั้ง scope และ all และอ้างฟิลด์แผนกถูกต้อง"""
        rule_model = self.env["ir.rule"]
        for model_name, field_name in DEPARTMENT_RULE_FIELDS.items():
            model = self.env["ir.model"].search(
                [("model", "=", model_name)], limit=1
            )
            if not model:
                # โมดูลเจ้าของโมเดลไม่ได้ติดตั้งในฐานนี้ -> ข้าม
                continue
            scope_rules = rule_model.search(
                [("model_id", "=", model.id), ("groups", "in", self.scope_group.id)]
            )
            self.assertTrue(
                scope_rules, "ไม่พบ department rule สำหรับ %s" % model_name
            )
            self.assertTrue(
                any(
                    field_name in (rule.domain_force or "") for rule in scope_rules
                ),
                "department rule ของ %s ไม่ได้อ้างฟิลด์ %s"
                % (model_name, field_name),
            )
            all_rules = rule_model.search(
                [("model_id", "=", model.id), ("groups", "in", self.all_group.id)]
            )
            self.assertTrue(
                all_rules, "ไม่พบ all-departments rule สำหรับ %s" % model_name
            )

    # ------------------------------------------------------------------
    # พฤติกรรมขอบเขตแผนก (ใช้งานจริง)
    # ------------------------------------------------------------------
    def test_scope_user_sees_own_department_and_unassigned(self):
        """ผู้ใช้แผนก A เห็นเอกสารแผนก A + เอกสารที่ไม่ระบุแผนก แต่ไม่เห็นของแผนก B"""
        user = self._make_scoped_user("od19_scope_a", self.dept_a)
        vehicles = self.env["fleet.vehicle"].with_user(user).search([])
        self.assertIn(self.vehicle_a, vehicles)
        self.assertIn(self.vehicle_none, vehicles)
        self.assertNotIn(self.vehicle_b, vehicles)

    def test_scope_user_with_other_department(self):
        """ผู้ใช้แผนก B เห็นเอกสารแผนก B + ไม่ระบุแผนก แต่ไม่เห็นของแผนก A"""
        user = self._make_scoped_user("od19_scope_b", self.dept_b)
        vehicles = self.env["fleet.vehicle"].with_user(user).search([])
        self.assertIn(self.vehicle_b, vehicles)
        self.assertIn(self.vehicle_none, vehicles)
        self.assertNotIn(self.vehicle_a, vehicles)

    def test_scope_user_without_department_sees_only_unassigned(self):
        """ผู้ใช้ scope ที่ยังไม่มีแผนก เห็นเฉพาะเอกสารที่ไม่ระบุแผนก"""
        user = self._make_scoped_user("od19_scope_none", None)
        vehicles = self.env["fleet.vehicle"].with_user(user).search([])
        self.assertIn(self.vehicle_none, vehicles)
        self.assertNotIn(self.vehicle_a, vehicles)
        self.assertNotIn(self.vehicle_b, vehicles)

    def test_department_all_user_sees_everything(self):
        """ผู้ใช้ที่มีกลุ่มเห็นทุกแผนก เห็นข้อมูลทุกแผนก แม้ยังติด scope group อยู่"""
        user = self._make_all_department_user("od19_scope_all")
        self.assertIn(
            self.all_group,
            user.group_ids,
            "ผู้ใช้ all departments ต้องมีกลุ่ม group_od19_department_all",
        )
        vehicles = self.env["fleet.vehicle"].with_user(user).search([])
        self.assertIn(self.vehicle_a, vehicles)
        self.assertIn(self.vehicle_b, vehicles)
        self.assertIn(self.vehicle_none, vehicles)
