# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MaintenanceEquipment(models.Model):
    """เพิ่มประวัติงานบริการ (helpdesk.ticket) บนอุปกรณ์ ATG — ไม่สร้างโมเดลงานซ้ำ."""

    _inherit = "maintenance.equipment"

    od19_ta_ticket_ids = fields.One2many(
        "helpdesk.ticket", "od19_ta_equipment_id", string="Service Tickets"
    )
    od19_ta_ticket_count = fields.Integer(
        compute="_compute_od19_ta_ticket_count", string="Tickets Count"
    )

    @api.depends("od19_ta_ticket_ids")
    def _compute_od19_ta_ticket_count(self):
        for equipment in self:
            equipment.od19_ta_ticket_count = len(equipment.od19_ta_ticket_ids)

    def action_view_od19_ta_tickets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Service Tickets",
            "res_model": "helpdesk.ticket",
            "view_mode": "kanban,list,form",
            "domain": [("od19_ta_equipment_id", "=", self.id)],
            "context": {
                "default_od19_ta_plant_id": self.od19_ta_plant_id.id,
                "default_od19_ta_tank_id": self.od19_ta_tank_id.id,
                "default_od19_ta_equipment_id": self.id,
            },
        }
