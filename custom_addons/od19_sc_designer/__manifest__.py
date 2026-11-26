# -*- coding: utf-8 -*-
{
    "name": "OD19 Service Center — Designer",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Services/Service Center",
    "summary": "หน้าจอออกแบบ Service Center (front-end) — ปรับ 5 มิติผ่านเว็บ "
    "(เมนู · ฟิลด์ · ธีม · สูตร · การเชื่อมต่อ) + Preview/Apply/Rollback",
    "description": """
OD19 Service Center — Designer
==============================

ชั้น 2 ของ AutoInfo Service Center: หน้าจอออกแบบผ่านเว็บ (OWL client action)
ให้ผู้ใช้ออกแบบ "หัวใจ" (เอนจิน 5 มิติของ ``od19_sc_core``) ได้เองโดยไม่ต้องเขียนโค้ด

หน้าจอออกแบบ 5 ส่วน
--------------------
* **Menu** — สร้าง/แก้ tree เมนู (กลุ่ม/หน้าต่าง/URL/client action)
* **Field** — เพิ่มฟิลด์ใหม่ หรือแก้ Label/สถานะของฟิลด์เดิม
* **Theme** — ตั้ง design token (สี/ระยะ/มุม) + header แบรนด์
* **Formula** — เขียนสูตรคำนวณ + ปุ่มทดสอบกับข้อมูลจริง
* **Integration** — ตั้ง endpoint (outbound/inbound) + ปุ่มทดสอบเชื่อมต่อ

ทุกหน้าจอมี Preview, Apply และ Rollback (ผ่าน ``od19.sc.revision``)
""",
    "depends": [
        "od19_sc_core",
        "web",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/od19_sc_designer_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "od19_sc_designer/static/src/sc_designer/*.js",
            "od19_sc_designer/static/src/sc_designer/*.xml",
            "od19_sc_designer/static/src/sc_designer/*.scss",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "icon": "/od19_sc_core/static/description/icon.svg",
}
