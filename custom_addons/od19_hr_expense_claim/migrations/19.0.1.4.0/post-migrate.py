# -*- coding: utf-8 -*-
"""อัปเดต definition_domain ของชั้น CEO ให้ยกเว้นเงินสดย่อย (petty_cash).

ไฟล์ data ``tier_definition_data.xml`` เป็น ``noupdate=1`` จึงไม่ถูกอัปเดต
อัตโนมัติเมื่อ ``-u`` ต้องอัปเดต record ที่ค้างในฐานข้อมูลตรงนี้
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

NEW_DOMAIN = "[('claim_type', '!=', 'petty_cash')]"


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ceo_def = env.ref(
        "od19_hr_expense_claim.tier_definition_claim_ceo",
        raise_if_not_found=False,
    )
    if ceo_def and ceo_def.definition_domain != NEW_DOMAIN:
        ceo_def.definition_domain = NEW_DOMAIN
        _logger.info("Updated CEO tier definition domain to skip petty_cash")
