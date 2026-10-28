# -*- coding: utf-8 -*-
"""Debit Note form (ใบเพิ่มหนี้ / ใบกำกับภาษี).

Odoo 19 port of the legacy ``dtr_accounting_form`` module (report
``F-AC-003``).  The document is a standard ``account.move`` (``out_invoice``)
flagged with ``dncn = 'dn'`` by the ``od19_accounting_dncn`` module, so no
re-basing is required - only the SQL inside ``debit_note_form.jrxml`` is
adapted to the Odoo 19 schema.

The legacy validation combined the two conditions with ``and`` (a bug that let
most documents through); the port uses the intended ``or`` so that only a debit
note can be printed.
"""
from odoo import _, fields, models
from odoo.exceptions import ValidationError

from .invoice_form import DATE_FORMATS


class DebitNoteForm(models.TransientModel):
    _name = "debit.note.form"
    _description = "Debit Note Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Debit Note")
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
        if moves.filtered(lambda move: move.move_type != "out_invoice" or move.dncn != "dn"):
            raise ValidationError(_("Cannot print a document that is not a debit note."))
        self.name = self.get_file_name(ids, "account.move", "Debit Note Report")
        return {
            "ids": "where invoice.id in (%s)" % ", ".join(str(i) for i in ids),
            "iscopy": "%s" % self.env.context.get("iscopy", 0),
            "p_language": self.p_language,
            "p_locale": "th" if self.date_type == "BE" else "en",
            "p_DateFormat": str(self.date_format),
        }

    def show_report(self, report_name=False, email_subject=False, email_document_number=False):
        moves = self.env["account.move"].browse(self.env.context.get("active_ids", []))
        email_subject = "Debit Notes Form"
        if len(moves) == 1:
            email_subject = "Debit Notes Form: %s" % moves.name
            email_document_number = moves.name
            self.can_send_email = True
        return super().show_report(
            email_subject=email_subject,
            email_document_number=email_document_number,
        )
