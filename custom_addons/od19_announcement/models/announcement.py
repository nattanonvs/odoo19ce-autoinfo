from datetime import date, timedelta

from odoo import api, fields, models


class Announcement(models.Model):
    _name = "announcement"
    _description = "Announcement"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char("Title", required=True, tracking=True)
    body = fields.Html("Content", sanitize_style=True, required=True)
    announcement_type = fields.Selection(
        [
            ("info", "Info"),
            ("warning", "Warning"),
            ("mandatory", "Mandatory"),
        ],
        string="Type",
        default="info",
        required=True,
        tracking=True,
    )
    target_type = fields.Selection(
        [
            ("company", "Company-wide"),
            ("department", "Department"),
            ("role", "Role"),
        ],
        string="Target",
        default="company",
        required=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
    )
    role_id = fields.Many2one(
        "res.users.role",
        string="Role",
    )
    expiry_date = fields.Date("Expiry Date")
    published = fields.Boolean("Published", default=False, tracking=True)
    published_date = fields.Date("Published Date", readonly=True)
    author_id = fields.Many2one(
        "res.users",
        string="Author",
        default=lambda self: self.env.user,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    read_ids = fields.One2many(
        "announcement.read", "announcement_id", string="Read Receipts"
    )
    read_count = fields.Integer(
        "Read Count", compute="_compute_read_count", store=True
    )

    @api.depends("read_ids")
    def _compute_read_count(self):
        for rec in self:
            rec.read_count = len(rec.read_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("published"):
                vals["published_date"] = fields.Date.context_today(self)
        recs = super().create(vals_list)
        for rec in recs:
            if rec.published and rec.announcement_type in ("warning", "mandatory"):
                rec._notify_targets()
        return recs

    def write(self, vals):
        was_published = {rec.id: rec.published for rec in self}
        if vals.get("published"):
            vals.setdefault("published_date", fields.Date.context_today(self))
        res = super().write(vals)
        for rec in self:
            if (
                rec.published
                and not was_published.get(rec.id)
                and rec.announcement_type in ("warning", "mandatory")
            ):
                rec._notify_targets()
        return res

    def _get_target_users(self):
        self.ensure_one()
        User = self.env["res.users"]
        if self.target_type == "company":
            return User.search([("company_ids", "in", self.company_id.id)])
        if self.target_type == "department":
            employees = self.env["hr.employee"].search(
                [("department_id", "=", self.department_id.id)]
            )
            return employees.mapped("user_id")
        if self.target_type == "role" and self.role_id:
            return self.role_id.line_ids.mapped("user_id")
        return User

    def _notify_targets(self):
        self.ensure_one()
        users = self._get_target_users()
        partners = users.mapped("partner_id")
        if not partners:
            return
        self.env["notification.service"].notify(
            partners=partners,
            message=self.body,
            event="announcement",
            subject=self.name,
        )

    def action_mark_as_read(self):
        self.ensure_one()
        existing = self.env["announcement.read"].search(
            [
                ("announcement_id", "=", self.id),
                ("user_id", "=", self.env.user.id),
            ],
            limit=1,
        )
        if not existing:
            self.env["announcement.read"].create(
                {"announcement_id": self.id, "user_id": self.env.user.id}
            )
        return True

    def action_publish(self):
        self.write({"published": True})

    def action_unpublish(self):
        self.write({"published": False})

    @api.model
    def _cron_unpublish_expired(self):
        today = date.today()
        expired = self.search(
            [("published", "=", True), ("expiry_date", "<", today)]
        )
        expired.write({"published": False})
