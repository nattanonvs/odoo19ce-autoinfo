from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    _OD19_APPROVAL_STATE_WRITE_CTX = "od19_allow_approval_state_write"
    _OD19_SKIP_INVALIDATION_CTX = "od19_skip_approval_invalidation"
    _OD19_MATERIAL_FIELDS = {
        "company_id",
        "currency_id",
        "date_order",
        "dest_address_id",
        "fiscal_position_id",
        "order_line",
        "partner_id",
        "partner_ref",
        "payment_term_id",
        "requisition_id",
    }

    od19_entry_mode = fields.Selection(
        [
            ("requisition", "Purchase Requisition"),
            ("direct", "Direct Purchase Order"),
        ],
        string="Entry Mode",
        compute="_compute_od19_entry_mode",
        store=True,
        readonly=True,
        precompute=True,
    )

    @api.depends("requisition_id")
    def _compute_od19_entry_mode(self):
        for order in self:
            order.od19_entry_mode = (
                "requisition" if order.requisition_id else "direct"
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
    od19_budget_warning_count = fields.Integer(
        string="Budget Warning Count",
        compute="_compute_od19_budget_warning_count",
    )

    @api.depends("order_line.od19_budget_warning")
    def _compute_od19_budget_warning_count(self):
        for order in self:
            order.od19_budget_warning_count = len(
                order.order_line.filtered("od19_budget_warning")
            )

    def _od19_ensure_no_post_confirm_material_edit(self):
        blocked_orders = self.filtered(lambda order: order.state == "purchase" and not order.locked)
        if blocked_orders:
            raise UserError(
                _(
                    "Confirmed purchase orders cannot be materially edited after unlock. "
                    "Create a change through a new procurement review flow instead."
                )
            )

    def _od19_reset_approval_if_needed(self):
        reset_candidates = self.filtered(
            lambda order: order.od19_approval_state == "approved"
            and order.state in ("draft", "sent", "to approve")
        )
        if not reset_candidates:
            return
        to_reset_state = reset_candidates.filtered(lambda order: order.state == "to approve")
        if to_reset_state:
            super(
                PurchaseOrder,
                to_reset_state.with_context(
                    **{
                        self._OD19_APPROVAL_STATE_WRITE_CTX: True,
                        self._OD19_SKIP_INVALIDATION_CTX: True,
                    }
                ),
            ).write({"od19_approval_state": "draft", "state": "draft"})
        remaining = reset_candidates - to_reset_state
        if remaining:
            super(
                PurchaseOrder,
                remaining.with_context(
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
        if reset_candidates:
            reset_candidates._od19_ensure_no_post_confirm_material_edit()
        result = super().write(vals)
        if reset_candidates:
            reset_candidates._od19_reset_approval_if_needed()
        return result

    def action_od19_submit_for_approval(self):
        if any(order.od19_approval_state != "draft" for order in self):
            raise UserError(_("Only draft documents can be submitted for approval."))
        self.with_context(**{self._OD19_APPROVAL_STATE_WRITE_CTX: True}).write(
            {"od19_approval_state": "submitted"}
        )

    def action_od19_approve(self):
        if not self.env.user.has_group("purchase.group_purchase_manager"):
            raise AccessError(_("Only purchase managers can approve procurement documents."))
        if any(order.od19_approval_state != "submitted" for order in self):
            raise UserError(_("Only submitted documents can be approved."))
        self.with_context(**{self._OD19_APPROVAL_STATE_WRITE_CTX: True}).write(
            {"od19_approval_state": "approved"}
        )

    def button_confirm(self):
        for order in self:
            if order.state in ("draft", "sent") and order.od19_approval_state != "approved":
                raise UserError(
                    _("Every purchase order must be approved before confirmation.")
                )
        return super().button_confirm()

    def button_approve(self, force=False):
        for order in self:
            if order.state == "to approve" and order.od19_approval_state != "approved":
                raise UserError(
                    _("This purchase order needs a fresh procurement approval before manager approval.")
                )
        return super().button_approve(force=force)
