# -*- coding: utf-8 -*-
"""Pilot Jasper form: Customer Invoice / Vendor Bill print.

This is the Odoo 19 port of the legacy ``dtr_accounting_form`` module
(report ``F-AC-001``), and it doubles as the reference implementation for the
other Jasper print forms: inherit :class:`od19.jasper.report`, declare the
parameters, override :meth:`get_parameters`, and inherit the shared wizard view.

The legacy "running line sequence" step (which wrote ``report_sequence`` on the
invoice lines to control the print order) is not needed any more - Odoo 19
already stores the print order in ``account.move.line.sequence``, which the
ported ``invoice_form.jrxml`` reads directly.
"""
from odoo import _, fields, models
from odoo.exceptions import ValidationError

DATE_FORMATS = (
    "dd/MM/yy",
    "dd/MMM/yy",
    "MM/dd/yy",
    "MMM/dd/yy",
    "dd/MM/yyyy",
    "dd/MMM/yyyy",
    "MM/dd/yyyy",
    "MMM/dd/yyyy",
    "yy/dd/MM",
    "yy/dd/MMM",
    "yy/MM/dd",
    "yy/MMM/dd",
    "yyyy/dd/MM",
    "yyyy/dd/MMM",
    "yyyy/MM/dd",
    "yyyy/MMM/dd",
    "dd-MM-yy",
    "dd-MMM-yy",
    "MM-dd-yy",
    "MMM-dd-yy",
    "dd-MM-yyyy",
    "dd-MMM-yyyy",
    "MM-dd-yyyy",
    "MMM-dd-yyyy",
    "yy-dd-MM",
    "yy-dd-MMM",
    "yy-MM-dd",
    "yy-MMM-dd",
    "yyyy-dd-MM",
    "yyyy-dd-MMM",
    "yyyy-MM-dd",
    "yyyy-MMM-dd",
)


class InvoiceForm(models.TransientModel):
    _name = "invoice.form"
    _description = "Customer Invoice Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Invoice")
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

    def get_partner_ids_for_send_by_email(self):
        moves = self.env["account.move"].browse(self.env.context.get("active_ids", []))
        return moves.mapped("partner_id")

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        ids = self.env.context.get("active_ids") or []
        moves = self.env["account.move"].browse(ids)
        invalid = moves.filtered(
            lambda move: move.move_type not in ("in_invoice", "out_invoice")
            or move.dncn in ("dn", "cn")
        )
        if invalid:
            raise ValidationError(
                _("Cannot print a document that is not a customer invoice or a vendor bill.")
            )
        self.name = self.get_file_name(ids, "account.move", "Invoice Report")
        return {
            "ids": "where invoice.id in (%s)" % ", ".join(str(i) for i in ids),
            "iscopy": "%s" % self.env.context.get("iscopy", 0),
            "p_language": self.p_language,
            "p_locale": "th" if self.date_type == "BE" else "en",
            "p_DateFormat": str(self.date_format),
        }

    def show_report(self, report_name=False, email_subject=False, email_document_number=False):
        moves = self.env["account.move"].browse(self.env.context.get("active_ids", []))
        email_subject = "Customer Invoices Form"
        if len(moves) == 1:
            email_subject = "Customer Invoices Form: %s" % moves.name
            email_document_number = moves.name
            self.can_send_email = True
        return super().show_report(
            email_subject=email_subject,
            email_document_number=email_document_number,
        )
