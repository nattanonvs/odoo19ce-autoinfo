# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Od19TaPlant(models.Model):
    """ไซต์/คลังของลูกค้า (Plant) — โดเมน TA ที่ Odoo core ไม่มี.

    ไม่มีโมดูลมาตรฐาน/OCA ที่ตรงโดเมนนี้จึงสร้างใหม่ แต่ผูกกับของมาตรฐาน:
    เจ้าของไซต์ = ``res.partner`` และอุปกรณ์ = ``maintenance.equipment``
    """

    _name = "od19.ta.plant"
    _description = "TA Plant / Site"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "code"

    name = fields.Char(string="Plant Name", required=True, tracking=True)
    code = fields.Char(string="Plant Code", required=True, tracking=True, copy=False)
    partner_id = fields.Many2one(
        "res.partner",
        string="Owner",
        required=True,
        tracking=True,
        domain="[('is_company', '=', True)]",
        help="เจ้าของไซต์ (ใช้ res.partner มาตรฐาน)",
    )
    province = fields.Char(string="Province")
    street = fields.Text(string="Site Address")
    latitude = fields.Float(string="Latitude", digits=(10, 6))
    longitude = fields.Float(string="Longitude", digits=(10, 6))
    access_requirements = fields.Text(string="Access Requirements")
    inventory_software = fields.Char(string="Inventory Software")
    interface_type = fields.Char(string="Interface Type")
    system_version = fields.Char(string="System / Version")
    aliases = fields.Char(string="Aliases")
    merged_into_id = fields.Many2one(
        "od19.ta.plant", string="Merged Into", copy=False
    )
    active = fields.Boolean(default=True)
    notes = fields.Html(string="Notes")

    tank_ids = fields.One2many("od19.ta.tank", "plant_id", string="Tanks")
    equipment_ids = fields.One2many(
        "maintenance.equipment", "od19_ta_plant_id", string="Equipment"
    )
    tank_count = fields.Integer(compute="_compute_counts", string="Tanks Count")
    equipment_count = fields.Integer(
        compute="_compute_counts", string="Equipment Count"
    )
    atg_tank_count = fields.Integer(
        compute="_compute_atg_tank_count", string="Tanks with ATG"
    )

    _od19_ta_plant_code_uniq = models.Constraint(
        "unique(code)",
        "Plant code must be unique.",
    )

    @api.depends("tank_ids", "equipment_ids")
    def _compute_counts(self):
        for plant in self:
            plant.tank_count = len(plant.tank_ids)
            plant.equipment_count = len(plant.equipment_ids)

    @api.depends("tank_ids", "tank_ids.equipment_ids")
    def _compute_atg_tank_count(self):
        for plant in self:
            plant.atg_tank_count = len(plant.tank_ids.filtered("equipment_ids"))

    def action_view_tanks(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Tanks",
            "res_model": "od19.ta.tank",
            "view_mode": "list,form",
            "domain": [("plant_id", "=", self.id)],
            "context": {"default_plant_id": self.id},
        }

    def action_view_equipment(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Equipment",
            "res_model": "maintenance.equipment",
            "view_mode": "list,form,kanban",
            "domain": [("od19_ta_plant_id", "=", self.id)],
            "context": {"default_od19_ta_plant_id": self.id, "default_od19_ta_is_ta": True},
        }
