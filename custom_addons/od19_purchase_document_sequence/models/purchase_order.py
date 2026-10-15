from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        tracking=True,
        index=True,
    )
    od19_purchase_type = fields.Selection(
        [
            ("local", "Local"),
            ("indent", "Indent/Import"),
            ("bulk", "Bulk"),
        ],
        string="Purchase Type",
        default="local",
        required=True,
        tracking=True,
        help="Local uses PB/PT/PI/PF/PF-D sequences. "
        "Indent uses IB/IT/II sequences. Bulk uses BULK sequence.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "department_id" not in res or not res.get("department_id"):
            user = self.env["res.users"].browse(self.env.uid)
            if user.employee_id and user.employee_id.department_id:
                res["department_id"] = user.employee_id.department_id.id
        return res

    def _get_purchase_sequence(self, department=None):
        """Return the appropriate sequence based on purchase type and department."""
        self.ensure_one()
        department = department or self.department_id
        if not department:
            return False
        if self.od19_purchase_type == "indent":
            return department.po_indent_sequence_id or department.po_sequence_id
        if self.od19_purchase_type == "bulk":
            return self.env.ref(
                "od19_purchase_document_sequence.seq_purchase_order_bulk",
                raise_if_not_found=False,
            )
        return department.po_sequence_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") != "New":
                continue
            department_id = vals.get("department_id")
            if not department_id:
                continue
            department = self.env["hr.department"].browse(department_id)
            purchase_type = vals.get("od19_purchase_type", "local")
            if purchase_type == "indent":
                sequence = department.po_indent_sequence_id or department.po_sequence_id
            elif purchase_type == "bulk":
                sequence = self.env.ref(
                    "od19_purchase_document_sequence.seq_purchase_order_bulk",
                    raise_if_not_found=False,
                )
            else:
                sequence = department.po_sequence_id
            if sequence:
                seq_date = None
                if vals.get("date_order"):
                    seq_date = fields.Datetime.context_timestamp(
                        self, fields.Datetime.to_datetime(vals["date_order"])
                    )
                vals["name"] = sequence.next_by_id(sequence_date=seq_date) or "/"
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if "department_id" in vals or "od19_purchase_type" in vals:
            for rec in self:
                if rec.name in ("New", "/"):
                    sequence = rec._get_purchase_sequence()
                    if sequence:
                        seq_date = (
                            fields.Datetime.context_timestamp(rec, rec.date_order)
                            if rec.date_order
                            else None
                        )
                        rec.name = (
                            sequence.next_by_id(sequence_date=seq_date) or "/"
                        )
        return res
