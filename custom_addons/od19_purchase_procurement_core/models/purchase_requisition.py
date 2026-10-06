from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    _OD19_APPROVAL_STATE_WRITE_CTX = "od19_allow_approval_state_write"
    _OD19_SKIP_INVALIDATION_CTX = "od19_skip_approval_invalidation"
    _OD19_MATERIAL_FIELDS = {
        "currency_id",
        "date_start",
        "description",
        "line_ids",
        "requisition_type",
        "vendor_id",
    }

    od19_entry_mode = fields.Selection(
        [
            ("requisition", "Purchase Requisition"),
            ("direct", "Direct Purchase Order"),
        ],
        string="Entry Mode",
        default="requisition",
        required=True,
        tracking=True,
    )
    od19_approval_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
        ],
        string="Approval State",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )

    def _od19_reset_approval_if_needed(self):
        reset_candidates = self.filtered(
            lambda requisition: requisition.od19_approval_state == "approved"
            and requisition.state == "draft"
        )
        if not reset_candidates:
            return
        super(
            PurchaseRequisition,
            reset_candidates.with_context(
                **{
                    self._OD19_APPROVAL_STATE_WRITE_CTX: True,
                    self._OD19_SKIP_INVALIDATION_CTX: True,
                }
            ),
        ).write({"od19_approval_state": "draft"})

    def write(self, vals):
        if (
            "od19_approval_state" in vals
            and not self.env.context.get(self._OD19_APPROVAL_STATE_WRITE_CTX)
        ):
            raise UserError(
                _("Approval state can only be changed through the approval actions.")
            )
        needs_invalidation = (
            not self.env.context.get(self._OD19_SKIP_INVALIDATION_CTX)
            and bool(self._OD19_MATERIAL_FIELDS.intersection(vals))
        )
        reset_candidates = self if needs_invalidation else self.browse()
        result = super().write(vals)
        if reset_candidates:
            reset_candidates._od19_reset_approval_if_needed()
        return result

    def action_od19_submit_for_approval(self):
        if any(requisition.od19_approval_state != "draft" for requisition in self):
            raise UserError(_("Only draft documents can be submitted for approval."))
        self.with_context(**{self._OD19_APPROVAL_STATE_WRITE_CTX: True}).write(
            {"od19_approval_state": "submitted"}
        )

    def action_od19_approve(self):
        if not self.env.user.has_group("purchase.group_purchase_manager"):
            raise AccessError(_("Only purchase managers can approve procurement documents."))
        if any(requisition.od19_approval_state != "submitted" for requisition in self):
            raise UserError(_("Only submitted documents can be approved."))
        self.with_context(**{self._OD19_APPROVAL_STATE_WRITE_CTX: True}).write(
            {"od19_approval_state": "approved"}
        )

    def action_confirm(self):
        self.ensure_one()
        if self.od19_approval_state != "approved":
            raise UserError(
                _("Every purchase requisition must be approved before confirmation.")
            )
        return super().action_confirm()


class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    _OD19_MATERIAL_FIELDS = {
        "price_unit",
        "product_id",
        "product_qty",
        "product_uom_id",
    }

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if not self.env.context.get("od19_skip_approval_invalidation"):
            lines.requisition_id._od19_reset_approval_if_needed()
        return lines

    def write(self, vals):
        reset_candidates = (
            self.requisition_id
            if (
                not self.env.context.get("od19_skip_approval_invalidation")
                and bool(self._OD19_MATERIAL_FIELDS.intersection(vals))
            )
            else self.env["purchase.requisition"]
        )
        result = super().write(vals)
        if reset_candidates:
            reset_candidates._od19_reset_approval_if_needed()
        return result

    def unlink(self):
        reset_candidates = (
            self.requisition_id
            if not self.env.context.get("od19_skip_approval_invalidation")
            else self.env["purchase.requisition"]
        )
        result = super().unlink()
        if reset_candidates:
            reset_candidates._od19_reset_approval_if_needed()
        return result
