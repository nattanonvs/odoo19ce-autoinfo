# -*- coding: utf-8 -*-
"""Revision — snapshot ก่อน apply + ปุ่มย้อนกลับ (Restore)"""
import json
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class Od19ScRevision(models.Model):
    _name = "od19.sc.revision"
    _description = "Service Center — Revision"
    _order = "id desc"

    template_id = fields.Many2one("od19.sc.template", required=True, ondelete="cascade")
    name = fields.Char(required=True)
    snapshot = fields.Text()
    note = fields.Char()
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)

    def action_restore(self):
        self.ensure_one()
        data = json.loads(self.snapshot or "{}")
        self.template_id._restore_snapshot(data)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Service Center",
                "message": "Restored revision #%s" % self.id,
                "type": "success",
                "sticky": False,
            },
        }
