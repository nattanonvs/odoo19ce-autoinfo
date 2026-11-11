# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Generic Explorer — the layer that gives the assistant access to *every*
installed Odoo model the current user may read, without a bespoke tool.

The four meta-tools are bounded (``orm_guard``), read with the user's real
rights (no ``sudo``) and cached metadata-wise so repeated calls are free.
"""

import logging

from odoo import api, models, tools

from ..lib import orm_guard

_logger = logging.getLogger(__name__)

MAX_LIST_MODELS = 60
MAX_DESCRIBE_FIELDS = 60


class Od19AiToolGeneric(models.AbstractModel):
    _inherit = "od19.ai.tool"

    # ------------------------------------------------------------------
    # Registry contribution
    # ------------------------------------------------------------------
    @api.model
    def _generic_definitions(self):
        return [
            {
                "name": "list_models",
                "model": None,
                "kind": "read",
                "description": "ค้นหาโมเดล (ตาราง) ในระบบที่ผู้ใช้มีสิทธิ์อ่าน",
                "arguments": {
                    "keyword": "คำค้นหา (ไม่บังคับ)",
                    "limit": "จำนวนผลสูงสุด",
                },
            },
            {
                "name": "describe_model",
                "model": None,
                "kind": "read",
                "description": "ดูรายชื่อฟิลด์ของโมเดล (ชื่อ ชนิด ป้าย จำเป็น ความสัมพันธ์)",
                "arguments": {"model": "ชื่อโมเดล"},
            },
            {
                "name": "search_records",
                "model": None,
                "kind": "read",
                "description": "ค้นหาเรกคอร์ดจริงในโมเดลใดก็ได้ ด้วย domain/fields/limit",
                "arguments": {
                    "model": "ชื่อโมเดล",
                    "domain": "เงื่อนไข เช่น [['name','ilike','abc']]",
                    "fields": "รายชื่อฟิลด์ที่ต้องการ",
                    "limit": "จำนวนผลสูงสุด (ไม่เกิน 20)",
                    "order": "การเรียง (ไม่บังคับ)",
                },
            },
            {
                "name": "aggregate_records",
                "model": None,
                "kind": "read",
                "description": "สรุปผลด้วย _read_group (groupby/aggregates)",
                "arguments": {
                    "model": "ชื่อโมเดล",
                    "domain": "เงื่อนไข",
                    "groupby": "เช่น ['state'] หรือ ['create_date:month']",
                    "aggregates": "เช่น ['__count', 'amount_total:sum']",
                },
            },
        ]

    # ------------------------------------------------------------------
    # Metadata cache
    # ------------------------------------------------------------------
    @api.model
    @tools.ormcache("self.env.uid", cache="stable")
    def _readable_model_names(self):
        """Cached set of model names the current user may read.

        Uses ``ir.model.access._get_allowed_models`` (itself ormcached) instead
        of reading ``ir.model``, which plain users cannot access. The
        ``stable`` cache is cleared whenever the registry reloads.
        """
        allowed = self.env["ir.model.access"]._get_allowed_models("read")
        return frozenset(name for name in allowed if name in self.env)

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------
    @api.model
    def _run_list_models(self, arguments):
        keyword = (arguments.get("keyword") or "").strip().lower()
        limit = orm_guard.safe_limit(
            arguments.get("limit"), default=20, cap=MAX_LIST_MODELS
        )
        lines = []
        for model_name in sorted(self._readable_model_names()):
            label = self.env[model_name]._description or model_name
            if (
                keyword
                and keyword not in model_name.lower()
                and keyword not in (label or "").lower()
            ):
                continue
            lines.append("- %s: %s" % (model_name, label))
            if len(lines) >= limit:
                break
        return "\n".join(lines) or "ไม่พบโมเดล"

    @api.model
    def _run_describe_model(self, arguments):
        model_name = (arguments.get("model") or "").strip()
        try:
            orm_guard.check_model(self.env, model_name)
        except orm_guard.OrmGuardError as exc:
            return str(exc)
        model = self.env[model_name]
        lines = [
            "โมเดล %s — %s" % (model_name, model._description or model_name)
        ]
        shown = 0
        for field_name in sorted(model._fields):
            field = model._fields[field_name]
            if not field.store:
                continue
            if shown >= MAX_DESCRIBE_FIELDS:
                lines.append("... (แสดง %d ฟิลด์แรก)" % MAX_DESCRIBE_FIELDS)
                break
            parts = [field_name, field.type]
            if field.required:
                parts.append("required")
            relation = getattr(field, "comodel_name", None)
            if relation:
                parts.append("→ %s" % relation)
            label = field.string or field_name
            lines.append("- %s: %s" % (", ".join(parts), label))
            shown += 1
        return "\n".join(lines)

    @api.model
    def _run_search_records(self, arguments):
        model_name = (arguments.get("model") or "").strip()
        try:
            orm_guard.check_model(self.env, model_name)
            domain = orm_guard.validate_domain(
                self.env, model_name, arguments.get("domain")
            )
            fields_ = orm_guard.validate_fields(
                self.env, model_name, arguments.get("fields")
            )
            order = orm_guard.validate_order(
                self.env, model_name, arguments.get("order")
            )
        except orm_guard.OrmGuardError as exc:
            return str(exc)
        limit = orm_guard.safe_limit(arguments.get("limit"))
        offset = orm_guard.safe_offset(arguments.get("offset"))
        records = self.env[model_name].search_read(
            domain, fields_, limit=limit, offset=offset, order=order
        )
        return self._format_records(records, fields_)

    @api.model
    def _run_aggregate_records(self, arguments):
        model_name = (arguments.get("model") or "").strip()
        try:
            orm_guard.check_model(self.env, model_name)
            domain = orm_guard.validate_domain(
                self.env, model_name, arguments.get("domain")
            )
            groupby = orm_guard.validate_groupby(
                self.env, model_name, arguments.get("groupby")
            )
            aggregates = orm_guard.validate_aggregates(
                self.env, model_name, arguments.get("aggregates")
            )
        except orm_guard.OrmGuardError as exc:
            return str(exc)
        try:
            rows = self.env[model_name]._read_group(
                domain,
                groupby=groupby,
                aggregates=aggregates,
                limit=orm_guard.safe_limit(arguments.get("limit"), default=20),
            )
        except Exception as exc:  # noqa: BLE001 - report, never crash the chat
            _logger.warning("aggregate_records failed: %s", exc)
            return "สรุปข้อมูลไม่สำเร็จ: %s" % exc
        group_labels = self._groupby_labels(model_name, groupby)
        aggregate_labels = [
            self._aggregate_label(model_name, expr) for expr in aggregates
        ]
        return self._format_groups(rows, group_labels, aggregate_labels)

    # ------------------------------------------------------------------
    # Label helpers
    # ------------------------------------------------------------------
    @api.model
    def _groupby_labels(self, model_name, groupby):
        model = self.env[model_name]
        labels = []
        for item in groupby:
            field_name = item.split(":")[0]
            field = model._fields.get(field_name)
            labels.append(field.string if field else field_name)
        return labels

    @api.model
    def _aggregate_label(self, model_name, expr):
        if expr == "__count":
            return "จำนวน"
        field_name, func = expr.split(":")
        field = self.env[model_name]._fields.get(field_name)
        base = field.string if field else field_name
        return "%s (%s)" % (base, func)
