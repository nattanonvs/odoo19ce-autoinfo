import re

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        tracking=True,
        index=True,
    )
    parent_ids = fields.One2many(
        "quotation.revision.parent",
        "sale_order_id",
        string="Revision History",
    )
    revision_count = fields.Integer(
        string="# of Revision",
        compute="_compute_revision_count",
        readonly=True,
    )
    child_ids = fields.One2many(
        "quotation.revision.parent",
        "parent_id",
        string="Child Revisions",
    )
    child_count = fields.Integer(
        string="# of Child",
        compute="_compute_child_count",
        readonly=True,
    )

    @api.depends("parent_ids")
    def _compute_revision_count(self):
        for order in self:
            order.revision_count = len(order.parent_ids)

    @api.depends("child_ids")
    def _compute_child_count(self):
        for order in self:
            order.child_count = len(order.child_ids)

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
        if vals.get("name", _("New")) == _("New"):
            department_id = vals.get("department_id")
            if department_id:
                department = self.env["hr.department"].browse(department_id)
                if department and department.quotation_sequence_id:
                    seq_date = None
                    if vals.get("date_order"):
                        seq_date = fields.Datetime.context_timestamp(
                            self, fields.Datetime.to_datetime(vals["date_order"])
                        )
                    vals["name"] = (
                        department.quotation_sequence_id.next_by_id(
                            sequence_date=seq_date
                        )
                        or "/"
                    )
        return super().create(vals)

    def write(self, vals):
        res = super().write(vals)
        if "department_id" in vals:
            for rec in self:
                if rec.name in (_("New"), "/") and rec.department_id:
                    if rec.department_id.quotation_sequence_id:
                        seq_date = (
                            fields.Datetime.context_timestamp(rec, rec.date_order)
                            if rec.date_order
                            else None
                        )
                        rec.name = (
                            rec.department_id.quotation_sequence_id.next_by_id(
                                sequence_date=seq_date
                            )
                            or "/"
                        )
        return res

    def action_create_revision(self):
        """Open the revision confirmation wizard."""
        self.ensure_one()
        return {
            "name": _("Quotation Revision Confirmation"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "sale.order.revision.wizard",
            "target": "new",
            "context": {"sale_id": self.id},
        }

    def action_view_revisions(self):
        """View parent revisions of this quotation."""
        self.ensure_one()
        action = self.env.ref("sale.action_quotations_with_onboarding")
        return {
            "name": action.name,
            "type": action.type,
            "view_mode": action.view_mode,
            "res_model": action.res_model,
            "target": action.target,
            "help": action.help,
            "domain": [
                ("id", "in", self.parent_ids.mapped("parent_id").mapped("id"))
            ],
        }

    def action_view_child_revisions(self):
        """View child revisions of this quotation."""
        self.ensure_one()
        action = self.env.ref("sale.action_quotations_with_onboarding")
        return {
            "name": action.name,
            "type": action.type,
            "view_mode": action.view_mode,
            "res_model": action.res_model,
            "target": action.target,
            "help": action.help,
            "domain": [
                ("id", "in", self.child_ids.mapped("sale_order_id").mapped("id"))
            ],
        }

    @api.model
    def _generate_revision_name(self, base_name, revision_number):
        """Generate a revision name by appending /R01, /R02, etc.

        If the name already ends with /RNN, increment it.
        Otherwise append /R01.
        """
        match = re.search(r"/R(\d+)$", base_name)
        if match:
            base = base_name[: match.start()]
        else:
            base = base_name
        return f"{base}/R{revision_number:02d}"
