# -*- coding: utf-8 -*-
"""Customer Receipt form (ใบเสร็จรับเงิน).

Odoo 19 port of the legacy ``dtr_accounting_form`` module (report
``F-AC-007``).  The document is a standard ``account.payment``; the SQL in
``receipt_form.jrxml`` is adapted to the Odoo 19 schema (see the template
header for the field mapping).
"""
from odoo import _, fields, models

from .invoice_form import DATE_FORMATS


class ReceiptForm(models.TransientModel):
    _name = "receipt.form"
    _description = "Receipt Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Receipt Form")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Language",
        default="thai",
        required=True,
    )
    p_Tax = fields.Selection(
        [("1", "Receipt"), ("2", "Tax Invoice / Receipt")],
        string="Type Receipt",
        default="1",
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
        payments = self.env["account.payment"].browse(self.env.context.get("active_ids", []))
        return payments.mapped("partner_id")

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        ids = self.env.context.get("active_ids") or []
        self.name = self.get_file_name(ids, "account.payment", "Receipt Report")
        return {
            "ids": "WHERE pay.id in (%s)" % ", ".join(str(i) for i in ids),
            "p_language": str(self.p_language),
            "p_Tax": str(self.p_Tax),
            "p_Path": self._legacy_filestore_path(),
            "p_ISO": self.iso_no or "",
            "p_EName": str(self.p_EName),
            "p_ESignature": str(self.p_ESignature),
            "p_DateFormat": str(self.date_format),
            "p_Iscopy": "%s" % self.env.context.get("iscopy", 0),
            "p_locale": "th" if self.date_type == "BE" else "en",
        }

    def show_report(self, report_name=False, email_subject=False, email_document_number=False):
        payments = self.env["account.payment"].browse(self.env.context.get("active_ids", []))
        email_subject = "Customer Receipt Form"
        if len(payments) == 1:
            email_subject = "Customer Receipt Form: %s" % payments.name
            email_document_number = payments.name
            self.can_send_email = True
        return super().show_report(
            email_subject=email_subject,
            email_document_number=email_document_number,
        )
