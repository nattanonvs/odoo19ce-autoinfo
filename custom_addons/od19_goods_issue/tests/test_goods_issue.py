# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import Command, fields
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestGoodsIssue(TransactionCase):
    """Tests for the Thai Goods Issue document layer on stock.request.order."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.product = cls.env["product.product"].create(
            {
                "name": "Goods Issue Product",
                "default_code": "GI-TEST",
                "type": "consu",
                "is_storable": True,
                "uom_id": cls.uom_unit.id,
            }
        )
        cls.dept_ia = cls.env["hr.department"].create(
            {"name": "Internal Audit", "code": "IA"}
        )
        cls.dept_ba = cls.env["hr.department"].create(
            {"name": "Business Administration", "code": "BA"}
        )
        # A dedicated requester with exactly one employee, so the auto-fill of
        # department / employee from ``requested_by`` is deterministic and does
        # not depend on whatever demo employee is attached to the admin user.
        cls.requester = new_test_user(
            cls.env,
            login="od19_gi_requester",
            groups="stock_request.group_stock_request_user",
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Goods Issue Employee",
                "user_id": cls.requester.id,
                "department_id": cls.dept_ia.id,
            }
        )
        cls.issue_type = cls.env["od19.goods.issue.type"].create(
            {"name": "Material Issue", "code": "MI"}
        )
        cls.project = cls.env["project.project"].create(
            {"name": "Goods Issue Project"}
        )
        cls.no_dept_user = new_test_user(
            cls.env,
            login="od19_gi_no_dept",
            groups="stock_request.group_stock_request_user",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _order_vals(self, **kwargs):
        request_vals = {
            "product_id": self.product.id,
            "product_uom_id": self.uom_unit.id,
            "product_uom_qty": 3.0,
            "company_id": self.company.id,
            "warehouse_id": self.warehouse.id,
            "location_id": self.warehouse.lot_stock_id.id,
            "expected_date": fields.Datetime.now(),
        }
        # OCA validates that the line requester matches the order
        # (``stock.request.check_order_requested_by``); keep them in sync.
        if kwargs.get("requested_by"):
            request_vals["requested_by"] = kwargs["requested_by"]
        vals = {
            "company_id": self.company.id,
            "warehouse_id": self.warehouse.id,
            "location_id": self.warehouse.lot_stock_id.id,
            "expected_date": fields.Datetime.now(),
            "stock_request_ids": [Command.create(request_vals)],
        }
        vals.update(kwargs)
        return vals

    def _create_order(self, **kwargs):
        return self.env["stock.request.order"].create(self._order_vals(**kwargs))

    def _render(self, report_ref, records):
        html, report_type = self.env["ir.actions.report"]._render_qweb_html(
            report_ref, records.ids
        )
        text = html.decode() if isinstance(html, bytes) else html
        return text, report_type

    # ------------------------------------------------------------------
    # Numbering
    # ------------------------------------------------------------------
    def test_numbering_per_department(self):
        order_1 = self._create_order(department_id=self.dept_ia.id)
        order_2 = self._create_order(department_id=self.dept_ia.id)
        self.assertEqual(order_1.name, "GI/IA/00001")
        self.assertEqual(order_2.name, "GI/IA/00002")

    def test_numbering_other_department_is_independent(self):
        self._create_order(department_id=self.dept_ia.id)
        ba_order = self._create_order(department_id=self.dept_ba.id)
        self.assertEqual(ba_order.name, "GI/BA/00001")

    def test_numbering_fallback_without_department(self):
        # Force a fresh fallback sequence so the running number starts at 1.
        self.env["ir.sequence"].search(
            [("code", "=", "od19.goods.issue")]
        ).unlink()
        order = self._create_order(
            requested_by=self.no_dept_user.id, department_id=False
        )
        self.assertFalse(order.department_id)
        self.assertEqual(order.name, "GI/GEN/00001")

    # ------------------------------------------------------------------
    # Defaults / fields
    # ------------------------------------------------------------------
    def test_defaults_prefilled_from_current_user(self):
        order = (
            self.env["stock.request.order"]
            .with_user(self.requester)
            .create(self._order_vals())
        )
        self.assertEqual(order.department_id, self.dept_ia)
        self.assertEqual(order.od19_employee_id, self.employee)
        self.assertEqual(order.name, "GI/IA/00001")

    def test_default_get_prefills_from_current_user(self):
        vals = (
            self.env["stock.request.order"]
            .with_user(self.requester)
            .default_get(["department_id", "od19_employee_id"])
        )
        self.assertEqual(vals.get("department_id"), self.dept_ia.id)
        self.assertEqual(vals.get("od19_employee_id"), self.employee.id)

    def test_goods_issue_fields_persist(self):
        order = self._create_order(
            department_id=self.dept_ia.id,
            od19_issue_type_id=self.issue_type.id,
            od19_job_id=self.project.id,
            od19_reason="เบิกอุปกรณ์สำนักงาน / Office supplies",
        )
        self.assertEqual(order.od19_issue_type_id, self.issue_type)
        self.assertEqual(order.od19_job_id, self.project)
        self.assertEqual(
            order.od19_reason, "เบิกอุปกรณ์สำนักงาน / Office supplies"
        )

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------
    def test_goods_issue_report_renders(self):
        order = self._create_order(
            department_id=self.dept_ia.id,
            od19_issue_type_id=self.issue_type.id,
            od19_reason="Reason for issue",
        )
        text, report_type = self._render(
            "od19_goods_issue.report_od19_goods_issue_document", order
        )
        self.assertEqual(report_type, "html")
        self.assertIn("GOODS ISSUE", text)
        self.assertIn(order.name, text)

    def test_goods_issue_report_renders_without_optional_fields(self):
        order = self._create_order(
            requested_by=self.no_dept_user.id,
            department_id=False,
        )
        text, report_type = self._render(
            "od19_goods_issue.report_od19_goods_issue_document", order
        )
        self.assertEqual(report_type, "html")
        self.assertIn("GOODS ISSUE", text)

    def test_pick_list_report_renders(self):
        picking_type = self.env.ref("stock.picking_type_out")
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                # Mandatory DEPT code on the delivery (od19_delivery_label).
                "od19_department_code": self.dept_ia.code,
            }
        )
        self.env["stock.move"].create(
            {
                "product_id": self.product.id,
                "product_uom_qty": 2.0,
                "product_uom": self.uom_unit.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "picking_id": picking.id,
            }
        )
        text, report_type = self._render(
            "od19_goods_issue.report_od19_goods_issue_picklist", picking
        )
        self.assertEqual(report_type, "html")
        self.assertIn("PICK LIST", text)
        self.assertIn(picking.name, text)
