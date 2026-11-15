# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""คอนโทรลเลอร์ HTTP ของระบบเฝ้าระวังสุขภาพ Odoo 19 (P2).

มี 3 ปลายทาง:

* ``GET  /od19/health``          — JSON สั้น ไม่มีข้อมูลอ่อนไหว (สำหรับ probe/Uptime)
* ``GET  /od19/health/detail``   — รายละเอียดสำหรับผู้ดูแลเฝ้าระวัง (ต้องล็อกอิน)
* ``POST /od19/health/heartbeat``— รับสัญญาณจากตัวเฝ้าชั้นนอก (P1)

ทั้งหมดเป็น *อ่านอย่างเดียว* ยกเว้น heartbeat ที่เขียนเฉพาะตารางสถานะของตัวเอง
"""

import json
import logging

from odoo import http
from odoo.http import request

from ..models.od19_health_common import PARAM_HEARTBEAT_TOKEN

_logger = logging.getLogger(__name__)

# สถานะที่ตัวเฝ้าชั้นนอกรายงาน -> สถานะภายในของ watchdog
_STATUS_MAP = {
    "ok": "ok",
    "pass": "ok",
    "healthy": "ok",
    "normal": "ok",
    "warn": "warning",
    "warning": "warning",
    "degraded": "warning",
    "crit": "critical",
    "critical": "critical",
    "down": "critical",
    "fail": "critical",
}


class Od19SystemMonitorController(http.Controller):
    """ปลายทางตรวจสุขภาพระบบ (read-only + heartbeat)."""

    # ------------------------------------------------------------------
    # /od19/health — สัญญาณสั้น
    # ------------------------------------------------------------------
    @http.route(
        "/od19/health",
        type="http",
        auth="none",
        methods=["GET"],
        save_session=False,
        csrf=False,
    )
    def health(self, **kw):
        """คืนสถานะรวมแบบสั้น (ไม่มีรายละเอียดที่อ่อนไหว).

        HTTP 200 = ปกติ/ไม่ทราบ, 503 = วิกฤต — ให้ตัว probe ภายนอกตีความได้ง่าย
        """
        overall = request.env["od19.health.check"].sudo()._overall_state()
        payload = {
            "status": overall,
            "ok": overall in ("ok", "unknown"),
            "monitor": "od19_system_monitor",
        }
        status = 503 if overall == "critical" else 200
        return request.make_response(
            json.dumps(payload),
            [("Content-Type", "application/json"), ("Cache-Control", "no-store")],
            status=status,
        )

    # ------------------------------------------------------------------
    # /od19/health/detail — รายละเอียดสำหรับผู้ดูแล
    # ------------------------------------------------------------------
    @http.route(
        "/od19/health/detail",
        type="http",
        auth="user",
        methods=["GET"],
        save_session=False,
        csrf=False,
    )
    def health_detail(self, **kw):
        """คืนรายละเอียดการตรวจทุกตัว + เหตุการณ์ที่เปิดอยู่ (เฉพาะผู้มีสิทธิ์)."""
        user = request.env.user
        allowed = user.has_group(
            "od19_system_monitor.group_od19_health_user"
        ) or user.has_group("od19_system_monitor.group_od19_health_manager")
        if not allowed:
            return request.make_response(
                json.dumps({"error": "forbidden"}),
                [("Content-Type", "application/json"), ("Cache-Control", "no-store")],
                status=403,
            )

        checks = request.env["od19.health.check"].sudo().search(
            [("active", "=", True)], order="category, sequence, name"
        )
        incidents = (
            request.env["od19.health.incident"]
            .sudo()
            .search(
                [("state", "in", ["open", "acknowledged", "snoozed"])],
                order="state_rank desc, last_seen desc",
                limit=50,
            )
        )
        payload = {
            "status": checks._overall_state(),
            "checks": [
                {
                    "code": check.code,
                    "name": check.name,
                    "category": check.category,
                    "state": check.last_state,
                    "value": check.last_value,
                    "value_label": check.last_value_label,
                    "message": check.last_message,
                    "last_run": check.last_run.isoformat() if check.last_run else None,
                }
                for check in checks
            ],
            "incidents": [
                {
                    "name": incident.name,
                    "severity": incident.severity,
                    "state": incident.state,
                    "check": incident.check_id.code,
                    "occurrences": incident.occurrence_count,
                    "last_seen": incident.last_seen.isoformat()
                    if incident.last_seen
                    else None,
                }
                for incident in incidents
            ],
        }
        return request.make_response(
            json.dumps(payload),
            [("Content-Type", "application/json"), ("Cache-Control", "no-store")],
            status=200,
        )

    # ------------------------------------------------------------------
    # /od19/health/heartbeat — รับสัญญาณจากตัวเฝ้าชั้นนอก (P1)
    # ------------------------------------------------------------------
    @http.route(
        "/od19/health/heartbeat",
        type="http",
        auth="none",
        methods=["POST"],
        save_session=False,
        csrf=False,
    )
    def heartbeat(self, **kw):
        """บันทึก heartbeat ของตัวเฝ้าชั้นนอก (ต้องมี token เมื่อตั้งค่าไว้)."""
        raw = request.httprequest.get_data(as_text=True) or "{}"
        try:
            payload = json.loads(raw)
        except ValueError:
            return self._json_error("invalid-json", 400)
        if not isinstance(payload, dict):
            return self._json_error("invalid-payload", 400)

        expected = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param(PARAM_HEARTBEAT_TOKEN, "")
        )
        if expected:
            provided = request.httprequest.headers.get("X-Health-Token") or payload.get(
                "token", ""
            )
            if provided != expected:
                _logger.warning("heartbeat ถูกปฏิเสธ: token ไม่ถูกต้อง")
                return self._json_error("invalid-token", 403)

        code = (
            payload.get("code")
            or payload.get("agent_id")
            or payload.get("source")
            or "od19-health-watch"
        )
        status = _STATUS_MAP.get(str(payload.get("overall", "ok")).lower(), "unknown")
        message = payload.get("message") or "heartbeat จากตัวเฝ้าชั้นนอก"
        watchdog = (
            request.env["od19.health.watchdog"]
            .sudo()
            .register_heartbeat(code, status=status, message=message, payload=payload)
        )
        return request.make_response(
            json.dumps({"ok": True, "code": watchdog.code, "status": status}),
            [("Content-Type", "application/json"), ("Cache-Control", "no-store")],
            status=200,
        )

    # ------------------------------------------------------------------
    def _json_error(self, code, status):
        return request.make_response(
            json.dumps({"ok": False, "error": code}),
            [("Content-Type", "application/json"), ("Cache-Control", "no-store")],
            status=status,
        )
