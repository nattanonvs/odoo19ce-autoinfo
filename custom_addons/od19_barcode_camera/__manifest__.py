# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

{
    "name": "OD19 Barcode Camera",
    "version": "19.0.1.0.0",
    "author": "OD19",
    "category": "Inventory/Inventory",
    "summary": "สแกนบาร์โค้ดด้วยกล้องมือถือสำหรับงานคลังสินค้า "
    "(รับ/ส่ง/นับสต็อก) พร้อมประวัติการสแกน",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "product",
        "stock",
        "barcodes",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/od19_barcode_scan_log_views.xml",
        "views/stock_picking_views.xml",
        "views/od19_barcode_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "od19_barcode_camera/static/src/scss/od19_barcode.scss",
            "od19_barcode_camera/static/src/xml/barcode_scanner_action.xml",
            "od19_barcode_camera/static/src/js/barcode_scanner_action.js",
        ],
    },
    "installable": True,
    "application": True,
}
