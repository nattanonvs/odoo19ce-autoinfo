from odoo import fields, models


class Od19SalesProject(models.Model):
    _name = "od19.sales.project"
    _description = "Sales Project Context"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    project_owner_id = fields.Many2one("res.partner", required=True, tracking=True)
    contractor_ids = fields.Many2many("res.partner", string="Known Contractors")
    active = fields.Boolean(default=True)
