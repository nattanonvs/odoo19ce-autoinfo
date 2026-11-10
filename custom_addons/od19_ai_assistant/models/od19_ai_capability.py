# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Capability gate + safe draft creation + audit logging.

Two modes exist: ``read_only`` (A, default) and ``read_draft`` (B, opt-in).
Draft creation always uses the *current user's* rights (never ``sudo``), only
for whitelisted models, and always forces a non-posting ``draft`` state.
"""

import json
import logging

from odoo import api, models
from odoo.exceptions import UserError

from ..lib import orm_guard

_logger = logging.getLogger(__name__)

#: Sentinel prefix marking a tool result as a draft proposal (never a record).
DRAFT_MARKER = "__OD19_DRAFT__"

#: Secret-ish argument keys that must never reach the audit log.
REDACTED_KEYS = ("password", "api_key", "token", "secret", "key")

#: Substrings that mark an argument key as secret-ish even without separators.
REDACTED_SUBSTRINGS = (
    "password",
    "passwd",
    "secret",
    "token",
    "credential",
    "apikey",
    "api_key",
    "pwd",
)

#: Fields the AI may never set on a draft.
FORBIDDEN_FIELDS = frozenset(
    {
        "payment_state",
        "amount_residual",
        "amount_residual_signed",
        "reconciled",
    }
)


class Od19AiCapability(models.AbstractModel):
    _name = "od19.ai.capability"
    _description = "ชั้นควบคุมความสามารถของผู้ช่วย AI (OD19)"

    DRAFT_MODES = ("read_only", "read_draft")
    DEFAULT_DRAFT_MODELS = (
        "sale.order",
        "purchase.order",
        "account.move",
        "project.task",
        "mail.activity",
        "helpdesk.ticket",
        "crm.lead",
    )

    # ------------------------------------------------------------------
    # Mode resolution
    # ------------------------------------------------------------------
    @api.model
    def _param(self, key, default=None):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("od19_ai.%s" % key, default)
        )

    @api.model
    def system_mode(self):
        mode = self._param("capability_mode")
        return mode if mode in self.DRAFT_MODES else "read_only"

    @api.model
    def capability_mode(self, user=None):
        user = user or self.env.user
        mode = getattr(user, "od19_ai_capability_mode", None) or self.system_mode()
        return mode if mode in self.DRAFT_MODES else "read_only"

    @api.model
    def _draft_whitelist(self):
        raw = self._param("draft_models")
        names = [item.strip() for item in (raw or "").split(",") if item.strip()]
        if not names:
            names = list(self.DEFAULT_DRAFT_MODELS)
        return tuple(name for name in names if name in self.env)

    @api.model
    def can_draft(self, model_name=None):
        if self.capability_mode() != "read_draft":
            return False
        if not model_name:
            return True
        if model_name not in self._draft_whitelist():
            return False
        return self.env[model_name].has_access("create")

    # ------------------------------------------------------------------
    # Draft creation (2-step: preview -> confirm)
    # ------------------------------------------------------------------
    @api.model
    def preview_draft(self, model_name, values):
        if model_name not in self._draft_whitelist():
            raise UserError("โมเดล %s ไม่อยู่ในรายการที่อนุญาต" % model_name)
        cleaned = self._sanitize_values(model_name, values)
        return {
            "model": model_name,
            "model_label": self.env[model_name]._description or model_name,
            "values": {key: str(value) for key, value in cleaned.items()},
        }

    @api.model
    def create_draft(self, model_name, values):
        """Create a draft record with the current user's rights (never sudo)."""
        if not self.can_draft(model_name):
            raise UserError("โหมดปัจจุบันไม่อนุญาตให้สร้างเอกสารร่าง")
        cleaned = self._sanitize_values(model_name, values)
        record = self.env[model_name].create(cleaned)
        self.log_call(
            "draft_record",
            "draft",
            {"model": model_name, "values": cleaned},
            "สร้างร่าง %s" % record.display_name,
            success=True,
        )
        return record

    @api.model
    def _sanitize_values(self, model_name, values):
        model = self.env[model_name]
        cleaned = {}
        for field_name, value in (values or {}).items():
            if field_name in FORBIDDEN_FIELDS:
                raise orm_guard.OrmGuardError(
                    'ไม่อนุญาตให้ตั้งค่าฟิลด์ "%s"' % field_name
                )
            field = model._fields.get(field_name)
            if field is None or not field.store:
                raise orm_guard.OrmGuardError(
                    'ไม่พบฟิลด์ "%s" ในโมเดล %s' % (field_name, model_name)
                )
            if field.type in ("one2many", "many2many"):
                raise orm_guard.OrmGuardError(
                    'ไม่อนุญาตให้ตั้งค่าฟิลด์เชิงสัมพันธ์ "%s"' % field_name
                )
            cleaned[field_name] = value
        state_field = model._fields.get("state")
        if state_field and state_field.type == "selection":
            selection = [key for key, _label in (state_field.selection or [])]
            if "draft" in selection:
                cleaned["state"] = "draft"
        return cleaned

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------
    @api.model
    def _is_secret_key(self, key):
        """True when an argument key looks secret-ish (variant tolerant)."""
        lowered = str(key).lower()
        if lowered in REDACTED_KEYS or lowered in REDACTED_SUBSTRINGS:
            return True
        if any(marker in lowered for marker in REDACTED_SUBSTRINGS):
            return True
        # Split on separators so ``api_key`` matches the ``key`` token while
        # ``keyword`` does not.
        tokens = lowered.replace("-", "_").split("_")
        return any(token in REDACTED_KEYS for token in tokens)

    @api.model
    def _redact_arguments(self, arguments):
        if isinstance(arguments, dict):
            return {
                key: (
                    "***"
                    if self._is_secret_key(key)
                    else self._redact_arguments(value)
                )
                for key, value in arguments.items()
            }
        if isinstance(arguments, (list, tuple)):
            return [self._redact_arguments(item) for item in arguments]
        return arguments

    @api.model
    def log_call(
        self,
        tool_name,
        tool_kind,
        arguments,
        result,
        success=True,
        error="",
        duration_ms=0,
        chat=None,
    ):
        try:
            self.env["od19.ai.tool.log"].create(
                {
                    "user_id": self.env.user.id,
                    "chat_id": chat.id if chat else False,
                    "tool_name": tool_name,
                    "tool_kind": tool_kind or "read",
                    "arguments": self._redact_arguments(arguments),
                    "result_summary": (result or "")[:120],
                    "success": success,
                    "error_message": (error or "")[:200],
                    "duration_ms": duration_ms,
                }
            )
        except Exception:  # noqa: BLE001 - audit must never break a call
            _logger.warning("OD19 AI audit log failed", exc_info=True)


