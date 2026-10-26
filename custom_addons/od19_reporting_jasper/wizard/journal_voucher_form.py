# -*- coding: utf-8 -*-
"""Journal Voucher / WHT form (ใบสำคัญจ่าย + หนังสือรับรองการหักภาษี ณ ที่จ่าย).

Fifth Jasmine print form ported from the legacy ``dtr_accounting_form`` module
(report ``F-AC-004``).  Unlike the four previous ports this template is a small
*subreport chain*: the main ``journal_voucher_form.jrxml`` renders the voucher
header, the debit/credit lines and the signature block, and its group footer
embeds two subreports -

* ``journal_voucher_tax_form.jasper`` (the input-VAT lines), and
* ``journal_voucher_wht_form.jasper`` (the withholding-tax certificate lines).

All three ``.jasper`` files must therefore live in the same ``jrxml/`` folder so
that the ``-r`` resource directory resolves the subreport names.

Odoo 19 adaptations applied to the three templates:

* ``dtr_vat`` is replaced by ``account_move_tax_invoice`` (``tax_invoice_number``,
  ``tax_invoice_date``, ``tax_base_amount``, ``balance``, ``tax_line_id``).
* ``dtr_wht`` is replaced by ``account.withholding.move`` (``amount_income``,
  ``amount_wht``, ``wht_cert_income_desc``, ``wht_cert_income_type``,
  ``wht_tax_id``) and its certificate description/income type.
* ``account_move`` has no ``voucher_running_no`` / ``je_type`` and
  ``account_journal`` has no ``voucher_title_*`` - those columns print empty.
* ``account_account`` reads ``code_store`` (company aware) and the translated
  ``name``; ``account_journal.name`` is translated too.
* The legacy employee lookups are rebuilt from ``resource_resource.user_id`` ->
  ``hr_employee`` -> ``hr_version`` (department via ``hr_department``, position
  via ``hr_job``) and the signature image from the ``hr.employee`` signature
  attachment.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError

from .invoice_form import DATE_FORMATS


class JournalVoucherForm(models.TransientModel):
    _name = "journal.voucher.form"
    _description = "Journal Voucher Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Journal Voucher Form")
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

    def _legacy_active_ids(self):
        ids = self.env.context.get("active_ids") or []
        if not ids:
            raise UserError(_("No document selected."))
        return ids

    def _legacy_filestore_path(self):
        """Absolute filestore folder, used to load the signature images."""
        path = self.env["ir.attachment"]._filestore()
        return path.replace("\\", "/") + "/"

    def get_partner_ids_for_send_by_email(self):
        moves = self.env["account.move"].browse(self.env.context.get("active_ids", []))
        return moves.mapped("partner_id")

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        ids = self._legacy_active_ids()
        moves = self.env["account.move"].browse(ids)
        condition = "WHERE al.balance != 0 AND am.id in ({0})".format(
            ", ".join(str(i) for i in ids)
        )
        self.name = self.get_file_name(ids, "account.move", "Journal-Voucher Report")
        return {
            "p_ID": condition,
            "p_Path": self._legacy_filestore_path(),
            "p_ISO": self.iso_no or "",
            "p_EName": str(self.p_EName),
            "p_ESignature": str(self.p_ESignature),
            "p_language": self.p_language,
            "p_DateFormat": str(self.date_format),
            "p_locale": "th" if self.date_type == "BE" else "en",
        }

    def show_report(self, report_name=False, email_subject=False, email_document_number=False):
        moves = self.env["account.move"].browse(self.env.context.get("active_ids", []))
        email_subject = "Journal Voucher Form"
        if len(moves) == 1:
            email_subject = "Journal Voucher Form: %s" % moves.name
            email_document_number = moves.name
            self.can_send_email = True
        return super().show_report(
            email_subject=email_subject,
            email_document_number=email_document_number,
        )
