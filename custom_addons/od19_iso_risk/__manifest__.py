{
    "name": "ISO Risk & Opportunity",
    "version": "19.0.1.0.0",
    "category": "Management/ISO",
    "summary": "ISO 9001 / ISO 14001 Risk and Opportunity Management",
    "author": "TRAE",
    "license": "LGPL-3",
    "depends": ["od19_iso_document_control", "hr"],
    "data": [
        "security/ir.model.access.csv",
        "data/risk_data.xml",
        "views/risk_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