class Od19AiToolDraft(models.AbstractModel):
    """Registers the ``draft_record`` tool on the shared tool registry."""

    _inherit = "od19.ai.tool"

    @api.model
    def _draft_definitions(self):
        return [
            {
                "name": "draft_record",
                "model": None,
                "kind": "draft",
                "description": (
                    "เสนอสร้างเอกสารร่าง (ต้องได้รับการยืนยันจากผู้ใช้ก่อนสร้างจริง)"
                ),
                "arguments": {
                    "model": "ชื่อโมเดลที่อนุญาต",
                    "values": "ค่าฟิลด์ของเอกสารร่าง",
                },
            },
        ]

    @api.model
    def _run_draft_record(self, arguments):
        model_name = (arguments.get("model") or "").strip()
        values = arguments.get("values") or {}
        capability = self.env["od19.ai.capability"]
        if not capability.can_draft(model_name):
            return (
                "โหมดปัจจุบันไม่อนุญาตให้สร้างเอกสารร่าง "
                "หรือโมเดล %s ไม่อยู่ในรายการที่อนุญาต" % model_name
            )
        try:
            preview = capability.preview_draft(model_name, values)
        except orm_guard.OrmGuardError as exc:
            return str(exc)
        return DRAFT_MARKER + json.dumps(preview, ensure_ascii=False)
