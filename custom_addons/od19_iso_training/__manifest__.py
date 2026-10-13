{
    "name": "ISO Training & Competence",
    "version": "19.0.1.0.0",
    "category": "Management/ISO",
    "summary": "ISO 9001 / ISO 14001 Training, Awareness and Competence",
    "author": "TRAE",
    "license": "LGPL-3",
    "depends": ["od19_iso_document_control", "hr"],
    "data": [
        "security/ir.model.access.csv",
        "data/training_data.xml",
        "views/training_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
