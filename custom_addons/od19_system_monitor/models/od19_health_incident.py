# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""เหตุการณ์สุขภาพระบบ (incident): เปิด–รับทราบ–ปิด + dedup + ยกระดับ (P3).

ออกแบบตามข้อเสนอโครงการ P3:

* ความรุนแรง 4 ระดับ (Info / Warning / Critical / Emergency)
* Dedup ด้วย ``fingerprint`` (การตรวจ + เป้าหมาย) ภายในหน้าต่างเวลาที่กำหนด
* Escalation: ถ้าไม่มีการรับทราบภายใน N นาที จะยกระดับความรุนแรง/ช่องทาง
* รับทราบ (ack) / เลื่อน (snooze) / ปิด (close) + หน้าต่างซ่อมบำรุง
* สรุปรายวัน 08:00 (จ.–ศ.) ตามเวลาทำการของบริษัท
"""

import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .od19_health_common import (
    NOTIFY_EVENT_ALERT,
    NOTIFY_EVENT_DIGEST,
    PARAM_AI_TRIAGE_ENABLED,
    PARAM_DIGEST_ENABLED,
    PARAM_DIGEST_HOUR,
    SEVERITIES,
    SEVERITY_RANK,
    SEVERITY_TO_STATE,
)

_logger = logging.getLogger(__name__)

INCIDENT_STATES = [
    ("open", "เปิด"),
    ("acknowledged", "รับทราบแล้ว"),
    ("snoozed", "เลื่อนไว้"),
    ("closed", "ปิด"),
]

CLOSE_REASONS = [
    ("resolved", "แก้ไขแล้ว"),
    ("false_positive", "สัญญาณเท็จ"),
    ("maintenance", "อยู่ในหน้าต่างซ่อมบำรุง"),
    ("manual", "ปิดด้วยมือ"),
]

OPEN_STATES = ("open", "acknowledged", "snoozed")


class Od19HealthIncident(models.Model):
    """เหตุการณ์สุขภาพระบบ 1 เหตุการณ์ (มี unit of dedup = fingerprint)."""

    _name = "od19.health.incident"
    _description = "เหตุการณ์สุขภาพระบบ (OD19)"
    _inherit = ["mail.thread"]
    _order = "state_rank desc, last_seen desc, id desc"

    name = fields.Char(default=lambda self: _("New"), copy=False, readonly=True)
    check_id = fields.Many2one(
        "od19.health.check", required=True, ondelete="cascade", index=True
    )
    rule_id = fields.Many2one("od19.health.rule", ondelete="set null")
    fingerprint = fields.Char(required=True, index=True, copy=False)
    target = fields.Char(help="เป้าหมายที่เกิดเหตุ (เช่น ชื่อ cron)")

    severity = fields.Selection(SEVERITIES, default="warning", required=True, index=True)
    severity_label = fields.Char(compute="_compute_severity_label")
    state = fields.Selection(INCIDENT_STATES, default="open", required=True, index=True)
    state_rank = fields.Integer(compute="_compute_state_rank", store=True)
    check_state = fields.Selection(
        [("warning", "เตือน"), ("critical", "วิกฤต")],
        default="warning",
        required=True,
    )

    first_seen = fields.Datetime(default=fields.Datetime.now, required=True)
    last_seen = fields.Datetime(default=fields.Datetime.now, required=True)
    occurrence_count = fields.Integer(default=1)
    last_notified_at = fields.Datetime()
    notification_count = fields.Integer(default=0)

    acknowledged_by = fields.Many2one("res.users", readonly=True)
    acknowledged_at = fields.Datetime(readonly=True)
    snoozed_until = fields.Datetime()
    closed_at = fields.Datetime(readonly=True)
    closed_by = fields.Many2one("res.users", readonly=True)
    close_reason = fields.Selection(CLOSE_REASONS)

    escalated = fields.Boolean(default=False)
    escalated_at = fields.Datetime(readonly=True)
    previous_severity = fields.Selection(SEVERITIES)

    description = fields.Text()
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True
    )

    # ---------------------- การวินิจฉัยด้วย AI (P5) ----------------------
    triage_ids = fields.One2many(
        "od19.health.ai.triage",
        "incident_id",
        string="การวินิจฉัยด้วย AI",
        readonly=True,
    )
    triage_count = fields.Integer(compute="_compute_triage_count")
    ai_triage_enabled = fields.Boolean(compute="_compute_ai_triage_enabled")

    @api.depends("triage_ids")
    def _compute_triage_count(self):
        for incident in self:
            incident.triage_count = len(incident.triage_ids)

    def _compute_ai_triage_enabled(self):
        enabled = self.env["ir.config_parameter"].sudo().get_param(
            PARAM_AI_TRIAGE_ENABLED, "False"
        ) in ("True", "true", "1")
        for incident in self:
            incident.ai_triage_enabled = enabled

    _fingerprint_open_unique = models.Constraint(
        "unique(fingerprint, state)",
        "ต้องมีเหตุการณ์ที่เปิดอยู่เพียง 1 รายการต่อ fingerprint เดียวกัน",
    )

    # ------------------------------------------------------------------
    # compute
    # ------------------------------------------------------------------
    @api.depends("severity")
    def _compute_severity_label(self):
        labels = dict(SEVERITIES)
        for incident in self:
            incident.severity_label = labels.get(incident.severity, incident.severity)

    @api.depends("state")
    def _compute_state_rank(self):
        # เรียงเหตุที่ยังเปิดอยู่ขึ้นก่อน แล้วค่อยเรียงตามความรุนแรง
        for incident in self:
            incident.state_rank = 10 if incident.state in OPEN_STATES else 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("od19.health.incident")
                    or _("New")
                )
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # ผู้รับ / การแจ้งเตือน
    # ------------------------------------------------------------------
    def _default_recipients(self):
        """ผู้รับสำรอง: สมาชิกกลุ่มผู้จัดการเฝ้าระวัง (หรือผู้ดูแลระบบ)."""
        group = self.env.ref(
            "od19_system_monitor.group_od19_health_manager", raise_if_not_found=False
        )
        partners = self.env["res.users"].browse()
        if group:
            partners = self.env["res.users"].search(
                [("group_ids", "in", group.ids)]
            ).mapped("partner_id")
        partners = partners.filtered("active")
        if not partners:
            partners = self.env.ref("base.user_admin").partner_id
        return partners

    def _recipients(self):
        self.ensure_one()
        partners = self.rule_id._partners() if self.rule_id else self.env["res.partner"]
        return partners or self._default_recipients()

    def _notification_message(self, prefix=""):
        self.ensure_one()
        return "%s[%s] %s\n%s" % (
            prefix,
            self.severity.upper(),
            self.check_id.name,
            self.description or "",
        )

    def _notify(self, prefix=""):
        """ส่งแจ้งเตือนผ่าน notification.service (email/odoo/line)."""
        self.ensure_one()
        event = (self.rule_id.notify_event if self.rule_id else None) or NOTIFY_EVENT_ALERT
        subject = "[%s] %s" % (self.severity.upper(), self.check_id.name)
        body = self._notification_message(prefix)
        self.env["notification.service"].notify(
            self._recipients(), body, event=event, subject=subject
        )
        self.write(
            {
                "last_notified_at": fields.Datetime.now(),
                "notification_count": self.notification_count + 1,
            }
        )
        self.message_post(body=body, subject=subject)
        return True

    # ------------------------------------------------------------------
    # เปิด / อัปเดต / ปิดอัตโนมัติ
    # ------------------------------------------------------------------
    @api.model
    def _fingerprint(self, check, rule, target=""):
        """สร้างลายนิ้วมือสำหรับ dedup = การตรวจ | กฎ | เป้าหมาย."""
        return "%s|%s|%s" % (check.code, rule.id if rule else 0, target or "")

    @api.model
    def _open_or_update(self, check, rule, measure, state):
        """เปิดเหตุใหม่ หรืออัปเดตเหตุเดิม (dedup) แล้วแจ้งเตือนตามหน้าต่างเวลา."""
        maintenance = self.env["od19.health.maintenance"]
        target = measure.get("details", {}).get("cron") or ""
        fingerprint = self._fingerprint(check, rule, target)
        now = fields.Datetime.now()
        window = (rule.fingerprint_window_minutes if rule else 0) or 0
        existing = self.search(
            [("fingerprint", "=", fingerprint), ("state", "in", list(OPEN_STATES))],
            limit=1,
        )
        description = measure.get("message") or ""
        if existing:
            existing.write(
                {
                    "last_seen": now,
                    "occurrence_count": existing.occurrence_count + 1,
                    "description": description,
                    "check_state": state,
                }
            )
            # ถ้าเหตุเดิมอยู่ในหน้าต่าง dedup -> นับครั้ง แต่ไม่แจ้งซ้ำ
            should_notify = True
            if window and existing.last_notified_at:
                elapsed = (now - existing.last_notified_at).total_seconds() / 60.0
                should_notify = elapsed >= window
            if should_notify and not maintenance.is_suppressed(check, at=now):
                existing._notify(prefix="แจ้งซ้ำ: ")
            return existing

        incident = self.create(
            {
                "check_id": check.id,
                "rule_id": rule.id if rule else False,
                "fingerprint": fingerprint,
                "target": target,
                "severity": rule.severity if rule else "warning",
                "check_state": state,
                "first_seen": now,
                "last_seen": now,
                "description": description,
                "company_id": check.company_id.id,
            }
        )
        if not maintenance.is_suppressed(check, at=now):
            incident._notify()
        else:
            incident.message_post(body=_("อยู่ในหน้าต่างซ่อมบำรุง — งดแจ้งเตือน"))
        return incident

    @api.model
    def _auto_resolve(self, check, state):
        """ปิดเหตุที่เปิดอยู่ของ check นี้เมื่อผลกลับมาเป็นปกติ."""
        if state != "ok":
            return 0
        open_incidents = self.search(
            [("check_id", "=", check.id), ("state", "in", list(OPEN_STATES))]
        )
        count = 0
        for incident in open_incidents:
            if incident.state == "snoozed" and incident.snoozed_until and incident.snoozed_until > fields.Datetime.now():
                continue
            incident._close("resolved")
            count += 1
        return count

    def _close(self, reason):
        self.ensure_one()
        self.write(
            {
                "state": "closed",
                "closed_at": fields.Datetime.now(),
                "closed_by": self.env.user.id,
                "close_reason": reason,
            }
        )
        self.message_post(
            body=_("ปิดเหตุการณ์: %s") % dict(CLOSE_REASONS).get(reason, reason)
        )
        return True

    # ------------------------------------------------------------------
    # ปุ่มบนหน้าจอ
    # ------------------------------------------------------------------
    def action_acknowledge(self):
        for incident in self:
            if incident.state == "closed":
                raise UserError(_("เหตุการณ์นี้ปิดแล้ว"))
            incident.write(
                {
                    "state": "acknowledged",
                    "acknowledged_by": self.env.user.id,
                    "acknowledged_at": fields.Datetime.now(),
                }
            )
            incident.message_post(body=_("รับทราบเหตุการณ์แล้ว"))
        return True

    def action_snooze(self, hours=4):
        """เลื่อนการแจ้งเตือนออกไป ``hours`` ชั่วโมง (ค่าเริ่มต้น 4 ชั่วโมง)."""
        now = fields.Datetime.now()
        for incident in self:
            if incident.state == "closed":
                raise UserError(_("เหตุการณ์นี้ปิดแล้ว"))
            incident.write(
                {
                    "state": "snoozed",
                    "snoozed_until": now + timedelta(hours=hours),
                }
            )
            incident.message_post(body=_("เลื่อนการแจ้งเตือน %s ชั่วโมง") % hours)
        return True

    def action_close(self):
        for incident in self:
            incident._close("manual")
        return True

    def action_run_triage(self):
        """ปุ่มสั่งวินิจฉัยด้วย AI (โหมดอ่านเท่านั้น — AI ห้ามแก้ระบบเอง)."""
        self.ensure_one()
        if not self.ai_triage_enabled:
            raise UserError(_("ยังไม่ได้เปิดใช้การวินิจฉัยด้วย AI ในหน้าตั้งค่า"))
        self.env["od19.health.ai.triage"]._triage(self)
        return {
            "type": "ir.actions.act_window",
            "name": _("การวินิจฉัยด้วย AI: %s") % self.name,
            "res_model": "od19.health.ai.triage",
            "view_mode": "list,form",
            "domain": [("incident_id", "=", self.id)],
            "context": {"default_incident_id": self.id},
            "target": "current",
        }

    # ------------------------------------------------------------------
    # cron: ยกระดับ + สรุปรายวัน
    # ------------------------------------------------------------------
    @api.model
    def _cron_escalate(self):
        """ยกระดับเหตุที่ยังไม่ถูกรับทราบภายในเวลาที่กำหนด."""
        now = fields.Datetime.now()
        candidates = self.search([("state", "in", ["open", "snoozed"])])
        for incident in candidates:
            rule = incident.rule_id
            if not rule or not rule.escalate_after_minutes:
                continue
            if incident.escalated:
                continue
            elapsed = (now - incident.first_seen).total_seconds() / 60.0
            if elapsed < rule.escalate_after_minutes:
                continue
            target_severity = rule.escalate_severity or incident.severity
            if SEVERITY_RANK.get(target_severity, 0) <= SEVERITY_RANK.get(
                incident.severity, 0
            ):
                target_severity = "emergency"
            incident.write(
                {
                    "previous_severity": incident.severity,
                    "severity": target_severity,
                    "escalated": True,
                    "escalated_at": now,
                }
            )
            incident._notify(prefix=_("ยกระดับ: "))
        return True

    @api.model
    def _cron_send_digest(self):
        """สรุปรายวัน 08:00 (จ.–ศ.) ตามเวลาทำการของบริษัท."""
        params = self.env["ir.config_parameter"].sudo()
        enabled = params.get_param(PARAM_DIGEST_ENABLED, "True") in ("True", "true", "1")
        if not enabled:
            return
        hour = int(params.get_param(PARAM_DIGEST_HOUR, 8) or 8)
        now = fields.Datetime.now()
        # cron ทำงานทุกชั่วโมง แต่จะส่งเฉพาะชั่วโมงที่กำหนดและเฉพาะวันจันทร์–ศุกร์
        if now.hour != hour or now.weekday() > 4:
            return
        self._send_digest(now)

    @api.model
    def _send_digest(self, now=None):
        now = now or fields.Datetime.now()
        open_incidents = self.search([("state", "in", list(OPEN_STATES))])
        lines = [
            _("สรุปสุขภาพระบบ Odoo 19 — %s") % fields.Datetime.to_string(now),
            _("เหตุการณ์ที่ยังเปิดอยู่: %s รายการ") % len(open_incidents),
        ]
        for incident in open_incidents.sorted(
            lambda item: SEVERITY_RANK.get(item.severity, 0), reverse=True
        )[:25]:
            lines.append(
                "• [%s] %s (%s ครั้ง)"
                % (incident.severity.upper(), incident.check_id.name, incident.occurrence_count)
            )
        if not open_incidents:
            lines.append(_("• ไม่มีเหตุการณ์ค้าง — ระบบเป็นปกติ"))
        body = "\n".join(lines)
        recipients = self._default_recipients()
        self.env["notification.service"].notify(
            recipients,
            body,
            event=NOTIFY_EVENT_DIGEST,
            subject=_("สรุปสุขภาพระบบ Odoo 19"),
        )
        _logger.info("ส่งสรุปรายวันสุขภาพระบบถึง %d ผู้รับ", len(recipients))
        return body
