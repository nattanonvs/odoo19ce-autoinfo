# -*- coding: utf-8 -*-
"""Calculation Engine — สูตรคำนวณอิสระ ผ่าน safe_eval + base.automation / ir.cron"""
import logging

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class Od19ScFormula(models.Model):
    _name = "od19.sc.formula"
    _description = "Service Center — Formula / Rule"
    _order = "template_id, sequence, id"

    template_id = fields.Many2one("od19.sc.template", required=True, ondelete="cascade")
    name = fields.Char(required=True, translate=True)
    target_model = fields.Char(required=True, help="โมเดลที่ใช้คำนวณ เช่น helpdesk.ticket")
    target_field = fields.Char(required=True, help="ฟิลด์ปลายทางที่จะเก็บค่าที่คำนวณได้")
    expression = fields.Text(
        required=True,
        help="นิพจน์ Python — ตัวแปร 'record' คือเรคคอร์ดปัจจุบัน, 'env' คือ environment")
    trigger = fields.Selection(
        [("on_write", "On create / edit"), ("cron", "Scheduled")],
        default="on_write", required=True)
    cron_interval_number = fields.Integer(default=1)
    cron_interval_type = fields.Selection(
        [("minutes", "Minutes"), ("hours", "Hours"), ("days", "Days")],
        default="hours")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    ir_action_id = fields.Many2one("ir.actions.server", readonly=True, ondelete="set null")
    ir_automation_id = fields.Many2one("base.automation", readonly=True, ondelete="set null")
    ir_cron_id = fields.Many2one("ir.cron", readonly=True, ondelete="set null")
    last_result = fields.Char(readonly=True)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def _eval_context(self, record):
        return {"record": record, "env": self.env, "self": self}

    def _evaluate(self, record):
        return safe_eval(self.expression or "None", self._eval_context(record))

    def _run_on(self, records):
        """เรียกจาก server action / cron — เขียนผลลงฟิลด์ปลายทาง."""
        for formula in self:
            if formula.target_field not in records._fields:
                raise UserError(
                    _("Field '%s' does not exist on model '%s'.")
                    % (formula.target_field, formula.target_model))
            for record in records:
                value = formula._evaluate(record)
                record.write({formula.target_field: value})
        return True

    def _run_cron(self):
        for formula in self:
            records = self.env[formula.target_model].search([])
            formula._run_on(records)
            formula.last_result = _("Ran on %s record(s)") % len(records)
        return True

    def action_test(self):
        self.ensure_one()
        sample = self.env[self.target_model].search([], limit=1)
        if not sample:
            raise UserError(
                _("No '%s' record available to test with.") % self.target_model)
        value = self._evaluate(sample)
        self.last_result = "%s = %s" % (self.target_field, value)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Formula test"),
                "message": self.last_result,
                "type": "success",
                "sticky": False,
            },
        }

    # ------------------------------------------------------------------
    # Materialize
    # ------------------------------------------------------------------
    def _materialize(self):
        self.ensure_one()
        model = self.env["ir.model"].search([("model", "=", self.target_model)], limit=1)
        if not model:
            raise UserError(_("Model '%s' was not found.") % self.target_model)
        if self.trigger == "on_write":
            self._materialize_automation(model)
            if self.ir_cron_id:
                self.ir_cron_id.unlink()
                self.ir_cron_id = False
        else:
            self._materialize_cron(model)
            if self.ir_automation_id:
                self.ir_automation_id.unlink()
                self.ir_automation_id = False

    def _materialize_automation(self, model):
        self.ensure_one()
        code = "env['od19.sc.formula'].browse(%s)._run_on(records)" % self.id
        vals = {
            "name": "ASC: %s" % self.name,
            "model_id": model.id,
            "state": "code",
            "usage": "base_automation",
            "code": code,
        }
        action = self.ir_action_id
        if action and action.exists():
            action.write(vals)
        else:
            action = self.env["ir.actions.server"].create(vals)
            self.ir_action_id = action.id
        auto_vals = {
            "name": "ASC: %s" % self.name,
            "model_id": model.id,
            "trigger": "on_create_or_write",
            "active": True,
            "action_server_ids": [(6, 0, [action.id])],
        }
        automation = self.ir_automation_id
        if automation and automation.exists():
            automation.write(auto_vals)
        else:
            automation = self.env["base.automation"].create(auto_vals)
            self.ir_automation_id = automation.id

    def _materialize_cron(self, model):
        self.ensure_one()
        vals = {
            "name": "ASC: %s" % self.name,
            "model_id": self.env["ir.model"]._get_id("od19.sc.formula"),
            "state": "code",
            "code": "env['od19.sc.formula'].browse(%s)._run_cron()" % self.id,
            "interval_number": max(1, self.cron_interval_number),
            "interval_type": self.cron_interval_type,
            "active": True,
        }
        cron = self.ir_cron_id
        if cron and cron.exists():
            cron.write(vals)
        else:
            self.ir_cron_id = self.env["ir.cron"].create(vals).id
