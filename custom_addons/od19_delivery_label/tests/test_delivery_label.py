# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestDeliveryLabel(TransactionCase):
    """Tests for the delivery label (FM-PU-12) fields on stock.picking."""

    def setUp(self):
        super().setUp()
        # Departments with codes used for DEPT validation and auto-fill.
        self.dept_ia = self.env["hr.department"].create(
            {"name": "Internal Audit", "code": "IA"}
        )
        self.dept_ba = self.env["hr.department"].create(
            {"name": "Business Administration", "code": "BA"}
        )
        self.dept_sa = self.env["hr.department"].create(
            {"name": "Sales", "code": "SA"}
        )
        # Link the test (admin) user to the IA department so auto-fill works.
        self.employee = self.env["hr.employee"].create(
            {
                "name": "Test Employee",
                "user_id": self.env.uid,
                "department_id": self.dept_ia.id,
            }
        )
        self.customer = self.env["res.partner"].create(
            {
                "name": "Delivery Customer",
                "company_type": "company",
                "phone": "02-123-4567",
            }
        )
        self.owner = self.env["res.partner"].create(
            {"name": "Project Owner", "company_type": "company"}
        )
        self.product = self.env["product.product"].create(
            {
                "name": "Delivery Product",
                "type": "consu",
                "is_storable": True,
                "sale_ok": True,
            }
        )
        self.out_type = self.env.ref("stock.picking_type_out")
        self.project = self.env["project.project"].create(
            {
                "name": "Delivery Label Project",
                "project_owner_id": self.owner.id,
            }
        )

    def _create_delivery_picking(self, partner=None, origin=None, dept_code="IA"):
        values = {
            "picking_type_id": self.out_type.id,
            "location_id": self.out_type.default_location_src_id.id,
            "location_dest_id": self.out_type.default_location_dest_id.id,
            "od19_department_code": dept_code,
        }
        if partner:
            values["partner_id"] = partner.id
        if origin:
            values["origin"] = origin
        return self.env["stock.picking"].create(values)

    # ------------------------------------------------------------------
    # Department code field & validation
    # ------------------------------------------------------------------
    def test_department_code_field_exists(self):
        picking = self._create_delivery_picking(partner=self.customer)
        self.assertTrue(hasattr(picking, "od19_department_code"))
        self.assertEqual(picking.od19_department_code, "IA")

    def test_department_code_auto_filled_from_user_department(self):
        # When no DEPT is provided, it should default from the user's dept.
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.out_type.id,
                "location_id": self.out_type.default_location_src_id.id,
                "location_dest_id": self.out_type.default_location_dest_id.id,
                "partner_id": self.customer.id,
            }
        )
        self.assertEqual(picking.od19_department_code, "IA")

    def test_department_code_invalid_raises(self):
        with self.assertRaises(ValidationError):
            self._create_delivery_picking(
                partner=self.customer, dept_code="INVALID"
            )

    def test_department_code_cleared_on_write_raises(self):
        picking = self._create_delivery_picking(
            partner=self.customer, dept_code="IA"
        )
        with self.assertRaises(ValidationError):
            picking.od19_department_code = ""

    def test_hr_department_has_code_field(self):
        self.assertTrue(hasattr(self.dept_ia, "code"))
        self.assertEqual(self.dept_ia.code, "IA")

    # ------------------------------------------------------------------
    # Picking name includes department code: WH/IA/OUT/00001
    # ------------------------------------------------------------------
    def test_picking_name_includes_department_code(self):
        picking = self._create_delivery_picking(
            partner=self.customer, dept_code="IA"
        )
        # Name should be WH/IA/OUT/xxxxx
        self.assertTrue(
            picking.name.startswith("WH/IA/OUT/"),
            f"Expected name to start with 'WH/IA/OUT/', got {picking.name}",
        )

    def test_picking_name_includes_ba_department_code(self):
        picking = self._create_delivery_picking(
            partner=self.customer, dept_code="BA"
        )
        self.assertTrue(
            picking.name.startswith("WH/BA/OUT/"),
            f"Expected name to start with 'WH/BA/OUT/', got {picking.name}",
        )

    def test_format_name_with_department_does_not_double_insert(self):
        formatted = self.env["stock.picking"]._format_name_with_department(
            "WH/IA/OUT/00001", "IA"
        )
        self.assertEqual(formatted, "WH/IA/OUT/00001")

    def test_format_name_with_department_inserts_after_wh(self):
        formatted = self.env["stock.picking"]._format_name_with_department(
            "WH/OUT/00001", "IA"
        )
        self.assertEqual(formatted, "WH/IA/OUT/00001")

    def test_name_updates_when_department_changes(self):
        picking = self._create_delivery_picking(
            partner=self.customer, dept_code="IA"
        )
        self.assertTrue(picking.name.startswith("WH/IA/OUT/"))
        picking.od19_department_code = "BA"
        self.assertTrue(
            picking.name.startswith("WH/BA/OUT/"),
            f"Expected name to start with 'WH/BA/OUT/', got {picking.name}",
        )

    # ------------------------------------------------------------------
    # Core label fields
    # ------------------------------------------------------------------
    def test_project_field_exists(self):
        picking = self._create_delivery_picking(partner=self.customer)
        self.assertTrue(hasattr(picking, "project_id"))

    def test_label_code_returns_picking_name(self):
        picking = self._create_delivery_picking(partner=self.customer)
        self.assertEqual(picking._get_delivery_label_code(), picking.name)

    def test_label_customer_returns_partner_name(self):
        picking = self._create_delivery_picking(partner=self.customer)
        self.assertEqual(
            picking._get_delivery_label_customer_name(), "Delivery Customer"
        )

    def test_label_department_returns_department_code(self):
        picking = self._create_delivery_picking(
            partner=self.customer, dept_code="SA"
        )
        self.assertEqual(picking._get_delivery_label_department_code(), "SA")

    def test_label_project_name_empty_when_no_project(self):
        picking = self._create_delivery_picking(partner=self.customer)
        self.assertEqual(picking._get_delivery_label_project_name(), "")

    def test_label_project_name_returns_project_name(self):
        picking = self._create_delivery_picking(partner=self.customer)
        picking.project_id = self.project
        self.assertEqual(
            picking._get_delivery_label_project_name(), "Delivery Label Project"
        )

    def test_project_propagates_from_sale_order(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": self.project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )
        self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": 1.0,
                "product_uom_id": self.product.uom_id.id,
                "price_unit": 100.0,
            }
        )
        order.action_confirm()
        picking = order.picking_ids.filtered(
            lambda p: p.picking_type_code == "outgoing"
        ).ensure_one()
        self.assertEqual(picking.project_id, self.project)
        self.assertEqual(picking.od19_department_code, "IA")

    # ------------------------------------------------------------------
    # Delivery reason (เหตุผลการส่ง)
    # ------------------------------------------------------------------
    def test_delivery_reason_fields_exist(self):
        picking = self._create_delivery_picking(partner=self.customer)
        self.assertTrue(hasattr(picking, "od19_reason_claim"))
        self.assertTrue(hasattr(picking, "od19_reason_return"))
        self.assertTrue(hasattr(picking, "od19_reason_damaged"))
        self.assertTrue(hasattr(picking, "od19_reason_under_warranty"))
        self.assertTrue(hasattr(picking, "od19_reason_delivery"))
        self.assertTrue(hasattr(picking, "od19_reason_important_document"))

    def test_delivery_default_reason_is_delivery(self):
        picking = self._create_delivery_picking(partner=self.customer)
        self.assertTrue(picking.od19_reason_delivery)

    def test_delivery_reason_display_concatenates_selected_reasons(self):
        picking = self._create_delivery_picking(partner=self.customer)
        picking.od19_reason_claim = True
        picking.od19_reason_return = True
        self.assertEqual(
            picking.od19_delivery_reason_display,
            "สินค้าเคลม, สินค้าส่งคืน, ส่งมอบสินค้า",
        )

    def test_delivery_reason_display_empty_when_no_reasons(self):
        picking = self._create_delivery_picking(partner=self.customer)
        picking.od19_reason_delivery = False
        self.assertEqual(picking.od19_delivery_reason_display, "")

    def test_label_reasons_returns_display_string(self):
        picking = self._create_delivery_picking(partner=self.customer)
        picking.od19_reason_claim = True
        self.assertIn("สินค้าเคลม", picking._get_delivery_label_reasons())

    # ------------------------------------------------------------------
    # Delivery contact (ผู้ติดต่อสำหรับจัดส่ง)
    # ------------------------------------------------------------------
    def test_delivery_contact_fields_exist(self):
        picking = self._create_delivery_picking(partner=self.customer)
        self.assertTrue(hasattr(picking, "od19_contact_name"))
        self.assertTrue(hasattr(picking, "od19_contact_phone"))

    def test_contact_defaults_from_partner_on_create(self):
        picking = self._create_delivery_picking(partner=self.customer)
        self.assertEqual(picking.od19_contact_name, "Delivery Customer")
        self.assertEqual(picking.od19_contact_phone, "02-123-4567")

    def test_contact_defaults_from_sale_order_partner(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": self.project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )
        self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": 1.0,
                "product_uom_id": self.product.uom_id.id,
                "price_unit": 100.0,
            }
        )
        order.action_confirm()
        picking = order.picking_ids.filtered(
            lambda p: p.picking_type_code == "outgoing"
        ).ensure_one()
        self.assertEqual(picking.od19_contact_name, "Delivery Customer")
        self.assertEqual(picking.od19_contact_phone, "02-123-4567")

    def test_label_contact_name_returns_contact_name(self):
        picking = self._create_delivery_picking(partner=self.customer)
        self.assertEqual(
            picking._get_delivery_label_contact_name(), "Delivery Customer"
        )

    def test_label_contact_phone_returns_contact_phone(self):
        picking = self._create_delivery_picking(partner=self.customer)
        self.assertEqual(
            picking._get_delivery_label_contact_phone(), "02-123-4567"
        )
