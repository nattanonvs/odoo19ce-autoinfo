# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models

#: Families that map one-to-one onto a journal entry type. The customer
#: invoice is handled separately because its family depends on the buyer, and
#: the commercial invoice (380) and the cancellation note (T07) are issued
#: outside a single sale cycle, so they stay a manual choice.
_DEFAULT_TYPE_BY_MOVE = {
    "out_receipt": "receipt",
}


class AccountMove(models.Model):
    _inherit = "account.move"

    od19_etax_document_ids = fields.One2many(
        "od19.etax.document",
        "move_id",
        string="e-Tax Documents",
        copy=False,
    )
    od19_etax_document_count = fields.Integer(
        string="e-Tax Document Count",
        compute="_compute_od19_etax_document_count",
    )
    od19_etax_state = fields.Selection(
        [
            ("none", "Not Issued"),
            ("draft", "Draft"),
            ("generated", "XML Generated"),
            ("signed", "Signed"),
            ("cancelled", "Cancelled"),
        ],
        string="e-Tax Status",
        compute="_compute_od19_etax_state",
    )
    od19_etax_enabled = fields.Boolean(
        related="company_id.od19_etax_enabled",
        string="e-Tax Invoice Enabled",
        readonly=True,
    )

    @api.depends("od19_etax_document_ids")
    def _compute_od19_etax_document_count(self):
        for move in self:
            move.od19_etax_document_count = len(move.od19_etax_document_ids)

    @api.depends("od19_etax_document_ids.state")
    def _compute_od19_etax_state(self):
        for move in self:
            documents = move.od19_etax_document_ids
            if not documents:
                move.od19_etax_state = "none"
            elif "signed" in documents.mapped("state"):
                move.od19_etax_state = "signed"
            elif "generated" in documents.mapped("state"):
                move.od19_etax_state = "generated"
            elif "draft" in documents.mapped("state"):
                move.od19_etax_state = "draft"
            else:
                move.od19_etax_state = "cancelled"

    def _od19_etax_default_type(self):
        """Return the document type matching the journal entry.

        The journal entry alone cannot name every family: the commercial
        invoice (380) and the cancellation note (T07) are issued outside a
        single sale cycle, so they remain a manual choice. The remaining
        families are derived from the entry:

        * a debit/credit note (od19_accounting_dncn) is classified through
          ``dncn`` before the entry type, because Odoo posts a debit note as an
          ``out_invoice``;
        * a VAT-registered buyer must receive the full-form tax invoice (388),
          while a consumer sale may use the abbreviated form (T05, ม.86/6),
          matching how ``od19_thai_tax_reports`` resolves the Thai legal type;
        * a sales receipt (``out_receipt``) is reported as a Receipt (T01).
        """
        self.ensure_one()
        if self.dncn in ("dn", "cn"):
            return "debit_credit_note"
        if self.move_type == "out_invoice":
            return (
                "tax_invoice"
                if self.partner_id.vat
                else "abbreviated_tax_invoice"
            )
        if self.move_type == "out_refund":
            return "debit_credit_note"
        return _DEFAULT_TYPE_BY_MOVE.get(self.move_type, "tax_invoice")

    def action_od19_create_etax_document(self):
        """Create (or open) the e-Tax document of this journal entry."""
        self.ensure_one()
        document = self.od19_etax_document_ids[:1]
        if not document:
            document = self.env["od19.etax.document"].create({
                "move_id": self.id,
                "company_id": self.company_id.id,
                "document_type": self._od19_etax_default_type(),
            })
        return {
            "type": "ir.actions.act_window",
            "res_model": "od19.etax.document",
            "res_id": document.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_od19_view_etax_documents(self):
        """Open the list of e-Tax documents of this journal entry."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("e-Tax Documents"),
            "res_model": "od19.etax.document",
            "view_mode": "list,form",
            "domain": [("move_id", "=", self.id)],
            "context": {"default_move_id": self.id},
        }
