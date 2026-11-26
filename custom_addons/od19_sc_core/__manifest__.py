# -*- coding: utf-8 -*-
{
    "name": "OD19 Service Center — Config Engine (ASC)",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Services/Service Center",
    "summary": "เอนจินกลางของ AutoInfo Service Center (ASC) — ปรับแต่ง 5 มิติ "
    "(เมนู · ฟิลด์/Label · ดีไซน์ · การคำนวณ · การเชื่อมต่อ) เป็นข้อมูล ไม่ใช่โค้ด",
    "description": """
OD19 Service Center Config Engine (ASC)
=======================================

ชั้น 1 (เอนจิน) ของแพลตฟอร์มบริการที่ปรับแต่งได้อิสระ ตามข้อเสนอ
``docs/superpowers/specs/2026-11-26-od19-service-center-configurable-platform-proposal.md``

แนวคิด: ทุกสิ่งที่ "เปลี่ยนได้" เก็บเป็น *ข้อมูล* (record) ไม่ใช่โค้ด แล้ว "apply"
ให้กลายเป็นของจริงผ่านจุดต่อขยายที่ Odoo 19 รองรับ — ไม่แตะ Odoo core

5 มิติที่เอนจินจัดการ
---------------------
* **Menu** — ``od19.sc.menu.node`` → ``ir.ui.menu`` + ``ir.actions.*``
* **Field/Label** — ``od19.sc.field.def`` → ``ir.model.fields`` (manual) + ``ir.ui.view`` inherit
* **Design** — ``od19.sc.design.token`` → ``ir.attachment`` + ``ir.asset`` (CSS bundle)
* **Calculation** — ``od19.sc.formula`` → ``base.automation`` + ``ir.actions.server`` / ``ir.cron``
* **Integration** — ``od19.sc.integration.endpoint`` → controller (inbound) / requests + ``ir.cron``

ทุกมิติมี ``od19.sc.revision`` เก็บ snapshot ก่อน apply → ย้อนกลับได้เสมอ
""",
    "depends": [
        "base",
        "mail",
        "web",
        "base_automation",
    ],
    "data": [
        "security/od19_sc_security.xml",
        "security/ir.model.access.csv",
        "views/od19_sc_views.xml",
        "views/od19_sc_menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "icon": "/od19_sc_core/static/description/icon.svg",
}
