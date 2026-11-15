# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""นิยามการตรวจสุขภาพระบบ + ตัวตรวจในระบบ (in-process checkers).

แต่ละ ``od19.health.check`` คือ "หนึ่งการวัด" ที่รันได้จาก cron ภายใน Odoo
(ไม่ต้องพึ่งสคริปต์ภายนอก) แล้วบันทึกผลลง ``od19.health.result`` และเปิด/ปิด
``od19.health.incident`` ตามเกณฑ์ใน ``od19.health.rule``

การอ่านทั้งหมดเป็นแบบ *อ่านอย่างเดียว* (read-only) ตามนโยบายความปลอดภัย
"""

import logging
import os
import time

from odoo import api, fields, models, tools

from .od19_health_common import (
    CHECK_STATES,
    PARAM_ENABLED,
    PARAM_RETENTION_DAYS,
    SEVERITY_TO_STATE,
    STATE_TO_COLOR,
    human_bytes,
)

_logger = logging.getLogger(__name__)


class Od19HealthCheck(models.Model):
    """นิยามการตรวจสุขภาพระบบ 1 รายการ."""

    _name = "od19.health.check"
    _description = "การตรวจสุขภาพระบบ (OD19)"
    _order = "category, sequence, name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        required=True,
        index=True,
        help="รหัสอ้างอิงภายใน (machine key) เช่น cron_heartbeat",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    category = fields.Selection(
        [
            ("availability", "ความพร้อมใช้งาน"),
            ("queue", "คิว/งานเบื้องหลัง"),
            ("capacity", "ความจุ"),
            ("data", "ข้อมูล"),
            ("security", "ความปลอดภัย"),
        ],
        default="availability",
        required=True,
    )
    check_type = fields.Selection(
        [
            ("cron_heartbeat", "จังหวะการทำงานของ cron"),
            ("mail_queue", "คิวอีเมลค้างส่ง"),
            ("cron_backlog", "งาน cron เลยกำหนด"),
            ("db_size", "ขนาดฐานข้อมูล"),
            ("filestore_size", "ขนาด filestore"),
            ("session_store", "session store"),
            ("watchdog_heartbeat", "ความสดของตัวเฝ้าชั้นนอก"),
            ("custom", "กำหนดเอง (ใช้ค่าที่รายงานเข้ามา)"),
        ],
        default="custom",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True
    )
    interval_minutes = fields.Integer(
        default=15,
        help="ความถี่ที่ควรตรวจ (ใช้เป็นข้อมูลอ้างอิง; การรันจริงคุมด้วย cron)",
    )
    max_age_minutes = fields.Integer(
        default=30,
        help="อายุสูงสุดที่ยอมรับได้ (นาที) — ใช้กับการตรวจแบบจังหวะเวลา",
    )
    cron_id = fields.Many2one(
        "ir.cron", string="Cron ที่เฝ้า", help="ใช้กับการตรวจแบบจังหวะการทำงาน"
    )
    warning_threshold = fields.Float(digits=(16, 2), help="เกณฑ์เตือน (ค่าเริ่มต้นของ check)")
    critical_threshold = fields.Float(digits=(16, 2), help="เกณฑ์วิกฤต")

    rule_ids = fields.One2many("od19.health.rule", "check_id", string="เกณฑ์")
    result_ids = fields.One2many("od19.health.result", "check_id", string="ผลการตรวจ")
    rule_count = fields.Integer(compute="_compute_rule_count")

    # -------------------- สถานะล่าสุด (สำหรับ dashboard) --------------------
    last_run = fields.Datetime(readonly=True)
    last_state = fields.Selection(CHECK_STATES, default="unknown", readonly=True)
    last_state_color = fields.Char(compute="_compute_last_state_color")
    last_value = fields.Float(digits=(16, 2), readonly=True)
    last_value_label = fields.Char(readonly=True)
    last_message = fields.Char(readonly=True)
    last_result_age_minutes = fields.Integer(compute="_compute_last_result_age")

    _code_unique = models.Constraint(
        "unique(code)", "รหัสการตรวจต้องไม่ซ้ำกัน"
    )

    @api.depends("rule_ids")
    def _compute_rule_count(self):
        for check in self:
            check.rule_count = len(check.rule_ids)

    @api.depends("last_state")
    def _compute_last_state_color(self):
        for check in self:
            check.last_state_color = STATE_TO_COLOR.get(check.last_state, "grey")

    def _compute_last_result_age(self):
        now = fields.Datetime.now()
        for check in self:
            if not check.last_run:
                check.last_result_age_minutes = -1
                continue
            delta = now - check.last_run
            check.last_result_age_minutes = int(delta.total_seconds() // 60)

    # ------------------------------------------------------------------
    # ตัววัดแต่ละประเภท — คืน dict:
    #   {value, value_label, status, state, message, details}
    # ------------------------------------------------------------------
    def _measure(self):
        """เรียกตัววัดตาม ``check_type`` แล้วคืนผลการวัด (dict)."""
        self.ensure_one()
        method = getattr(self, "_measure_%s" % self.check_type, None)
        if method is None:
            return self._measure_custom()
        try:
            return method()
        except Exception as exc:  # noqa: BLE001 - การตรวจต้องไม่ทำให้ cron ล้ม
            _logger.warning("ตรวจ %s ล้มเหลว: %s", self.code, exc, exc_info=True)
            return {
                "value": 0.0,
                "value_label": "-",
                "status": "error",
                "state": "unknown",
                "message": "ตรวจไม่สำเร็จ: %s" % exc,
                "details": {"error": str(exc)},
            }

    def _measure_custom(self):
        """ประเภทกำหนดเอง: ใช้ค่าที่รายงานเข้ามาล่าสุด (ถ้ามี) หรือไม่ทราบ."""
        return {
            "value": self.last_value,
            "value_label": self.last_value_label or "-",
            "status": "reported",
            "state": "unknown",
            "message": "รอค่าที่รายงานเข้ามา",
            "details": {},
        }

    def _measure_cron_heartbeat(self):
        """ตรวจว่างาน cron ที่เฝ้ายังทำงานตามกำหนด (จังหวะไม่ขาดตอน)."""
        cron = self.cron_id
        if not cron:
            return self._state_from_threshold(
                0.0,
                "-",
                "ยังไม่ได้ผูก cron ที่ต้องเฝ้า",
                status="unknown",
                force_state="unknown",
            )
        if not cron.active:
            return {
                "value": -1.0,
                "value_label": "ปิดใช้งาน",
                "status": "inactive",
                "state": "critical",
                "message": "cron '%s' ถูกปิดใช้งาน" % cron.cron_name,
                "details": {"cron_id": cron.id},
            }
        now = fields.Datetime.now()
        reference = cron.lastcall or cron.create_date
        age_minutes = 99999.0 if not reference else (now - reference).total_seconds() / 60.0
        state = self._threshold_state(age_minutes)
        if state == "ok" and cron.nextcall and cron.nextcall < now:
            # เลยกำหนดแต่ยังไม่รัน — ถือว่าเริ่มผิดปกติ
            state = "warning"
        return {
            "value": round(age_minutes, 2),
            "value_label": "%.0f นาที" % age_minutes,
            "status": "ok" if state == "ok" else "stale",
            "state": state,
            "message": "cron '%s' รันล่าสุด %.0f นาทีที่แล้ว"
            % (cron.cron_name, age_minutes),
            "details": {
                "cron": cron.cron_name,
                "lastcall": str(cron.lastcall or ""),
                "nextcall": str(cron.nextcall or ""),
            },
        }

    def _measure_mail_queue(self):
        """นับอีเมลที่ยังค้างส่ง/ส่งไม่สำเร็จ."""
        Mail = self.env["mail.mail"].sudo()
        outgoing = Mail.search_count([("state", "=", "outgoing")])
        failed = Mail.search_count([("state", "=", "exception")])
        total = outgoing + failed
        state = self._threshold_state(total)
        return {
            "value": float(total),
            "value_label": "%d ฉบับ" % total,
            "status": "backlog",
            "state": state,
            "message": "อีเมลค้างส่ง %d (รอส่ง %d / ผิดพลาด %d)" % (total, outgoing, failed),
            "details": {"outgoing": outgoing, "failed": failed},
        }

    def _measure_cron_backlog(self):
        """นับงาน cron ที่เลยกำหนดแต่ยังไม่รัน (สัญญาณว่าคิวตัน)."""
        now = fields.Datetime.now()
        overdue = self.env["ir.cron"].sudo().search_count(
            [("active", "=", True), ("nextcall", "<", now)]
        )
        state = self._threshold_state(overdue)
        return {
            "value": float(overdue),
            "value_label": "%d งาน" % overdue,
            "status": "backlog",
            "state": state,
            "message": "งาน cron เลยกำหนด %d งาน" % overdue,
            "details": {"overdue": overdue},
        }

    def _measure_db_size(self):
        """วัดขนาดฐานข้อมูลปัจจุบัน (ไบต์)."""
        self.env.cr.execute("SELECT pg_database_size(current_database())")
        size = self.env.cr.fetchone()[0] or 0
        mb = size / (1024.0 * 1024.0)
        state = self._threshold_state(mb)
        return {
            "value": round(mb, 2),
            "value_label": human_bytes(size),
            "status": "measured",
            "state": state,
            "message": "ขนาดฐานข้อมูล %s" % human_bytes(size),
            "details": {"bytes": size, "megabytes": round(mb, 2)},
        }

    def _measure_filestore_size(self):
        """วัดขนาดโฟลเดอร์ filestore ของฐานข้อมูลปัจจุบัน."""
        path = self._filestore_path()
        size, file_count = self._dir_size(path)
        mb = size / (1024.0 * 1024.0)
        state = self._threshold_state(mb)
        return {
            "value": round(mb, 2),
            "value_label": human_bytes(size),
            "status": "measured",
            "state": state,
            "message": "filestore %s (%d ไฟล์)" % (human_bytes(size), file_count),
            "details": {"path": path, "bytes": size, "files": file_count},
        }

    def _measure_session_store(self):
        """วัดขนาดและจำนวนไฟล์ของ session store (ที่เก็บ session ของผู้ใช้)."""
        data_dir = tools.config.get("data_dir")
        path = os.path.join(data_dir, "sessions") if data_dir else ""
        size, file_count = self._dir_size(path)
        state = self._threshold_state(file_count)
        return {
            "value": float(file_count),
            "value_label": human_bytes(size),
            "status": "measured",
            "state": state,
            "message": "session store %d ไฟล์ (%s)" % (file_count, human_bytes(size)),
            "details": {"path": path, "bytes": size, "files": file_count},
        }

    def _measure_watchdog_heartbeat(self):
        """ตรวจว่าตัวเฝ้าชั้นนอก (P1) ยังรายงาน heartbeat ตามกำหนดหรือไม่."""
        summary = self.env["od19.health.watchdog"].sudo()._heartbeat_summary()
        if not summary["count"]:
            return self._state_from_threshold(
                0.0,
                "-",
                "ยังไม่มีตัวเฝ้าชั้นนอกที่ลงทะเบียน",
                status="unknown",
                force_state="unknown",
            )
        worst_age = float(summary["worst_age_minutes"])
        state = self._threshold_state(worst_age)
        if summary["stale_count"]:
            state = "critical" if state == "critical" else "warning"
        message = "ตัวเฝ้าชั้นนอก %d ตัว — heartbeat ล่าสุด %.0f นาทีที่แล้ว" % (
            summary["count"],
            worst_age,
        )
        if summary["never_seen"]:
            message += " (ยังไม่เคยรายงาน %d ตัว)" % summary["never_seen"]
        if summary["stale_codes"]:
            message += " | ขาดตอน: %s" % ", ".join(summary["stale_codes"])
        return {
            "value": worst_age,
            "value_label": "%.0f นาที" % worst_age,
            "status": "stale" if summary["stale_count"] else "ok",
            "state": state,
            "message": message,
            "details": summary,
        }

    # ------------------------------------------------------------------
    # ตัวช่วย
    # ------------------------------------------------------------------
    def _filestore_path(self):
        data_dir = tools.config.get("data_dir") or ""
        db_name = self.env.cr.dbname
        return os.path.join(data_dir, "filestore", db_name)

    @api.model
    def _dir_size(self, path):
        """คืน (ขนาดรวมเป็นไบต์, จำนวนไฟล์) ของโฟลเดอร์ — คืน (0,0) ถ้าไม่มี."""
        total = 0
        count = 0
        if not path or not os.path.isdir(path):
            return 0, 0
        for root, _dirs, files in os.walk(path):
            for name in files:
                try:
                    total += os.path.getsize(os.path.join(root, name))
                    count += 1
                except OSError:
                    continue
        return total, count

    def _threshold_state(self, value):
        """ตัดสินสถานะจากเกณฑ์ของ check (warning/critical threshold)."""
        if self.critical_threshold and value >= self.critical_threshold:
            return "critical"
        if self.warning_threshold and value >= self.warning_threshold:
            return "warning"
        return "ok"

    def _state_from_threshold(self, value, label, message, status="measured", force_state=None):
        return {
            "value": value,
            "value_label": label,
            "status": status,
            "state": force_state or self._threshold_state(value),
            "message": message,
            "details": {},
        }

    # ------------------------------------------------------------------
    # การรัน
    # ------------------------------------------------------------------
    def _process(self):
        """รันการตรวจ 1 รายการ: วัด -> บันทึกผล -> อัปเดตเหตุการณ์ -> แจ้งเตือน."""
        self.ensure_one()
        started = time.monotonic()
        measure = self._measure()
        rule = self.env["od19.health.rule"]._pick_rule(self, measure)
        if rule:
            state = rule.check_state
            severity = rule.severity
        else:
            state = measure.get("state") or "unknown"
            severity = "info" if state == "ok" else "warning"
        duration_ms = int((time.monotonic() - started) * 1000)

        self.env["od19.health.result"].create(
            {
                "check_id": self.id,
                "state": state,
                "severity": severity,
                "value": measure.get("value") or 0.0,
                "value_label": measure.get("value_label") or "",
                "message": measure.get("message") or "",
                "details": measure.get("details") or {},
                "duration_ms": duration_ms,
                "company_id": self.company_id.id,
            }
        )

        self.write(
            {
                "last_run": fields.Datetime.now(),
                "last_state": state,
                "last_value": measure.get("value") or 0.0,
                "last_value_label": measure.get("value_label") or "",
                "last_message": (measure.get("message") or "")[:255],
            }
        )

        incident = self.env["od19.health.incident"]
        if state in ("warning", "critical"):
            incident._open_or_update(self, rule, measure, state)
        else:
            incident._auto_resolve(self, state)
        return {"check": self.code, "state": state, "severity": severity}

    def action_run_now(self):
        """ปุ่มสั่งตรวจเดี๋ยวนี้จากหน้าจอ."""
        for check in self:
            check._process()
        return True

    @api.model
    def _cron_run_checks(self):
        """cron: รันการตรวจที่เปิดใช้ทั้งหมด (เรียงตามลำดับ)."""
        if not self._monitor_enabled():
            return
        checks = self.search([("active", "=", True)], order="sequence, id")
        for check in checks:
            check._process()
        self.env["od19.health.incident"]._cron_escalate()

    @api.model
    def _overall_state(self):
        """สถานะรวมของระบบ = สถานะที่แย่ที่สุดของผลการตรวจล่าสุด."""
        checks = self.search([("active", "=", True)])
        states = [check.last_state for check in checks if check.last_run]
        if not states:
            return "unknown"
        if "critical" in states:
            return "critical"
        if "warning" in states:
            return "warning"
        return "ok"

    @api.model
    def _monitor_enabled(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(PARAM_ENABLED, "True")
            in ("True", "true", "1")
        )

    @api.model
    def _retention_days(self):
        return int(self.env["ir.config_parameter"].sudo().get_param(PARAM_RETENTION_DAYS, 90) or 0)

    def action_view_results(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "ผลการตรวจ: %s" % self.name,
            "res_model": "od19.health.result",
            "view_mode": "list,graph,pivot",
            "domain": [("check_id", "=", self.id)],
            "context": {"default_check_id": self.id},
        }
