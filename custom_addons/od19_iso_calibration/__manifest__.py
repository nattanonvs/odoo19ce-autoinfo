{
    "name": "ISO Calibration Management",
    "version": "19.0.1.0.0",
    "category": "Management/ISO",
    "summary": "ISO 9001 / ISO 14001 Calibration and Monitoring Equipment Control",
    "author": "TRAE",
    "license": "LGPL-3",
    "depends": ["od19_iso_document_control", "hr", "maintenance"],
    "data": [
        "security/ir.model.access.csv",
        "data/calibration_data.xml",
        "views/calibration_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
