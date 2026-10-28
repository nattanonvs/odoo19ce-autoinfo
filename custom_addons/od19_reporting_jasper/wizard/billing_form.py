# -*- coding: utf-8 -*-
"""Billing Form (ใบวางบิล).

Odoo 19 port of the legacy ``dtr_accounting_form`` module (report
``F-AC-005``).  The legacy document was the custom ``dtr.account.billing``
model, which does not exist in Odoo 19; per the agreed strategy the form is
**re-based on the standard ``account.move``** (customer invoice) - the selected
invoice acts as the billing document and the SQL in ``billing_form.jrxml``
reads the Odoo 19 schema directly.
"""
from odoo import _, fields, models

from .invoice_form import DATE_FORMATS


class BillingForm(models.TransientModel):
    _name = "billing.form"
    _description = "Billing Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Billing Form")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Language",
        default="thai",
        required=True,
    )
    date_type = fields.Selection(
        [("AD", "AD"), ("BE", "BE")],
        string="Date Type",
        default="AD",
        required=True,
        help="AD = คริสตศักราช\nBE = พุทธศักราช",
    )
    date_format = fields.Selection(
        [(value, value) for value in DATE_FORMATS],
        string="Date Format",
        default="dd-MM-yyyy",
        required=True,
    )
    p_EName = fields.Boolean(
        string="Show Employee Name",
        default=True,
        help="พิมพ์ชื่อผู้จัดทำ / ผู้ตรวจสอบ / ผู้อนุมัติ ในช่องลงนาม",
    )
    p_ESignature = fields.Boolean(
        string="Show Signature",
        default=True,
        help="พิมพ์รูปลายเซ็นพนักงานในช่องลงนาม",
    )

    def get_partner_ids_for_send_by_email(self):
        moves = self.env["account.move"].browse(self.env.context.get("active_ids", []))
        return moves.mapped("partner_id")

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        ids = self.env.context.get("active_ids") or []
        self.name = self.get_file_name(ids, "account.move", "Billing Report")
        return {
            "ids": "WHERE bill.id in (%s)" % ", ".join(str(i) for i in ids),
            "p_language": self.p_language,
            "p_Path": self._legacy_filestore_path(),
            "p_ISO": self.iso_no or "",
            "p_EName": str(self.p_EName),
            "p_ESignature": str(self.p_ESignature),
            "p_DateFormat": str(self.date_format),
            "p_Iscopy": "%s" % self.env.context.get("iscopy", 0),
            "p_locale": "th" if self.date_type == "BE" else "en",
        }

    def show_report(self, report_name=False, email_subject=False, email_document_number=False):
        moves = self.env["account.move"].browse(self.env.context.get("active_ids", []))
        email_subject = "Billing Form"
        if len(moves) == 1:
            email_subject = "Billing Form: %s" % moves.name
            email_document_number = moves.name
            self.can_send_email = True
        return super().show_report(
            email_subject=email_subject,
            email_document_number=email_document_number,
        )
