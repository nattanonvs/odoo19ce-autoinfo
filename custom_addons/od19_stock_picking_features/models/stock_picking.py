# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # ------------------------------------------------------------------
    # Additional print lines
    # ------------------------------------------------------------------
    od19_additional_line_ids = fields.One2many(
        "od19.stock.picking.additional.line",
        "picking_id",
        string="Additional Lines / บรรทัดเพิ่มเติม",
        copy=True,
    )

    # ------------------------------------------------------------------
    # Signature chain auto-resolve
    # ------------------------------------------------------------------
    od19_sale_user_id = fields.Many2one(
        "res.users",
        string="Salesperson / พนักงานขาย",
        help="Salesperson copied from the linked sale order. "
        "Resolved automatically from sale_id or origin.",
        tracking=True,
    )
    od19_dept_manager_id = fields.Many2one(
        "res.users",
        string="Department Manager / หัวหน้าแผนก",
        help="Department manager of the salesperson "
        "(hr.department.manager_id.user_id). "
        "Resolved automatically from the salesperson's department.",
        tracking=True,
    )

    # ------------------------------------------------------------------
    # Sale order resolution helpers
    # ------------------------------------------------------------------
    def _od19_resolve_sale_order(self):
        """Return the sale.order linked to this picking.

        Resolution order:
        1. ``self.sale_id`` when it is set.
        2. A ``sale.order`` whose ``name`` matches ``self.origin``.
        """
        self.ensure_one()
        if self.sale_id:
            return self.sale_id
        if self.origin:
            sale = self.env["sale.order"].search(
                [("name", "=", self.origin)], limit=1
            )
            if sale:
                return sale
        return self.env["sale.order"]

    def _od19_get_user_department(self, user):
        """Return the hr.department of the given user, or an empty recordset."""
        if not user:
            return self.env["hr.department"]
        employee = self.env["hr.employee"].search(
            [("user_id", "=", user.id)], limit=1
        )
        return employee.department_id

    def _od19_get_department_manager_user(self, department):
        """Return the res.users of the department manager, or an empty recordset."""
        if not department or not department.manager_id:
            return self.env["res.users"]
        return department.manager_id.user_id

    def _od19_resolve_signature_chain(self):
        """Resolve ``od19_sale_user_id`` and ``od19_dept_manager_id``.

        Returns a dict with the two field values (as recordset ids) or
        ``False`` when a value cannot be resolved.
        """
        self.ensure_one()
        sale = self._od19_resolve_sale_order()
        sale_user = sale.user_id if sale else self.env["res.users"]
        department = self._od19_get_user_department(sale_user)
        manager_user = self._od19_get_department_manager_user(department)
        return {
            "od19_sale_user_id": sale_user.id if sale_user else False,
            "od19_dept_manager_id": manager_user.id if manager_user else False,
        }

    # ------------------------------------------------------------------
    # Onchange: auto-fill the signature chain from sale_id / origin
    # ------------------------------------------------------------------
    @api.onchange("sale_id", "origin")
    def _onchange_od19_signature_chain(self):
        for picking in self:
            values = picking._od19_resolve_signature_chain()
            picking.od19_sale_user_id = values["od19_sale_user_id"]
            picking.od19_dept_manager_id = values["od19_dept_manager_id"]

    # ------------------------------------------------------------------
    # Create / write: keep the signature chain in sync for non-UI flows
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.sale_id or record.origin:
                values = record._od19_resolve_signature_chain()
                to_write = {
                    key: value
                    for key, value in values.items()
                    if value and not record[key]
                }
                if to_write:
                    record.write(to_write)
        return records

    def write(self, vals):
        result = super().write(vals)
        if "sale_id" in vals or "origin" in vals:
            for record in self:
                values = record._od19_resolve_signature_chain()
                to_write = {
                    key: value
                    for key, value in values.items()
                    if value and not record[key]
                }
                if to_write:
                    super(StockPicking, record).write(to_write)
        return result
