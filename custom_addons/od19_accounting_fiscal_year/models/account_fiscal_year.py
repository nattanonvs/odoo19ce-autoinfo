from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountFiscalYear(models.Model):
    _name = "account.fiscal.year"
    _description = "Fiscal Year"
    _order = "date_from desc"

    name = fields.Char(string="Fiscal Year", required=True)
    date_from = fields.Date(string="Start Date", required=True)
    date_to = fields.Date(string="End Date", required=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("open", "Open"),
            ("closed", "Closed"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    note = fields.Text(string="Notes")

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for fy in self:
            if fy.date_from > fy.date_to:
                raise ValidationError(
                    _("Start date must be before end date.")
                )

    @api.constrains("date_from", "date_to", "company_id")
    def _check_overlap(self):
        for fy in self:
            overlapping = self.search(
                [
                    ("id", "!=", fy.id),
                    ("company_id", "=", fy.company_id.id),
                    ("date_from", "<=", fy.date_to),
                    ("date_to", ">=", fy.date_from),
                ],
                limit=1,
            )
            if overlapping:
                raise ValidationError(
                    _("Fiscal years cannot overlap.")
                )

    def action_open(self):
        for fy in self:
            if fy.state != "draft":
                continue
            fy.state = "open"

    def action_close(self):
        for fy in self:
            if fy.state != "open":
                continue
            fy.state = "closed"

    def action_draft(self):
        for fy in self:
            if fy.state != "closed":
                continue
            fy.state = "draft"
