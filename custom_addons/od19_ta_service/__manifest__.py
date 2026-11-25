# -*- coding: utf-8 -*-
{
    "name": "OD19 TA Service (งานบริการ ATG)",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Services/After-Sales",
    "summary": "โมดูลเสริมประวัติงานบริการ/PM/Event บนฐาน OCA helpdesk_mgmt "
    "— ผูกตั๋วงานเข้ากับทะเบียน ATG (Plant / Tank / อุปกรณ์)",
    "description": """
OD19 TA Service (งานบริการ ATG)
================================

โมดูล *เสริม* (thin supplement) ที่ใช้ **OCA ``helpdesk_mgmt`` เป็นฐานหลัก**
สำหรับบันทึกงานบริการ/บำรุงรักษา (PM), งานแก้ไข (CM), การติดตั้ง,
สอบเทียบ, ตรวจสอบ และ Event ต่าง ๆ แล้วผูกเข้ากับทะเบียน ATG
(``od19_ta_asset``):

* ตั๋วงาน → ``helpdesk.ticket`` (OCA) เพิ่มเฉพาะตำแหน่งติดตั้ง
  (Plant / Tank / อุปกรณ์ ATG) + ประเภทงาน + วันที่ทำงาน + สรุปงาน
* Plant / Tank / อุปกรณ์ ATG → ปุ่ม smart button เปิดดูประวัติงานย้อนหลัง

.. note:: ไม่แตะ Odoo core และไม่แตะ ``third_party/oca/``
    โมดูลนี้ต่อยอดจาก ``od19_ta_asset`` (ทะเบียน) และ ``helpdesk_mgmt`` (งานบริการ)
    """,
    "depends": [
        "od19_ta_asset",
        "helpdesk_mgmt",
    ],
    "data": [
        "security/od19_ta_service_security.xml",
        "views/helpdesk_ticket_views.xml",
        "views/od19_ta_asset_views.xml",
        "views/od19_ta_service_menus.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
