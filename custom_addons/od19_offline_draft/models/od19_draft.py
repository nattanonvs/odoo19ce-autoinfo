# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

DRAFT_PAYLOAD_VERSION = 1
DRAFT_TTL_DAYS = 7
DRAFT_DEBOUNCE_MS = 2000
DRAFT_MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024  # 5 MB
DEFAULT_ENABLED_MODELS = (
    "sale.order",
    "purchase.order",
    "purchase.request",
    "account.analytic.line",
)


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

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------
    @api.model
    def _get_enabled_models(self):
        enabled = set(DEFAULT_ENABLED_MODELS)
        for model_name, model in self.env.registry.models.items():
            if getattr(model, "_od19_draft_enabled", False):
                enabled.add(model_name)
        return tuple(sorted(enabled))

    @api.model
    def _validate_model(self, model_name):
        if model_name not in self._get_enabled_models():
            raise UserError(
                _("Model '%s' is not enabled for offline drafts.") % model_name
            )

    @api.model
    def _get_client_config(self):
        return {
            "enabled_models": list(self._get_enabled_models()),
            "debounce_ms": DRAFT_DEBOUNCE_MS,
            "ttl_days": DRAFT_TTL_DAYS,
            "max_attachment_size": DRAFT_MAX_ATTACHMENT_SIZE,
            "payload_version": DRAFT_PAYLOAD_VERSION,
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    @api.model
    def _active_domain(self, model_name, res_id):
        return [
            ("model_name", "=", model_name),
            ("res_id", "=", res_id or 0),
            ("user_id", "=", self.env.user.id),
            ("state", "=", "active"),
        ]

    @api.model
    def upsert_draft(self, model_name, res_id, payload, payload_version=None):
        self._validate_model(model_name)
        values = {
            "model_name": model_name,
            "res_id": res_id or 0,
            "user_id": self.env.user.id,
            "company_id": self.env.company.id,
            "payload": payload or {},
            "payload_version": payload_version or DRAFT_PAYLOAD_VERSION,
            "expires_at": fields.Datetime.now() + timedelta(days=DRAFT_TTL_DAYS),
        }
        draft = self.sudo().search(self._active_domain(model_name, res_id), limit=1)
        if draft:
            draft.write(values)
        else:
            draft = self.sudo().create(values)
        return {
            "id": draft.id,
            "updated_at": fields.Datetime.to_string(draft.write_date),
        }

    @api.model
    def fetch_draft(self, model_name, res_id):
        draft = self.sudo().search(self._active_domain(model_name, res_id), limit=1)
        if not draft:
            return False
        if draft.payload_version != DRAFT_PAYLOAD_VERSION:
            # เก็บร่างเดิมไว้เป็น expired เพื่อการตรวจสอบ ไม่ลบข้อมูลผู้ใช้แบบเงียบ
            draft.write({"state": "expired"})
            return False
        return {
            "id": draft.id,
            "payload": draft.payload,
            "payload_version": draft.payload_version,
            "updated_at": fields.Datetime.to_string(draft.write_date),
            "expires_at": (
                fields.Datetime.to_string(draft.expires_at) if draft.expires_at else False
            ),
            "attachment_ids": draft._get_attachment_ids(),
        }

    def _get_attachment_ids(self):
        self.ensure_one()
        return (
            self.env["ir.attachment"]
            .sudo()
            .search([("res_model", "=", self._name), ("res_id", "=", self.id)])
            .ids
        )

    @api.model
    def discard_draft(self, model_name, res_id):
        self.sudo().search(self._active_domain(model_name, res_id)).unlink()
        return True

    @api.model
    def mark_applied(self, model_name, res_id):
        drafts = self.sudo().search(self._active_domain(model_name, res_id))
        drafts.write({"state": "applied"})
        drafts.unlink()
        return True

    @api.model
    def _cron_expire_drafts(self):
        now = fields.Datetime.now()
        expired = self.sudo().search(
            [
                ("state", "=", "active"),
                ("expires_at", "!=", False),
                ("expires_at", "<", now),
            ]
        )
        count = len(expired)
        expired.unlink()
        # ร่างที่ถูกทำเป็น expired (เช่น payload version เก่า) เก็บไว้ตรวจสอบ
        # ชั่วคราวแล้วลบทิ้งเมื่อพ้นช่วงผ่อนผัน เพื่อไม่ให้ค้างถาวร
        self.sudo().search(
            [
                ("state", "=", "expired"),
                ("write_date", "<", now - timedelta(days=DRAFT_TTL_DAYS)),
            ]
        ).unlink()
        return count
