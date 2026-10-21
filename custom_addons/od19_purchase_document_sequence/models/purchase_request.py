from odoo import api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

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
