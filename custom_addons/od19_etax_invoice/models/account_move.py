# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models

_DEFAULT_TYPE_BY_MOVE = {
    "out_invoice": "tax_invoice",
    "out_refund": "debit_credit_note",
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
        """Return the document type matching the journal entry type."""
        self.ensure_one()
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
