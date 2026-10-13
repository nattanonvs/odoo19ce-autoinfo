# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    dncn = fields.Selection(
        [
            ("dn", "Debit Note (ใบเพิ่มหนี้)"),
            ("cn", "Credit Note (ใบลดหนี้)"),
            ("re", "Remaster Invoice (ออกใบแจ้งหนี้ใหม่)"),
        ],
        string="DN/CN/Remaster",
        copy=False,
    )
    parent_id = fields.Many2one(
        "account.move",
        string="Parent Invoice",
        ondelete="cascade",
        copy=False,
        help="Original invoice that this DN/CN/Remaster belongs to",
    )
    child_ids = fields.One2many(
        "account.move",
        "parent_id",
        string="Debit/Credit Notes",
        copy=False,
    )
    reason_id = fields.Many2one(
        "account.move.dncn.reason",
        string="Reason",
        copy=False,
    )
    remark = fields.Text(
        string="Remark/Reason Description",
        copy=False,
    )

    # Partner tax info snapshot (for tax invoice printing)
    partner_tax_name = fields.Char(
        string="Tax Invoice Name",
        copy=False,
        help="Partner name as shown on tax invoice",
    )
    partner_branch_code = fields.Char(
        string="Branch Code",
        size=5,
        copy=False,
    )

    def _prepare_dncn_defaults(self, dncn_type):
        self.ensure_one()
        return {
            "dncn": dncn_type,
            "parent_id": self.id,
            "partner_id": self.partner_id.id,
            "partner_tax_name": self.partner_id.tax_name or self.partner_id.name,
            "partner_branch_code": self.partner_id.branch_code,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "fiscal_position_id": self.fiscal_position_id.id,
            "invoice_origin": self.name,
            "payment_reference": self.payment_reference,
            "invoice_date": fields.Date.context_today(self),
        }

    def action_create_debit_note(self):
        """Create a Debit Note (ใบเพิ่มหนี้) from the current invoice."""
        self.ensure_one()
        defaults = self._prepare_dncn_defaults("dn")
        defaults["move_type"] = self.move_type  # same type as parent
        defaults["journal_id"] = self.journal_id.id

        # Copy invoice lines with zero price (for adding charges/tax)
        line_vals = []
        for line in self.invoice_line_ids:
            line_vals.append((0, 0, {
                "product_id": line.product_id.id,
                "name": line.name,
                "account_id": line.account_id.id,
                "quantity": line.quantity,
                "price_unit": 0.0,
                "tax_ids": [(6, 0, line.tax_ids.ids)],
            }))
        defaults["invoice_line_ids"] = line_vals

        new_move = self.env["account.move"].create(defaults)
        return {
            "type": "ir.actions.act_window",
            "name": "Debit Note",
            "res_model": "account.move",
            "res_id": new_move.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_create_credit_note(self):
        """Create a Credit Note (ใบลดหนี้) - uses Odoo standard refund."""
        self.ensure_one()
        # Use Odoo standard reversal/refund
        action = self.env.ref("account.action_move_out_refund_type").sudo()
        # Create a credit note via standard reversal
        ctx = dict(self.env.context)
        ctx.update({
            "default_move_type": self.move_type.replace("invoice", "refund"),
            "default_dncn": "cn",
            "default_parent_id": self.id,
            "default_partner_tax_name": self.partner_id.tax_name or self.partner_id.name,
            "default_partner_branch_code": self.partner_id.branch_code,
            "default_invoice_origin": self.name,
        })
        return {
            "type": "ir.actions.act_window",
            "name": "Credit Note",
            "res_model": "account.move",
            "view_mode": "form",
            "target": "current",
            "context": ctx,
        }

    def action_remaster_invoice(self):
        """Create a Remaster Invoice (ออกใบแจ้งหนี้ใหม่) - copy of original."""
        self.ensure_one()
        defaults = self._prepare_dncn_defaults("re")
        defaults["move_type"] = self.move_type
        defaults["journal_id"] = self.journal_id.id

        # Copy invoice lines
        line_vals = []
        for line in self.invoice_line_ids:
            line_vals.append((0, 0, {
                "product_id": line.product_id.id,
                "name": line.name,
                "account_id": line.account_id.id,
                "quantity": line.quantity,
                "price_unit": line.price_unit,
                "tax_ids": [(6, 0, line.tax_ids.ids)],
            }))
        defaults["invoice_line_ids"] = line_vals

        new_move = self.env["account.move"].create(defaults)
        return {
            "type": "ir.actions.act_window",
            "name": "Remaster Invoice",
            "res_model": "account.move",
            "res_id": new_move.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_parent(self):
        """Open the parent invoice."""
        self.ensure_one()
        if not self.parent_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.parent_id.id,
            "view_mode": "form",
            "target": "current",
        }


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    dncn = fields.Selection(
        related="move_id.dncn",
        store=True,
        string="DN/CN/Remaster",
    )
