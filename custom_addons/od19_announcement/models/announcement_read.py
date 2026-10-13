from odoo import fields, models


class AnnouncementRead(models.Model):
    _name = "announcement.read"
    _description = "Announcement Read Receipt"
    _rec_name = "announcement_id"

    announcement_id = fields.Many2one(
        "announcement",
        string="Announcement",
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Read by",
        required=True,
        default=lambda self: self.env.user,
    )
    read_date = fields.Datetime(
        "Read Date", default=fields.Datetime.now, readonly=True
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="announcement_id.company_id",
        store=True,
    )
