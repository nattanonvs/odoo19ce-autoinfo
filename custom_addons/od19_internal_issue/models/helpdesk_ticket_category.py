from odoo import fields, models


class HelpdeskTicketCategory(models.Model):
    _inherit = "helpdesk.ticket.category"

    default_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Default Assignee",
        help="User automatically assigned when a ticket uses this category.",
        index=True,
    )
    default_team_id = fields.Many2one(
        comodel_name="helpdesk.ticket.team",
        string="Default Team",
        help="Team automatically assigned when a ticket uses this category.",
        index=True,
    )
