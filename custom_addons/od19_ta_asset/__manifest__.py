# -*- coding: utf-8 -*-
{
    "name": "OD19 TA Asset Register (ทะเบียนสินทรัพย์ ATG)",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Services/After-Sales",
    "summary": "โมดูลเสริมทะเบียนอุปกรณ์ ATG บนฐานมาตรฐาน "
    "(maintenance.equipment + res.partner) ของ Odoo — ไม่เขียนทะเบียนซ้ำ",
    "description": """
OD19 TA Asset Register (ทะเบียนสินทรัพย์ ATG)
=============================================

โมดูล *เสริม* (thin supplement) ที่ผนวก "TA Asset Register" เข้า Odoo 19
โดย **ใช้ของมาตรฐานเป็นฐานหลัก** แทนการเขียนใหม่ทั้งหมด:

* **เจ้าของไซต์/ลูกค้า** → ``res.partner`` (เพิ่มเฉพาะฟิลด์โดเมน TA)
* **ทะเบียนอุปกรณ์ ATG** → ``maintenance.equipment`` (core) เพิ่มฟิลด์ติดตั้ง
  (Plant / Tank / วันที่ติดตั้ง-ถอด / แหล่งที่มา / Option ต่าง ๆ)
* **Plant (ไซต์) และ Tank (ถัง)** → สร้างใหม่ ``od19.ta.plant`` / ``od19.ta.tank``
  เพราะไม่มีโมดูลมาตรฐาน/OCA ตรงโดเมน (core ถอด ``maintenance.location`` ออกแล้ว)

.. note:: ไม่แตะ Odoo core และไม่แตะ ``third_party/oca/``
    โมดูลนี้เป็น *ฐาน* ของ ``od19_ta_service`` (ประวัติงานบน OCA ``helpdesk_mgmt``)
    """,
    "depends": [
        "base",
        "mail",
        "maintenance",
        "project",
    ],
    "data": [
        "security/od19_ta_security.xml",
        "security/ir.model.access.csv",
        "views/maintenance_equipment_views.xml",
        "views/od19_ta_plant_views.xml",
        "views/od19_ta_tank_views.xml",
        "views/res_partner_views.xml",
        "views/od19_ta_menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "icon": "/od19_ta_asset/static/description/icon.svg",
}
