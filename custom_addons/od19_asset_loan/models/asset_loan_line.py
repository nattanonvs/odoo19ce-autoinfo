from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AssetLoanLine(models.Model):
    _name = "asset.loan.line"
    _description = "Asset Loan Line"
    _order = "loan_id, id"
    _check_company_auto = True

    loan_id = fields.Many2one(
        comodel_name="asset.loan",
        string="Loan",
        required=True,
        ondelete="cascade",
        index=True,
    )
    equipment_id = fields.Many2one(
        comodel_name="maintenance.equipment",
        string="Equipment",
        required=True,
        ondelete="restrict",
        index=True,
        check_company=True,
    )
    quantity = fields.Integer(
        string="Quantity",
        required=True,
        default=1,
    )
    returned_quantity = fields.Integer(
        string="Returned",
        default=0,
    )
    state = fields.Selection(
        related="loan_id.state",
        string="Status",
        store=True,
        index=True,
    )
    note = fields.Char(string="Note")
    asset_id = fields.Many2one(
        related="equipment_id.asset_id",
        string="Accounting Asset",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="loan_id.company_id",
        string="Company",
        store=True,
        index=True,
    )

    @api.constrains("quantity")
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise UserError(_("Quantity must be greater than zero."))

    @api.constrains("returned_quantity", "quantity")
    def _check_returned_quantity(self):
        for record in self:
            if record.returned_quantity > record.quantity:
                raise UserError(
                    _("Returned quantity cannot exceed the borrowed quantity.")
                )
