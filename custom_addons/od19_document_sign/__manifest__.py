{
    "name": "Document Signing",
    "version": "19.0.1.0.0",
    "summary": "Electronic document signing with templates, roles and customer portal",
    "description": """
Document Signing
================
Sign documents electronically from the backend or from the customer portal.

Features
--------
* Reusable signing templates with an ordered list of signer roles.
* Signing requests (``od19.document``) generated from a template, each with
  its own content, reference and signing deadline.
* One signer line per participant with its own security token so every signer
  can sign independently through the portal.
* Built-in signature pad (Odoo core ``signature`` widget / portal
  ``portal.signature_form``), refusal with a reason and multi-signer status
  aggregation (draft / sent / signed / refused / expired).
* Scheduled job that expires overdue requests.
* QWeb PDF report with the document content and every collected signature.
""",
    "category": "Productivity/Sign",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "portal",
    ],
    "data": [
        "security/od19_document_sign_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/mail_template.xml",
        "data/ir_cron_data.xml",
        "report/document_report.xml",
        "views/document_template_views.xml",
        "views/document_views.xml",
        "views/portal_templates.xml",
        "views/menu_views.xml",
    ],
    "icon": "/od19_document_sign/static/description/icon.svg",
    "installable": True,
    "application": True,
}
