from odoo import fields, models


class HelpdeskTicketTeam(models.Model):
    _inherit = "helpdesk.ticket.team"

    team_type = fields.Selection(
        selection=[
            ("internal", "Internal IT Helpdesk"),
            ("customer_service", "Customer Sales Services"),
        ],
        string="Team Type",
        default="internal",
        required=True,
        help=(
            "Internal: tickets from employees (IT support, no billing).\n"
            "Customer Service: tickets from customers that generate revenue "
            "(repair, installation, maintenance, warranty)."
        ),
    )
