# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models

DRAFT_PAYLOAD_VERSION = 1


class Od19Draft(models.Model):
    _name = "od19.draft"
    _description = "Offline Draft / ร่างอัตโนมัติ"
    _rec_name = "name"
    _order = "write_date desc"

    name = fields.Char(compute="_compute_name", store=True, index=True)
    model_name = fields.Char(required=True, index=True)
    res_id = fields.Integer(default=0, index=True)
    user_id = fields.Many2one(
        "res.users",
        required=True,
        index=True,
        default=lambda self: self.env.user,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )
    payload = fields.Json()
    payload_version = fields.Integer(default=DRAFT_PAYLOAD_VERSION, required=True)
    state = fields.Selection(
        [
            ("active", "Active / ใช้งาน"),
            ("applied", "Applied / บันทึกจริงแล้ว"),
            ("discarded", "Discarded / ทิ้ง"),
            ("expired", "Expired / หมดอายุ"),
        ],
        default="active",
        required=True,
        index=True,
    )
    expires_at = fields.Datetime(index=True)

    @api.depends("model_name", "res_id")
    def _compute_name(self):
        for draft in self:
            suffix = draft.res_id or "new"
            draft.name = f"{draft.model_name}#{suffix}" if draft.model_name else "draft"

    def init(self):
        # Unique เฉพาะร่างที่ยัง active — 1 เรกคอร์ด : 1 ผู้ใช้ : 1 ร่างที่ใช้งานได้
        self._cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS od19_draft_active_uniq
            ON od19_draft (model_name, res_id, user_id)
            WHERE state = 'active'
            """
        )
