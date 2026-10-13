# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


# Ordered list of (field_name, label) for delivery reasons.
# The order determines how reasons are concatenated in the display field.
DELIVERY_REASON_FIELDS = [
    ("od19_reason_claim", "สินค้าเคลม"),
    ("od19_reason_return", "สินค้าส่งคืน"),
    ("od19_reason_damaged", "สินค้าชำรุด"),
    ("od19_reason_under_warranty", "สินค้าอยู่ในประกัน"),
    ("od19_reason_delivery", "ส่งมอบสินค้า"),
    ("od19_reason_important_document", "เอกสารสำคัญ"),
]


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # ------------------------------------------------------------------
    # Delivery label core fields
    # ------------------------------------------------------------------
    od19_department_code = fields.Char(
        string="DEPT",
        help="Department code printed on the delivery label (FM-PU-12) "
        "and used in the picking reference (e.g. WH/IA/OUT/00001). "
        "Must match a code defined on an hr.department.",
        copy=False,
        required=True,
    )
    od19_project_id = fields.Many2one(
        "project.project",
        string="Project",
        compute="_compute_od19_project_id",
        store=True,
        readonly=False,
        help="Project copied from the linked sale order for the delivery label.",
    )

    # ------------------------------------------------------------------
    # Delivery reasons (เหตุผลการส่ง)
    # ------------------------------------------------------------------
    od19_reason_claim = fields.Boolean(string="สินค้าเคลม", copy=False)
    od19_reason_return = fields.Boolean(string="สินค้าส่งคืน", copy=False)
    od19_reason_damaged = fields.Boolean(string="สินค้าชำรุด", copy=False)
    od19_reason_under_warranty = fields.Boolean(
        string="สินค้าอยู่ในประกัน", copy=False
    )
    od19_reason_delivery = fields.Boolean(
        string="ส่งมอบสินค้า", copy=False, default=True
    )
    od19_reason_important_document = fields.Boolean(
        string="เอกสารสำคัญ", copy=False
    )
    od19_delivery_reason_display = fields.Char(
        string="เหตุผลการส่ง",
        compute="_compute_od19_delivery_reason_display",
        store=True,
        help="Concatenated delivery reasons shown on the delivery label.",
    )

    # ------------------------------------------------------------------
    # Delivery contact (ผู้ติดต่อสำหรับจัดส่ง)
    # ------------------------------------------------------------------
    od19_contact_name = fields.Char(
        string="ผู้ติดต่อ",
        help="Contact person name for delivery.",
        copy=False,
    )
    od19_contact_phone = fields.Char(
        string="เบอร์ติดต่อ",
        help="Contact phone number for delivery.",
        copy=False,
    )

    @api.depends("sale_id", "sale_id.od19_project_id")
    def _compute_od19_project_id(self):
        for picking in self:
            if picking.sale_id and picking.sale_id.od19_project_id:
                picking.od19_project_id = picking.sale_id.od19_project_id
            elif not picking.od19_project_id:
                picking.od19_project_id = False

    @api.depends(
        "od19_reason_claim",
        "od19_reason_return",
        "od19_reason_damaged",
        "od19_reason_under_warranty",
        "od19_reason_delivery",
        "od19_reason_important_document",
    )
    def _compute_od19_delivery_reason_display(self):
        for picking in self:
            labels = [
                label
                for field_name, label in DELIVERY_REASON_FIELDS
                if picking[field_name]
            ]
            picking.od19_delivery_reason_display = ", ".join(labels)

    # ------------------------------------------------------------------
    # Department code helpers
    # ------------------------------------------------------------------
    @api.model
    def _get_current_user_department_code(self):
        """Return the department code of the current user's employee, or False."""
        employee = self.env["hr.employee"].search(
            [("user_id", "=", self.env.uid)], limit=1
        )
        if employee and employee.department_id and employee.department_id.code:
            return employee.department_id.code
        return False

    @api.model
    def _default_od19_department_code(self):
        """Default DEPT from the current user's department."""
        return self._get_current_user_department_code()

    @api.constrains("od19_department_code")
    def _check_od19_department_code(self):
        """Ensure the department code matches an existing hr.department code."""
        for picking in self:
            code = (picking.od19_department_code or "").strip()
            if not code:
                raise ValidationError(
                    _("DEPT (Department Code) is required on the delivery order.")
                )
            department = self.env["hr.department"].search(
                [("code", "=", code)], limit=1
            )
            if not department:
                raise ValidationError(
                    _(
                        "Department code '%(code)s' is not valid. "
                        "Please select a code that exists on a department "
                        "(e.g. IA, BA, TA, DES, FA).",
                        code=code,
                    )
                )

    # ------------------------------------------------------------------
    # Picking reference name formatting: WH/{DEPT}/OUT/00001
    # ------------------------------------------------------------------
    @api.model
    def _format_name_with_department(self, name, dept_code):
        """Insert the department code into the picking reference.

        Example: 'WH/OUT/00001' -> 'WH/IA/OUT/00001'
        If the name already contains the department code, it is left unchanged.
        """
        if not name or name == "/" or not dept_code:
            return name
        # If the department code is already in the name, do nothing.
        parts = name.split("/")
        if len(parts) >= 3 and parts[1] == dept_code:
            return name
        # Insert after the first segment (e.g. 'WH').
        first, _, rest = name.partition("/")
        if not rest:
            return name
        return f"{first}/{dept_code}/{rest}"

    def _update_name_with_department(self):
        """Rewrite the picking name to include the department code.

        Only applied to pickings that are not yet done/cancelled.
        """
        for picking in self:
            if picking.state in ("done", "cancel"):
                continue
            if not picking.od19_department_code or not picking.name:
                continue
            new_name = self._format_name_with_department(
                picking.name, picking.od19_department_code
            )
            if new_name != picking.name:
                super(StockPicking, picking).write({"name": new_name})

    # ------------------------------------------------------------------
    # Default values for delivery contact (auto-fill from sale order)
    # ------------------------------------------------------------------
    def _get_delivery_contact_default_values(self):
        """Return default contact name/phone from the sale order's partner."""
        self.ensure_one()
        sale = self.sale_id
        partner = False
        if sale:
            partner = sale.partner_shipping_id or sale.partner_id
        if not partner:
            partner = self.partner_id
        return {
            "od19_contact_name": partner.name if partner else False,
            "od19_contact_phone": (partner.phone or partner.mobile) if partner else False,
        }

    def _apply_delivery_contact_defaults(self):
        """Auto-fill contact fields only when they are empty on non-backorder pickings."""
        for picking in self.filtered(lambda record: not record.backorder_id):
            defaults = picking._get_delivery_contact_default_values()
            values_to_write = {}
            if not picking.od19_contact_name and defaults["od19_contact_name"]:
                values_to_write["od19_contact_name"] = defaults["od19_contact_name"]
            if not picking.od19_contact_phone and defaults["od19_contact_phone"]:
                values_to_write["od19_contact_phone"] = defaults["od19_contact_phone"]
            if values_to_write:
                super(StockPicking, picking).write(values_to_write)

    @api.model_create_multi
    def create(self, vals_list):
        # Auto-fill DEPT from the current user's department when not provided.
        for vals in vals_list:
            if not vals.get("od19_department_code"):
                vals["od19_department_code"] = (
                    self._default_od19_department_code()
                )
        records = super().create(vals_list)
        for record in records:
            if record.sale_id and record.sale_id.od19_project_id:
                record.od19_project_id = record.sale_id.od19_project_id
        records._apply_delivery_contact_defaults()
        records._update_name_with_department()
        return records

    def write(self, vals):
        result = super().write(vals)
        if "sale_id" in vals or "partner_id" in vals:
            self._apply_delivery_contact_defaults()
        if "od19_department_code" in vals:
            self._update_name_with_department()
        return result

    # ------------------------------------------------------------------
    # Delivery label helper methods
    # ------------------------------------------------------------------
    def _get_delivery_label_code(self):
        """Return the CODE value (picking reference) for the delivery label."""
        self.ensure_one()
        return self.name or ""

    def _get_delivery_label_customer_name(self):
        """Return the customer name for the delivery label."""
        self.ensure_one()
        return self.partner_id.name or ""

    def _get_delivery_label_project_name(self):
        """Return the Project name for the delivery label."""
        self.ensure_one()
        return self.od19_project_id.name or ""

    def _get_delivery_label_department_code(self):
        """Return the DEPT value for the delivery label."""
        self.ensure_one()
        return self.od19_department_code or ""

    def _get_delivery_label_reasons(self):
        """Return the delivery reasons string for the delivery label."""
        self.ensure_one()
        return self.od19_delivery_reason_display or ""

    def _get_delivery_label_contact_name(self):
        """Return the contact person name for the delivery label."""
        self.ensure_one()
        return self.od19_contact_name or ""

    def _get_delivery_label_contact_phone(self):
        """Return the contact phone number for the delivery label."""
        self.ensure_one()
        return self.od19_contact_phone or ""
