# -*- coding: utf-8 -*-
{
    "name": "Project Document Sequence (OD19)",
    "version": "1.0.0",
    "summary": "Job/Server/PM/Service numbering with dept + sales initials + year + sequence",
    "description": """
Adds department-based document sequences for project documents.
Job Number format: J + dept_code + sales_initials + year + sequence
Same format for Server (SV), Preventive Maintenance (PM), Service (S).
Task Code format: T + dept_code + sales_initials + sequence.
    """,
    "author": "OD19 Custom",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": [
        "project",
        "hr",
        "od19_purchase_document_sequence",
    ],
    "data": [
        "data/ir_sequence_data.xml",
        "views/hr_department_views.xml",
        "views/res_users_views.xml",
        "views/project_project_views.xml",
        "views/project_task_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
