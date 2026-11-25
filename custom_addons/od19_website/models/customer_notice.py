import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class Od19CustomerNotice(models.Model):
    """Notices published to customers inside the portal (``/my``).

    A lightweight, website-facing counterpart to ``od19_announcement``:
    staff announcements target employees, whereas these notices are shown to
    logged-in customers on their portal home page.
    """

    _name = "od19.customer.notice"
    _description = "Customer Notice"
    _order = "published_date desc, id desc"

    name = fields.Char(string="Title", required=True, translate=True)
    body = fields.Html(translate=True, sanitize_attributes=False)
    notice_type = fields.Selection(
        [
            ("info", "Information"),
            ("warning", "Warning"),
            ("mandatory", "Important"),
        ],
        string="Type",
        default="info",
        required=True,
    )
    published = fields.Boolean(default=False)
    published_date = fields.Date(readonly=True)
    expiry_date = fields.Date(help="Hide this notice automatically after this date.")
    website_url = fields.Char(
        string="Details link",
        help="Optional URL shown as a link under the notice.",
    )
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("published") and not vals.get("published_date"):
                vals["published_date"] = fields.Date.context_today(self)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("published") and not vals.get("published_date"):
            vals = dict(vals, published_date=fields.Date.context_today(self))
        return super().write(vals)

    @api.model
    def od19_published_notices(self, limit=5):
        """Return the notices a customer should currently see."""
        today = fields.Date.context_today(self)
        domain = [
            ("published", "=", True),
            ("active", "=", True),
            "|", ("expiry_date", "=", False), ("expiry_date", ">=", today),
        ]
        return self.sudo().search(domain, limit=limit)

    def action_publish(self):
        self.write({"published": True})

    def action_unpublish(self):
        self.write({"published": False})
