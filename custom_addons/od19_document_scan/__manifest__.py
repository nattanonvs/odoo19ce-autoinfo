# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

{
    "name": "OD19 Document Scan",
    "version": "19.0.1.0.0",
    "author": "OD19",
    "category": "Productivity/Document",
    "summary": "สแกนเอกสาร/ภาพถ่ายด้วยกล้องมือถือ แปลงเป็นบทความ Knowledge "
    "(OCR) และแนบภาพถ่ายจากกล้องใน chatter ทุกที่ในระบบ",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "web",
        "document_page",
        "document_knowledge",
        "od19_knowledge_enhanced",
        "od19_document_hub",
        "od19_ai_assistant",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/od19_scan_article_wizard_views.xml",
        "views/od19_scan_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "od19_document_scan/static/src/scss/od19_scan.scss",
            "od19_document_scan/static/src/xml/camera_dialog.xml",
            "od19_document_scan/static/src/xml/chatter_camera.xml",
            "od19_document_scan/static/src/xml/scan_camera_field.xml",
            "od19_document_scan/static/src/js/image_utils.js",
            "od19_document_scan/static/src/js/camera_dialog.js",
            "od19_document_scan/static/src/js/chatter_camera_patch.js",
            "od19_document_scan/static/src/js/scan_camera_field.js",
        ],
    },
    "installable": True,
    "application": True,
}
