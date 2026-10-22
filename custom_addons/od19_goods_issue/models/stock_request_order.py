# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class StockRequestOrder(models.Model):
    _inherit = "stock.request.order"

    od19_issue_type_id = fields.Many2one(
        comodel_name="od19.goods.issue.type",
        string="ประเภทการเบิก / Issue Type",
        tracking=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="แผนกที่ขอเบิก / Requesting Department",
        compute="_compute_department_id",
        store=True,
        readonly=False,
        index=True,
        tracking=True,
    )
    od19_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="ผู้ขอเบิก / Requested By (Employee)",
        compute="_compute_od19_employee_id",
        store=True,
        readonly=False,
        tracking=True,
    )
    od19_job_id = fields.Many2one(
        comodel_name="project.project",
        string="งาน/โครงการ / Job",
        tracking=True,
    )
    od19_reason = fields.Text(
        string="เหตุผลการเบิก / Issue Reason",
        tracking=True,
    )

    @api.model
    def _od19_employee_for_user(self, user):
        """Return ``user``'s employee with the HR-restricted fields readable.

        ``hr.employee.department_id`` is inherited from ``hr.version`` through
        ``version_id``, and ``version_id`` is restricted to
        ``hr.group_hr_user``. A Goods Issue requester is typically not an HR
        officer, so reading the department on a plain record would raise an
        AccessError. The lookup is therefore performed with ``sudo()``.
        """
        if not user:
            return self.env["hr.employee"]
        return user.sudo().employee_id

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        employee = self._od19_employee_for_user(self.env.user)
        if employee:
            if not res.get("department_id") and employee.department_id:
                res["department_id"] = employee.department_id.id
            if not res.get("od19_employee_id"):
                res["od19_employee_id"] = employee.id
        return res

    @api.depends("requested_by")
    def _compute_department_id(self):
        for rec in self:
            employee = self._od19_employee_for_user(rec.requested_by)
            rec.department_id = employee.department_id if employee else False

    @api.depends("requested_by")
    def _compute_od19_employee_id(self):
        for rec in self:
            rec.od19_employee_id = self._od19_employee_for_user(rec.requested_by)

    @api.model
    def _od19_get_goods_issue_sequence(self, department=False):
        """Return (creating it on demand) the Goods Issue sequence to use.

        A separate sequence is kept per department so that each department has
        its own running number (e.g. GI/IA/00001 and GI/BA/00001). When no
        department is available the shared fallback sequence is used.
        """
        sequence_model = self.env["ir.sequence"].sudo()
        if department:
            dept_code = (department.code or department.name or "")[:3].upper()
            code = "od19.goods.issue.%s" % department.id
        else:
            dept_code = False
            code = "od19.goods.issue"
        dept_code = dept_code or "GEN"
        sequence = sequence_model.search([("code", "=", code)], limit=1)
        if not sequence:
            sequence = sequence_model.create(
                {
                    "name": "Goods Issue %s" % dept_code,
                    "code": code,
                    "prefix": "GI/%s/" % dept_code,
                    "padding": 5,
                    "company_id": False,
                }
            )
        return sequence

    @api.model
    def _od19_resolve_department(self, vals):
        """Resolve the hr.department used for Goods Issue numbering."""
        department_id = vals.get("department_id")
        if department_id:
            return self.env["hr.department"].browse(department_id)
        requested_by_id = vals.get("requested_by")
        user = (
            self.env["res.users"].browse(requested_by_id)
            if requested_by_id
            else self.env.user
        )
        employee = self._od19_employee_for_user(user)
        if employee and employee.department_id:
            return employee.department_id
        return self.env["hr.department"]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Only replace an empty name; OCA's own create() would otherwise fill
            # it from the shared "stock.request.order" sequence.
            if not vals.get("name") or vals.get("name") == "/":
                department = self._od19_resolve_department(vals)
                sequence = self._od19_get_goods_issue_sequence(department)
                vals["name"] = sequence.next_by_id()
        return super().create(vals_list)
