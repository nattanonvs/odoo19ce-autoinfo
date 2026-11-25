# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    """เพิ่มฟิลด์โดเมน TA บน ``res.partner`` — ไม่สร้างโมเดลบริษัทซ้ำ."""

    _inherit = "res.partner"

    od19_ta_is_company = fields.Boolean(
        string="TA Company",
        help="ทำเครื่องหมายว่า partner นี้เป็นบริษัทลูกค้า/เจ้าของไซต์ในทะเบียน TA",
    )
    od19_ta_company_type = fields.Selection(
        [
            ("end_user", "End User"),
            ("contractor", "Contractor"),
            ("distributor", "Distributor"),
            ("epc", "EPC"),
            ("other", "Other"),
        ],
        string="TA Company Type",
    )
    od19_ta_industry = fields.Selection(
        [
            ("refinery", "Refinery"),
            ("petrochem", "Petrochem"),
            ("terminal", "Terminal"),
            ("fuel_marketing", "Fuel Marketing"),
            ("lpg", "LPG"),
            ("bio_agro", "Bio / Agro"),
            ("aviation", "Aviation"),
            ("power", "Power"),
            ("service", "Service"),
            ("other", "Other"),
        ],
        string="TA Industry",
    )
    od19_ta_odoo_ref = fields.Char(
        string="Legacy Odoo Ref",
        help="รหัสลูกค้าที่ระบบ TA เดิมอ้างอิง (เก็บเพื่อ audit / reconcile)",
    )
    od19_ta_merged_into_id = fields.Many2one(
        "res.partner", string="Merged Into", copy=False
    )
    od19_ta_merged_at = fields.Datetime(string="Merged At", copy=False)

    od19_ta_plant_ids = fields.One2many(
        "od19.ta.plant", "partner_id", string="Plants (Owner)"
    )
    od19_ta_plant_count = fields.Integer(compute="_compute_od19_ta_plant_count")
    od19_ta_contact_plant_id = fields.Many2one(
        "od19.ta.plant", string="Contact Plant"
    )

    @api.depends("od19_ta_plant_ids")
    def _compute_od19_ta_plant_count(self):
        for partner in self:
            partner.od19_ta_plant_count = len(partner.od19_ta_plant_ids)

    def action_view_od19_ta_plants(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Plants",
            "res_model": "od19.ta.plant",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }
