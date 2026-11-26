# -*- coding: utf-8 -*-
"""Integration Engine — เชื่อมต่อภายนอก (outbound requests / inbound webhook / cron)"""
import json
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Od19ScIntegrationEndpoint(models.Model):
    _name = "od19.sc.integration.endpoint"
    _description = "Service Center — Integration Endpoint"
    _order = "template_id, sequence, id"

    template_id = fields.Many2one("od19.sc.template", required=True, ondelete="cascade")
    name = fields.Char(required=True, translate=True)
    direction = fields.Selection(
        [("outbound", "Outbound (push)"), ("inbound", "Inbound (webhook)")],
        default="outbound", required=True)
    url = fields.Char()
    method = fields.Selection(
        [("GET", "GET"), ("POST", "POST"), ("PUT", "PUT")], default="POST")

    headers = fields.Text(help="JSON object ของ HTTP headers")
    payload_template = fields.Text(
        help="JSON ของ body — ถ้าไม่ใช่ JSON จะถือเป็นนิพจน์ Python ที่ประเมินด้วย safe_eval")
    auth_token_param = fields.Char(
        help="ชื่อ ir.config_parameter ที่เก็บ token (ค่า token ไม่เก็บในเทมเพลต)")
    mapping_model = fields.Char(help="โมเดลที่ใช้เป็นบริบทในการประเมิน payload")

    schedule = fields.Boolean(string="Run on schedule")
    cron_interval_number = fields.Integer(default=24)
    cron_interval_type = fields.Selection(
        [("minutes", "Minutes"), ("hours", "Hours"), ("days", "Days")],
        default="hours")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    ir_cron_id = fields.Many2one("ir.cron", readonly=True, ondelete="set null")
    last_status = fields.Char(readonly=True)
    last_run = fields.Datetime(readonly=True)

    # ------------------------------------------------------------------
    # HTTP call
    # ------------------------------------------------------------------
    def _build_headers(self):
        self.ensure_one()
        headers = {"Content-Type": "application/json"}
        if self.headers:
            try:
                headers.update(json.loads(self.headers))
            except ValueError:
                _logger.warning("ASC integration %s: invalid headers JSON", self.name)
        if self.auth_token_param:
            token = self.env["ir.config_parameter"].sudo().get_param(self.auth_token_param)
            if token:
                headers.setdefault("Authorization", "Bearer %s" % token)
        return headers

    def _build_payload(self):
        self.ensure_one()
        if not self.payload_template:
            return None
        text = self.payload_template.strip()
        try:
            return json.loads(text)
        except ValueError:
            from odoo.tools.safe_eval import safe_eval  # local import to keep module import light
            record = None
            if self.mapping_model:
                record = self.env[self.mapping_model].search([], limit=1)
            return safe_eval(text, {"record": record, "env": self.env})

    def action_test_connection(self):
        self.ensure_one()
        return self._call(payload={"ping": True, "endpoint": self.name})

    def action_run_now(self):
        self.ensure_one()
        return self._call(payload=self._build_payload())

    def _call(self, payload=None):
        self.ensure_one()
        if not self.url:
            raise UserError(_("Endpoint '%s' has no URL.") % self.name)
        import requests  # Odoo ships requests
        try:
            response = requests.request(
                self.method or "POST", self.url, timeout=15,
                headers=self._build_headers(),
                data=json.dumps(payload) if payload is not None else None)
            status = "%s %s" % (response.status_code, (response.reason or "")[:40])
            ok = response.ok
        except Exception as error:  # noqa: BLE001 - surface any network error to the UI
            status = _("ERROR: %s") % error
            ok = False
        self.write({"last_status": status, "last_run": fields.Datetime.now()})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Integration — %s") % self.name,
                "message": status,
                "type": "success" if ok else "danger",
                "sticky": False,
            },
        }

    def _cron_run(self):
        for endpoint in self.filtered(lambda e: e.direction == "outbound" and e.active):
            endpoint.action_run_now()
        return True

    @api.model
    def _webhook_receive(self, endpoint_id, payload):
        endpoint = self.browse(endpoint_id).exists()
        if not endpoint or endpoint.direction != "inbound":
            return {"ok": False, "error": "unknown endpoint"}
        endpoint.write({
            "last_status": _("Inbound received"),
            "last_run": fields.Datetime.now(),
        })
        _logger.info("ASC webhook %s received: %s", endpoint.name, payload)
        return {"ok": True, "endpoint": endpoint.name}

    # ------------------------------------------------------------------
    # Materialize
    # ------------------------------------------------------------------
    def _materialize(self):
        self.ensure_one()
        if self.direction == "outbound" and self.schedule:
            vals = {
                "name": "ASC: %s" % self.name,
                "model_id": self.env["ir.model"]._get_id("od19.sc.integration.endpoint"),
                "state": "code",
                "code": "env['od19.sc.integration.endpoint'].browse(%s)._cron_run()" % self.id,
                "interval_number": max(1, self.cron_interval_number),
                "interval_type": self.cron_interval_type,
                "active": True,
            }
            cron = self.ir_cron_id
            if cron and cron.exists():
                cron.write(vals)
            else:
                self.ir_cron_id = self.env["ir.cron"].create(vals).id
        elif self.ir_cron_id:
            self.ir_cron_id.unlink()
            self.ir_cron_id = False
