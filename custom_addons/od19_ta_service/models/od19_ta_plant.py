# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Od19TaPlant(models.Model):
    """เพิ่มประวัติงานบริการ (helpdesk.ticket) บน Plant — ไม่สร้างโมเดลงานซ้ำ."""

    _inherit = "od19.ta.plant"

    od19_ta_ticket_ids = fields.One2many(
        "helpdesk.ticket", "od19_ta_plant_id", string="Service Tickets"
    )
    od19_ta_ticket_count = fields.Integer(
        compute="_compute_od19_ta_ticket_count", string="Tickets Count"
    )

    @api.depends("od19_ta_ticket_ids")
    def _compute_od19_ta_ticket_count(self):
        for plant in self:
            plant.od19_ta_ticket_count = len(plant.od19_ta_ticket_ids)

    def action_view_od19_ta_tickets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Service Tickets",
            "res_model": "helpdesk.ticket",
            "view_mode": "kanban,list,form",
            "domain": [("od19_ta_plant_id", "=", self.id)],
            "context": {"default_od19_ta_plant_id": self.id},
        }
