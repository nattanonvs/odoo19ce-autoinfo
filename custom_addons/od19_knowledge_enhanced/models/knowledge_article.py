from odoo import api, fields, models


class DocumentPage(models.Model):
    _inherit = "document.page"

    category = fields.Selection(
        [
            ("procedure", "Procedure"),
            ("troubleshooting", "Troubleshooting"),
            ("faq", "FAQ"),
            ("general", "General"),
        ],
        string="Knowledge Category",
        default="general",
        tracking=True,
    )
    keywords = fields.Char("Keywords", help="Comma-separated keywords")
    is_emergency = fields.Boolean("Emergency", default=False, tracking=True)
    ticket_id = fields.Many2one(
        "helpdesk.ticket", string="Source Ticket", ondelete="set null"
    )

    # Stored plain-text version for search performance (uses document.page content)
    content_plain = fields.Text(
        "Content (plain text)", compute="_compute_content_plain", store=True
    )

    @api.depends("content")
    def _compute_content_plain(self):
        from odoo.tools import html2plaintext

        for rec in self:
            rec.content_plain = html2plaintext(rec.content or "")

    def action_create_from_ticket(self, ticket):
        """Create a knowledge article from a resolved helpdesk ticket."""
        self.ensure_one()
        if not ticket:
            return
        vals = {
            "name": ticket.name,
            "content": ticket.resolution or ticket.description or "",
            "category": "troubleshooting",
            "keywords": ticket.name,
            "ticket_id": ticket.id,
        }
        return self.create(vals)

    @api.model
    def search_emergency(self, query):
        """Search emergency articles matching the query."""
        domain = [("is_emergency", "=", True)]
        if query:
            domain += [
                "|",
                ("name", "ilike", query),
                ("keywords", "ilike", query),
            ]
        return self.search(domain)
