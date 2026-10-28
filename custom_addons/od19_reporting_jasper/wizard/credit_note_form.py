# -*- coding: utf-8 -*-
"""Credit Note form (ใบลดหนี้ / ใบกำกับภาษี).

Odoo 19 port of the legacy ``dtr_accounting_form`` module (report
``F-AC-002``).  The document is a standard ``account.move`` refund, so no
re-basing is required - only the SQL inside ``credit_note_form.jrxml`` is
adapted to the Odoo 19 schema (see the template header for the mapping).

The legacy "Running Line Sequence" step (which wrote ``report_sequence`` on the
invoice lines so the printed order matched the screen) is not needed any more:
Odoo 19 stores the print order directly in ``account.move.line.sequence``.
"""
from odoo import _, fields, models
from odoo.exceptions import ValidationError

from .invoice_form import DATE_FORMATS


class CreditNoteForm(models.TransientModel):
    _name = "credit.note.form"
    _description = "Credit Note Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Credit Note")
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
        if moves.filtered(lambda move: move.move_type not in ("out_refund", "in_refund")):
            raise ValidationError(_("Cannot print a document that is not a credit note."))
        self.name = self.get_file_name(ids, "account.move", "Credit Note Report")
        return {
            "ids": "where invoice.id in (%s)" % ", ".join(str(i) for i in ids),
            "iscopy": "%s" % self.env.context.get("iscopy", 0),
            "p_language": self.p_language,
            "p_locale": "th" if self.date_type == "BE" else "en",
            "p_DateFormat": str(self.date_format),
        }

    def show_report(self, report_name=False, email_subject=False, email_document_number=False):
        moves = self.env["account.move"].browse(self.env.context.get("active_ids", []))
        email_subject = "Credit Notes Form"
        if len(moves) == 1:
            email_subject = "Credit Notes Form: %s" % moves.name
            email_document_number = moves.name
            self.can_send_email = True
        return super().show_report(
            email_subject=email_subject,
            email_document_number=email_document_number,
        )
