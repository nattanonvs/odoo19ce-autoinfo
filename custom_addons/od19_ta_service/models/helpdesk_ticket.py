# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    """โมดูล *เสริม* บน OCA ``helpdesk_mgmt`` — ผูกตั๋วงานบริการเข้ากับทะเบียน ATG.

    ใช้ ``helpdesk.ticket`` เป็นฐานหลัก (ไม่สร้างโมเดลงานบริการซ้ำ) แล้วเพิ่ม
    เฉพาะข้อมูลตำแหน่ง/อุปกรณ์ ATG, ประเภทงาน และสรุปงาน
    """

    _inherit = "helpdesk.ticket"

    od19_ta_plant_id = fields.Many2one(
        "od19.ta.plant", string="TA Plant", tracking=True, index=True
    )
    od19_ta_tank_id = fields.Many2one(
        "od19.ta.tank",
        string="TA Tank",
        tracking=True,
        domain="[('plant_id', '=', od19_ta_plant_id)]",
    )
    od19_ta_equipment_id = fields.Many2one(
        "maintenance.equipment",
        string="ATG Equipment",
        tracking=True,
        domain="[('od19_ta_plant_id', '=', od19_ta_plant_id)]",
    )
    od19_ta_is_ta = fields.Boolean(
        string="TA Service",
        compute="_compute_od19_ta_is_ta",
        store=True,
        index=True,
        help="ตั๋วนี้ผูกกับไซต์ (Plant) ของทะเบียน ATG",
    )
    od19_ta_job_type = fields.Selection(
        [
            ("pm", "Preventive (PM)"),
            ("cm", "Corrective (CM)"),
            ("installation", "Installation"),
            ("calibration", "Calibration"),
            ("inspection", "Inspection"),
            ("event", "Event / Other"),
        ],
        string="Job Type",
        tracking=True,
    )
    od19_ta_work_date = fields.Date(string="Work Date", tracking=True)
    od19_ta_work_summary = fields.Html(string="Work Summary")

    @api.depends("od19_ta_plant_id")
    def _compute_od19_ta_is_ta(self):
        for ticket in self:
            ticket.od19_ta_is_ta = bool(ticket.od19_ta_plant_id)

    @api.onchange("od19_ta_tank_id")
    def _onchange_od19_ta_tank_id(self):
        for ticket in self:
            if ticket.od19_ta_tank_id:
                ticket.od19_ta_plant_id = ticket.od19_ta_tank_id.plant_id

    @api.onchange("od19_ta_equipment_id")
    def _onchange_od19_ta_equipment_id(self):
        for ticket in self:
            equipment = ticket.od19_ta_equipment_id
            if not equipment:
                continue
            if equipment.od19_ta_plant_id:
                ticket.od19_ta_plant_id = equipment.od19_ta_plant_id
            if equipment.od19_ta_tank_id:
                ticket.od19_ta_tank_id = equipment.od19_ta_tank_id

    @api.onchange("od19_ta_plant_id")
    def _onchange_od19_ta_plant_id(self):
        for ticket in self:
            plant = ticket.od19_ta_plant_id
            if (
                ticket.od19_ta_tank_id
                and ticket.od19_ta_tank_id.plant_id != plant
            ):
                ticket.od19_ta_tank_id = False
            if (
                ticket.od19_ta_equipment_id
                and ticket.od19_ta_equipment_id.od19_ta_plant_id != plant
            ):
                ticket.od19_ta_equipment_id = False
            if plant and not ticket.partner_id:
                ticket.partner_id = plant.partner_id
