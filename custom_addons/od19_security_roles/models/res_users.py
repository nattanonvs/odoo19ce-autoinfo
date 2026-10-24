# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import Command, api, fields, models

# ฟิลด์บน res.users ที่เมื่อเปลี่ยนแล้วแผนก mirror อาจเปลี่ยนตาม
# (เปลี่ยนบริษัทหลัก/บริษัทที่สังกัด => พนักงานที่ผูกด้วยเปลี่ยน)
_OD19_DEPARTMENT_TRIGGER_FIELDS = {"company_id", "company_ids"}

# context flag กันการเรียกซ้ำเมื่อตัว sync เขียนค่ากลับเข้า res.users
_SKIP_SYNC_CONTEXT_KEY = "od19_skip_department_sync"


def _od19_explicit_group_ids(vals):
    """กลุ่มที่ผู้เรียกส่งมาตรง ๆ ใน ``vals['group_ids']``

    รองรับทั้ง x2many command (``Command.set/link/unlink/clear``) และ id เปล่า ๆ
    เพื่อให้รู้ว่าผู้เรียก "ตั้งใจกำหนดกลุ่มเอง" หรือปล่อยให้ระบบใช้ค่า default
    """
    result = set()
    for command in vals.get("group_ids") or []:
        if not isinstance(command, (list, tuple)):
            result.add(command)
            continue
        code = command[0]
        if code == Command.SET:
            result = set(command[2] or [])
        elif code == Command.LINK:
            result.add(command[1])
        elif code == Command.UNLINK:
            result.discard(command[1])
        elif code == Command.CLEAR:
            result = set()
    return result


class ResUsers(models.Model):
    _inherit = "res.users"

    od19_department_id = fields.Many2one(
        "hr.department",
        string="Department",
        index=True,
        copy=False,
        help="แผนกที่ใช้กำหนดขอบเขตการเข้าถึงข้อมูลของผู้ใช้นี้ "
        "(mirror มาจากแผนกของพนักงานที่ผูกกับผู้ใช้)",
    )
    od19_department_code = fields.Char(
        string="Department Code",
        related="od19_department_id.code",
        readonly=True,
    )

    # ------------------------------------------------------------------
    # กลไก mirror แผนก (D3: hr.employee เป็นแหล่งความจริง)
    # ------------------------------------------------------------------
    def _od19_get_employee(self):
        """คืนพนักงานที่ผูกกับผู้ใช้รายนี้ในบริษัทที่เกี่ยวข้อง

        ใช้ sudo() เพื่อไม่ให้สิทธิ์การอ่าน hr.employee ของผู้ใช้ทั่วไป
        ทำให้การ sync ล้มเหลว (พนักงานเป็นข้อมูลอ้างอิง ไม่ใช่ข้อมูลลับ)
        """
        self.ensure_one()
        companies = (self.company_id | self.company_ids).ids
        employees = (
            self.env["hr.employee"]
            .sudo()
            .with_context(active_test=False)
            .search([("user_id", "=", self.id), ("company_id", "in", companies)])
        )
        # ให้ความสำคัญกับพนักงานของบริษัทหลักก่อน ถ้าไม่มีจึงใช้รายแรก
        return employees.filtered(lambda emp: emp.company_id == self.company_id)[:1] or employees[:1]

    def _od19_department_from_employee(self):
        """แผนกที่ควรถูก mirror มาจากพนักงานที่ผูกอยู่"""
        self.ensure_one()
        return self._od19_get_employee().department_id

    def _od19_sync_department_from_employee(self):
        """ปรับ od19_department_id ให้ตรงกับแผนกของพนักงาน (idempotent)"""
        for user in self:
            department = user._od19_department_from_employee()
            if user.od19_department_id != department:
                user.with_context(**{_SKIP_SYNC_CONTEXT_KEY: True}).write(
                    {"od19_department_id": department.id or False}
                )

    @api.model
    def _od19_cron_sync_all_departments(self):
        """cron รายวัน: กวาดปรับแผนก mirror ให้ตรงกับพนักงาน (กันข้อมูลเพี้ยน)"""
        users = (
            self.with_context(active_test=False)
            .search(
                [
                    "|",
                    ("od19_department_id", "!=", False),
                    ("employee_ids", "!=", False),
                ]
            )
        )
        users._od19_sync_department_from_employee()

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """ให้กลุ่มที่ผู้เรียกส่งมาตรง ๆ ชนะ default role ของ OCA

        ``base_user_role`` ใส่ role เริ่มต้น (พนักงานทั่วไป) ให้ผู้ใช้ใหม่ทุกคน
        แล้ว ``set_groups_from_roles()`` จะ "แทนที่" ``group_ids`` ด้วยกลุ่มที่มา
        จาก role เท่านั้น ทำให้กลุ่มที่ผู้เรียกส่งมา (เช่น portal user ที่ต้องอยู่
        กลุ่ม ``base.group_portal``) ถูกลบทิ้งและผู้ใช้นั้นกลายเป็นพนักงานภายใน

        ถ้าผู้เรียกส่ง ``group_ids`` มาแบบไม่ว่าง แปลว่าตั้งใจกำหนดสิทธิ์เอง
        เราจึงไม่ผูก default role เพื่อรักษากลุ่มที่ระบุไว้
        """
        vals_list = [dict(vals) for vals in vals_list]
        for vals in vals_list:
            if "role_line_ids" not in vals and _od19_explicit_group_ids(vals):
                vals["role_line_ids"] = [Command.clear()]
        users = super().create(vals_list)
        users._od19_sync_department_from_employee()
        return users

    def write(self, vals):
        res = super().write(vals)
        if (
            not self.env.context.get(_SKIP_SYNC_CONTEXT_KEY)
            and _OD19_DEPARTMENT_TRIGGER_FIELDS & set(vals)
        ):
            self._od19_sync_department_from_employee()
        return res
