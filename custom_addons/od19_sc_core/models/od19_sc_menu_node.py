# -*- coding: utf-8 -*-
"""Menu Engine — สร้าง/แก้เมนูจากข้อมูล (tree) ผ่าน ir.ui.menu + ir.actions.*"""
import logging

from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class Od19ScMenuNode(models.Model):
    _name = "od19.sc.menu.node"
    _description = "Service Center — Menu Node"
    _order = "template_id, sequence, id"

    template_id = fields.Many2one("od19.sc.template", required=True, ondelete="cascade")
    name = fields.Char(required=True, translate=True)
    parent_id = fields.Many2one(
        "od19.sc.menu.node", string="Parent Menu", ondelete="cascade",
        domain="[('template_id', '=', template_id)]")
    sequence = fields.Integer(default=10)
    menu_type = fields.Selection(
        [
            ("group", "Group (no action)"),
            ("window", "Open a model"),
            ("url", "Open a URL"),
            ("client", "Client action"),
        ],
        string="Type", default="group", required=True)
    target_model = fields.Char(string="Model", help="เช่น maintenance.equipment")
    view_mode = fields.Char(default="list,form")
    target_url = fields.Char()
    client_tag = fields.Char(help="tag ของ ir.actions.client เช่น od19_sc.designer")
    group_ids = fields.Many2many("res.groups", string="Visible to groups")
    active = fields.Boolean(default=True)

    ir_menu_id = fields.Many2one("ir.ui.menu", readonly=True, ondelete="set null")
    ir_action_id = fields.Char(string="Materialized Action", readonly=True)

    def _materialize(self):
        self.ensure_one()
        menu = self.ir_menu_id
        if not menu or not menu.exists():
            menu = self.env["ir.ui.menu"].create({"name": self.name})
            self.ir_menu_id = menu.id
        vals = {
            "name": self.name,
            "sequence": self.sequence,
            "active": self.active,
            "parent_id": self.parent_id.ir_menu_id.id or False,
        }
        action_ref = self._materialize_action()
        if action_ref is not False:
            vals["action"] = action_ref
        vals["group_ids"] = [(6, 0, self.group_ids.ids)]
        menu.write(vals)

    def _materialize_action(self):
        """สร้าง/อัปเดต action ปลายทาง แล้วคืน reference string (หรือ False = ไม่มี action)."""
        self.ensure_one()
        model = action = None
        if self.menu_type == "window" and self.target_model:
            model = "ir.actions.act_window"
            vals = {"name": self.name, "res_model": self.target_model,
                    "view_mode": self.view_mode or "list,form"}
        elif self.menu_type == "url" and self.target_url:
            model = "ir.actions.act_url"
            vals = {"name": self.name, "url": self.target_url, "target": "self"}
        elif self.menu_type == "client" and self.client_tag:
            model = "ir.actions.client"
            vals = {"name": self.name, "tag": self.client_tag}
        if not model:
            return False

        if self.ir_action_id and "," in self.ir_action_id:
            existing_model, existing_id = self.ir_action_id.split(",")
            if existing_model == model:
                action = self.env[existing_model].browse(int(existing_id))
        if action and action.exists():
            action.write(vals)
        else:
            action = self.env[model].create(vals)
        ref = "%s,%s" % (model, action.id)
        self.ir_action_id = ref
        return ref
