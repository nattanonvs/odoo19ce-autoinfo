from odoo import api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        tracking=True,
        index=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "department_id" not in res or not res.get("department_id"):
            user = self.env["res.users"].browse(self.env.uid)
            if user.employee_id and user.employee_id.department_id:
                res["department_id"] = user.employee_id.department_id.id
        return res

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            department_id = vals.get("department_id")
            if department_id:
                department = self.env["hr.department"].browse(department_id)
                if department and department.pr_sequence_id:
                    seq_date = None
                    if vals.get("date_start"):
                        seq_date = fields.Date.to_date(vals["date_start"])
                    vals["name"] = (
                        department.pr_sequence_id.next_by_id(
                            sequence_date=seq_date
                        )
                        or "/"
                    )
        return super().create(vals)

    def write(self, vals):
        res = super().write(vals)
        if "department_id" in vals:
            for rec in self:
                if rec.name in ("New", "/") and rec.department_id:
                    if rec.department_id.pr_sequence_id:
                        seq_date = rec.date_start or None
                        rec.name = (
                            rec.department_id.pr_sequence_id.next_by_id(
                                sequence_date=seq_date
                            )
                            or "/"
                        )
        return res
