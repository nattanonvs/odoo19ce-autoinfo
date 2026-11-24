# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "OD19 Claim Document Store",
    "version": "19.0.1.0.0",
    "category": "Document Management",
    "summary": "ที่เก็บเอกสารสำหรับทำเรื่องเรียกร้อง/คำขอของบริษัท (หมวด + ทะเบียนแบบฟอร์ม + แฟ้มเรื่องเรียกร้อง)",
    "author": "TRAE",
    "license": "LGPL-3",
    "depends": ["od19_document_hub", "mail", "hr"],
    "data": [
        "security/ir.model.access.csv",
        "data/od19_claim_category_data.xml",
        "data/ir_sequence_data.xml",
        "views/od19_claim_form_views.xml",
        "views/od19_claim_request_views.xml",
        "views/od19_claim_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
