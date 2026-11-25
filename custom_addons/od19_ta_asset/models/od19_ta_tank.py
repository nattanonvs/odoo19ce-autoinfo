# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Od19TaTank(models.Model):
    """ถัง (Tank) ภายใน Plant — โดเมน TA ที่ Odoo core ไม่มี."""

    _name = "od19.ta.tank"
    _description = "TA Tank"
    _inherit = ["mail.thread"]
    _order = "plant_id, tag"

    name = fields.Char(compute="_compute_name", store=True, string="Tank")
    plant_id = fields.Many2one(
        "od19.ta.plant", string="Plant", required=True, ondelete="cascade", tracking=True
    )
    partner_id = fields.Many2one(
        related="plant_id.partner_id", store=True, string="Owner"
    )
    tag = fields.Char(string="Tank Tag", required=True, tracking=True)
    area = fields.Selection(
        [
            ("movement", "Movement"),
            ("offsite", "Offsite"),
            ("lorry", "LORRY"),
            ("c_cot", "C-COT"),
            ("utility", "UTILITY"),
            ("other", "Other"),
        ],
        string="Area",
    )
    tank_type = fields.Char(string="Tank Type")
    product = fields.Char(string="Product")
    height_mm = fields.Float(string="Height (mm)")
    has_stilling_well = fields.Boolean(string="Has Stilling Well")
    notes = fields.Text(string="Notes")

    equipment_ids = fields.One2many(
        "maintenance.equipment", "od19_ta_tank_id", string="Equipment"
    )
    equipment_count = fields.Integer(compute="_compute_equipment_count")

    _od19_ta_tank_tag_uniq = models.Constraint(
        "unique(plant_id, tag)",
        "Tank tag must be unique within a plant.",
    )

    @api.depends("plant_id.code", "tag")
    def _compute_name(self):
        for tank in self:
            left = tank.plant_id.code or ""
            right = tank.tag or ""
            tank.name = ("%s / %s" % (left, right)).strip(" /")

    @api.depends("equipment_ids")
    def _compute_equipment_count(self):
        for tank in self:
            tank.equipment_count = len(tank.equipment_ids)
