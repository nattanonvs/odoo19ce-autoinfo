# -*- coding: utf-8 -*-
{
    "name": "OD19 Service Center — Portal & Reports",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Services/Service Center",
    "summary": "พอร์ทัลลูกค้า/พนักงานของ Service Center — หน้า self-service และหน้ารายงาน KPI "
    "ที่ผูกกับ Designed Template",
    "description": """
OD19 Service Center — Portal & Reports (ASC · P3)
=================================================

ชั้นพอร์ทัลของแพลตฟอร์ม AutoInfo Service Center (ASC) ตามข้อเสนอ
``docs/superpowers/specs/2026-11-26-od19-service-center-configurable-platform-proposal.md``

แนวคิด: เอนจิน 5 มิติของ ``od19_sc_core`` สร้างเมนู/ฟิลด์/ดีไซน์/สูตร/การเชื่อมต่อ
ให้กลายเป็นของจริง โมดูลนี้ **ไม่เพิ่มมิติที่ 6** แต่เป็น *ผู้บริโภค* — เอา
``od19.sc.template`` ที่ออกแบบไว้มาทำเป็น **หน้าพอร์ทัล** ให้ลูกค้า/พนักงาน
เปิดใช้เองได้ พร้อม **หน้ารายงาน KPI** ที่คำนวณจากข้อมูลจริง

สิ่งที่โมดูลนี้เพิ่ม
-------------------
* ``od19.sc.portal.page`` — ผูกเทมเพลตเข้ากับหน้าพอร์ทัล (published + กลุ่มที่มองเห็นได้)
* ``od19.sc.portal.kpi`` — การ์ดรายงาน: ค่าสถิติ (count/sum/avg/min/max) จาก
  โมเดล + โดเมนที่กำหนดได้อิสระ (ไม่เขียนโค้ด)
* Route พอร์ทัล ``/my/service-center`` และ ``/my/service-center/<id>``
  (ต่อกับ ``portal`` — ลูกค้า/พนักงานเห็นเฉพาะหน้าที่เผยแพร่และได้รับสิทธิ์)
""",
    "depends": [
        "od19_sc_core",
        "portal",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/od19_sc_portal_views.xml",
        "views/od19_sc_portal_menus.xml",
        "views/od19_sc_portal_templates.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "icon": "/od19_sc_portal/static/description/icon.svg",
}
