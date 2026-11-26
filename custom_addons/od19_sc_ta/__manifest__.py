# -*- coding: utf-8 -*-
{
    "name": "OD19 Service Center — Template 01 (TA)",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Services/Service Center",
    "summary": "เทมเพลต 01 (แผนก TA): TA Service & Equipment Workload Monitoring — "
    "เมนู · ฟิลด์ · ธีม · สูตรภาระงาน · การเชื่อมต่อ สำหรับ Service Center",
    "description": """
OD19 Service Center — Template 01 (TA)
======================================

Designed Template ชุดแรกของแพลตฟอร์ม AutoInfo Service Center (ASC)
ตามข้อเสนอ ``docs/superpowers/specs/2026-11-26-od19-service-center-configurable-platform-proposal.md``

* **Department:** TA
* **Designed Template:** 01 (code ``TA-01``)
* **Design Header Name:** TA Service & Equipment Workload Monitoring

เทมเพลตนี้เป็น *ข้อมูล* ทั้งหมด (od19.sc.template + 5 มิติ) — ไม่แก้ Odoo core
ติดตั้งแล้ว apply อัตโนมัติผ่าน ``post_init_hook`` ให้กลายเป็นของจริง
(``ir.ui.menu`` · ``ir.model.fields`` · ``ir.asset`` · ``ir.cron``) และยัง
แก้ไข/ออกแบบต่อได้จากหน้าจอ Designer ของ ``od19_sc_designer``

มิติทั้ง 5
---------
* **เมนู** — ทะเบียนอุปกรณ์ · งานบริการ · การติดตามภาระงาน · ลูกค้า · Service Designer
* **ฟิลด์** — รหัสทรัพย์สิน · โซนบริการ · ความสำคัญวิกฤต · ช่องทางรับงาน · SLA · คะแนนภาระงาน
* **ดีไซน์** — Liquid Glass (design tokens) + header แบรนด์
* **สูตร** — คะแนนภาระงานต่อคนต่อช่วงเวลา (Workload Points) + ป้ายงานบริการ (Scheduled)
* **การเชื่อมต่อ** — push snapshot อุปกรณ์ไปยังระบบเดิม (API) + webhook ขาเข้า
""",
    "depends": [
        "od19_sc_core",
        "maintenance",
    ],
    "data": [
        "data/od19_sc_ta_template.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
