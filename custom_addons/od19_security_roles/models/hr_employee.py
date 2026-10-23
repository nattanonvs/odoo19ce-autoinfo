# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, models

# ฟิลด์บน hr.employee ที่เมื่อเปลี่ยนแล้วต้อง sync แผนกกลับไปยังผู้ใช้ที่ผูกอยู่
_SYNC_TRIGGER_FIELDS = {"department_id", "user_id"}


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _od19_resync_users(self, previous_users):
        """sync แผนกไปยังผู้ใช้ทั้งที่ผูกอยู่เดิมและผูกใหม่"""
        users = previous_users | self.mapped("user_id")
        users._od19_sync_department_from_employee()

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        employees.mapped("user_id")._od19_sync_department_from_employee()
        return employees

    def write(self, vals):
        triggers = _SYNC_TRIGGER_FIELDS & set(vals)
        previous_users = self.env["res.users"]
        if triggers:
            previous_users = self.mapped("user_id")
        res = super().write(vals)
        if triggers:
            self._od19_resync_users(previous_users)
        return res
