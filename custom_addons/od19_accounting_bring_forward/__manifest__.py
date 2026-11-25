{
    "name": "OD19 Accounting - Bring Forward (ยกยอดปิดงวด)",
    "author": "OD19",
    "version": "19.0.1.0.1",
    "category": "Accounting/Accounting",
    "summary": "ยกยอดคงเหลือเอกสารปิดงวด (AR/AP, CN/DN, Payment, สินทรัพย์ถาวร, "
    "ปรับปรุงสต็อก) ไปงวดใหม่ พร้อมโหมดอัตโนมัติรวมเอกสารและคำนวณ",
    "description": """
OD19 Accounting - Bring Forward (ยกยอดปิดงวด)
==============================================

รวบยอดคงเหลือของเอกสารทุกประเภทก่อนปิดงวดบัญชี แล้วสร้างรายการสมุดรายวัน
(Journal Entry) ยกยอดมาสู่งวดใหม่

ขอบเขตเอกสารที่ยกยอด:

* ใบแจ้งหนี้ลูกค้า / ใบวางบิลผู้ขาย (AR / AP)
* ใบลดหนี้ / ใบเพิ่มหนี้ (CN / DN)
* รับเงิน / จ่ายเงิน (Payment)
* สินทรัพย์ถาวร (ค่าเสื่อมราคา)
* ปรับปรุงสต็อก (Inventory Adjustment)

โหมดการทำงาน:

* **Manual** — ผู้ใช้เลือกเอกสารเอง แล้วกด Compute จากนั้นกรอก Target แล้ว Post
* **Automatic** — ระบบดึงเอกสาร posted ของงวด (Period From .. Period To)
  มา link ให้อัตโนมัติ แล้วคำนวณทันที (Target ยังคงเป็นค่าที่ผู้ใช้กำหนด
  ไม่ post อัตโนมัติ)
    """,
    "depends": [
        "account",
        "stock",
        "account_asset_management",
        "od19_accounting_document_sequence",
        "od19_accounting_dncn",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/od19_bring_forward_security.xml",
        "data/ir_sequence_data.xml",
        "views/od19_bring_forward_views.xml",
        "views/res_config_settings_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "icon": "/od19_accounting_bring_forward/static/description/icon.svg",
}
