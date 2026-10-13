# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .supplier_quality import BLOCKED_SUPPLIER_STATUSES


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    override_supplier_block = fields.Boolean(
        string="ยืนยัน override การซื้อจากผู้จำหน่ายที่ถูกบล็อก",
        default=False,
        copy=False,
        help="ติ๊กเพื่อยืนยันว่าผู้จัดการอนุญาตให้ซื้อจากผู้จำหน่ายที่ถูกระงับ/ตัดสิทธิ์",
    )
    override_supplier_block_reason = fields.Text(
        string="เหตุผลการ override",
        copy=False,
        help="เหตุผลที่ผู้จัดการอนุญาตให้ซื้อจากผู้จำหน่ายที่ถูกบล็อก",
    )

    def _get_blocked_supplier_message(self, partner):
        """Return a user-facing message when the supplier is blocked, else False."""
        status = partner.od19_iso_supplier_status
        if status in BLOCKED_SUPPLIER_STATUSES:
            selection = self.env["res.partner"]._fields[
                "od19_iso_supplier_status"
            ].selection
            label = dict(selection).get(status, status)
            return _(
                "ไม่สามารถสร้าง/แก้ไขใบสั่งซื้อกับผู้จำหน่าย '%(name)s' "
                "ได้ เนื่องจากสถานะผู้จำหน่ายเป็น '%(status)s' "
                "หากต้องการดำเนินการต่อ โปรดให้ผู้จัดการยืนยัน override "
                "และระบุเหตุผล"
            ) % {"name": partner.display_name, "status": label}
        return False

    def _check_supplier_quality_block(self, vals):
        """Raise UserError if the supplier is blocked and not properly
        overridden by a manager.
        """
        company = self.env.company
        if not company.enable_supplier_quality_block:
            return
        partner_id = vals.get("partner_id") or (
            self.partner_id.id if self else False
        )
        if not partner_id:
            return
        partner = self.env["res.partner"].browse(partner_id)
        msg = self._get_blocked_supplier_message(partner)
        if not msg:
            return
        # Allow override: only managers / system admins can override.
        override = vals.get(
            "override_supplier_block",
            self.override_supplier_block if self else False,
        )
        reason = vals.get(
            "override_supplier_block_reason",
            self.override_supplier_block_reason if self else "",
        )
        can_override = self.env.user.has_group(
            "purchase.group_purchase_manager"
        ) or self.env.user.has_group("base.group_system")
        if override and reason and can_override:
            return
        # Build the message with guidance.
        message = msg
        if not can_override:
            message += _(
                "\n(ผู้ใช้ปัจจุบันไม่มีสิทธิ์ override "
                "ต้องเป็น Purchase Manager หรือ System Administrator)"
            )
        elif not override or not reason:
            message += _("\n(กรุณาติ๊กยืนยัน override และระบุเหตุผล)")
        raise UserError(message)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_supplier_quality_block(vals)
        return super().create(vals_list)

    def write(self, vals):
        for order in self:
            merged = dict(vals)
            if "partner_id" not in merged:
                merged["partner_id"] = order.partner_id.id
            self._check_supplier_quality_block(merged)
        return super().write(vals)
