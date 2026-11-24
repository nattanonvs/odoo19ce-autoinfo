# -*- coding: utf-8 -*-
"""ลบ tier.definition 3 รายการบน hr.expense ที่เคย seed ไว้ (ย้ายไปหัวใบแล้ว).

ไฟล์ data เดิมเป็น ``noupdate=1`` จึงไม่ถูกลบอัตโนมัติเมื่อถอดออกจาก manifest
ต้องลบ record + ir.model.data ที่ค้างในฐานข้อมูล
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    xmlids = [
        "od19_hr_expense_thai.tier_definition_hr_expense_manager",
        "od19_hr_expense_thai.tier_definition_hr_expense_accounting",
        "od19_hr_expense_thai.tier_definition_hr_expense_ceo",
    ]
    definitions = env["tier.definition"].browse()
    for xmlid in xmlids:
        rec = env.ref(xmlid, raise_if_not_found=False)
        if rec:
            definitions |= rec
    if definitions:
        # ล้าง review ที่อ้างถึงก่อน (กัน FK/ตรวจสอบตอน unlink)
        env["tier.review"].search([("definition_id", "in", definitions.ids)]).unlink()
        _logger.info("Removing %s legacy hr.expense tier definition(s)", len(definitions))
        definitions.unlink()
    # ทำความสะอาด ir.model.data ที่อาจค้าง
    stray = env["ir.model.data"].search([
        ("module", "=", "od19_hr_expense_thai"),
        ("name", "in", [x.split(".")[-1] for x in xmlids]),
    ])
    if stray:
        stray.unlink()
