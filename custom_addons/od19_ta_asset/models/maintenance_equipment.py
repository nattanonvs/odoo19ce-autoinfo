# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MaintenanceEquipment(models.Model):
    """โมดูล *เสริม* บน ``maintenance.equipment`` (core) แทนการสร้างทะเบียนซ้ำ.

    ใช้ของเดิมให้ครบก่อน: ``name``, ``serial_no``, ``model``, ``manufacturer``
    ไม่มีใน core — Odoo ใช้ ``model`` (รุ่น) + ``partner_id`` (ผู้ขาย) +
    ``category_id`` (หมวด) + ``warranty_date`` (หมดประกัน) แล้ว
    ที่นี่เพิ่มเฉพาะฟิลด์ *ตำแหน่งติดตั้ง* และข้อมูลเฉพาะโดเมน ATG
    """

    _inherit = "maintenance.equipment"

    od19_ta_is_ta = fields.Boolean(
        string="TA / ATG Equipment",
        tracking=True,
        help="ทำเครื่องหมายว่าอุปกรณ์นี้อยู่ในทะเบียน ATG ของแผนก TA",
    )
    od19_ta_plant_id = fields.Many2one(
        "od19.ta.plant", string="Plant", tracking=True, index=True
    )
    od19_ta_tank_id = fields.Many2one(
        "od19.ta.tank",
        string="Tank",
        tracking=True,
        domain="[('plant_id', '=', od19_ta_plant_id)]",
    )
    od19_ta_source = fields.Selection(
        [("supplied", "Supplied"), ("third_party", "Third Party")],
        string="Source",
        default="supplied",
        tracking=True,
    )
    od19_ta_state = fields.Selection(
        [
            ("in_service", "In Service"),
            ("spare", "Spare"),
            ("repair", "Under Repair"),
            ("scrapped", "Scrapped"),
        ],
        string="ATG Status",
        default="in_service",
        tracking=True,
    )
    od19_ta_function = fields.Char(string="Function")
    od19_ta_install_date = fields.Date(string="Install Date", tracking=True)
    od19_ta_removal_date = fields.Date(string="Removal Date")
    od19_ta_replaces_id = fields.Many2one(
        "maintenance.equipment", string="Replaces", help="อุปกรณ์ที่ถูกแทนที่ด้วยชิ้นนี้"
    )
    od19_ta_replaced_by_ids = fields.One2many(
        "maintenance.equipment",
        "od19_ta_replaces_id",
        string="Replaced By",
        help="อุปกรณ์ที่มาแทนที่ชิ้นนี้",
    )
    od19_ta_job_id = fields.Many2one("project.project", string="Source Job")
    od19_ta_job_no = fields.Char(string="Job No. (legacy)")
    od19_ta_model_code = fields.Char(string="Model Code")
    od19_ta_test_date = fields.Date(string="Factory Test Date")
    od19_ta_opt_pressure = fields.Char(string="Option: Pressure")
    od19_ta_opt_alarm_relay = fields.Char(string="Option: Alarm Relay")
    od19_ta_opt_analog_out = fields.Char(string="Option: Analog Output")
    od19_ta_opt_sil_relay = fields.Char(string="Option: SIL Relay")
    od19_ta_opt_sil_4_20 = fields.Char(string="Option: SIL 4-20 mA")

    @api.onchange("od19_ta_tank_id")
    def _onchange_od19_ta_tank_id(self):
        for equipment in self:
            if equipment.od19_ta_tank_id:
                equipment.od19_ta_plant_id = equipment.od19_ta_tank_id.plant_id

    @api.onchange("od19_ta_plant_id")
    def _onchange_od19_ta_plant_id(self):
        for equipment in self:
            if (
                equipment.od19_ta_tank_id
                and equipment.od19_ta_tank_id.plant_id != equipment.od19_ta_plant_id
            ):
                equipment.od19_ta_tank_id = False
