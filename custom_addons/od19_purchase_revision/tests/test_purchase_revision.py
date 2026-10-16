from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPurchaseRevision(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.purchase_user_group = cls.env.ref("purchase.group_purchase_user")
        cls.director_group = cls.env.ref(
            "od19_purchase_procurement_core.group_purchase_director"
        )
        cls.partner = cls.env["res.partner"].create({"name": "Revision Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "Revision Product", "type": "consu", "purchase_ok": True}
        )
        cls.director = cls.env["res.users"].create(
            {
                "name": "Revision Director",
                "login": "od19_revision_director",
                "group_ids": [
                    (6, 0, [
                        cls.base_user_group.id,
                        cls.purchase_user_group.id,
                        cls.director_group.id,
                    ])
                ],
            }
        )
        cls.plain_user = cls.env["res.users"].create(
            {
                "name": "Revision Plain",
                "login": "od19_revision_plain",
                "group_ids": [
                    (6, 0, [cls.base_user_group.id, cls.purchase_user_group.id])
                ],
            }
        )
        # Confirming a purchase order creates a receipt picking. When the
        # optional od19_delivery_label feature is installed, that picking
        # requires a DEPT code auto-filled from the current user's
        # department, so make sure the test environment has one.
        if "od19_department_code" in cls.env["stock.picking"]._fields:
            department = cls.env["hr.department"].create(
                {"name": "Purchase Revision Dept", "code": "PUR"}
            )
            employee = cls.env["hr.employee"].search(
                [("user_id", "=", cls.env.uid)], limit=1
            )
            if employee:
                employee.department_id = department.id
            else:
                cls.env["hr.employee"].create(
                    {
                        "name": "Purchase Revision Test User",
                        "user_id": cls.env.uid,
                        "department_id": department.id,
                    }
                )

    def _create_po(self, name="PO-REV-TEST-0001"):
        return self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "name": name,
                "order_line": [
                    (0, 0, {
                        "product_id": self.product.id,
                        "product_qty": 1.0,
                        "price_unit": 10.0,
                    })
                ],
            }
        )

    def _confirm(self, order):
        """Walk the procurement approval flow required before confirmation."""
        order.action_od19_submit_for_approval()
        order.action_od19_approve()
        order.button_confirm()
        return order

    def _create_confirmed_po(self, name="PO-REV-TEST-0001"):
        return self._confirm(self._create_po(name=name))

    def test_naming_and_first_revision(self):
        po = self._create_confirmed_po()
        self.assertEqual(po.od19_revision_no, -1)
        self.assertFalse(po.od19_is_revision)
        self.assertEqual(po.od19_base_name, "PO-REV-TEST-0001")

        action = po.with_user(self.director).action_create_revision()
        rev = self.env["purchase.order"].browse(action["res_id"])

        self.assertEqual(rev.name, "PO-REV-TEST-0001/R00")
        self.assertEqual(rev.od19_revision_of_id, po)
        self.assertTrue(rev.od19_is_revision)
        self.assertEqual(rev.od19_revision_no, 0)
        self.assertEqual(rev.od19_base_name, "PO-REV-TEST-0001")
        self.assertEqual(rev.od19_revision_status, "current")
        self.assertEqual(rev.state, "draft")
        self.assertFalse(rev.date_approve)
        self.assertEqual(len(rev.order_line), 1)
        self.assertEqual(po.od19_revision_status, "superseded")

    def test_revision_chain_and_count(self):
        po = self._create_confirmed_po()
        rev1 = self.env["purchase.order"].browse(
            po.with_user(self.director).action_create_revision()["res_id"]
        )
        self._confirm(rev1)
        rev2 = self.env["purchase.order"].browse(
            rev1.with_user(self.director).action_create_revision()["res_id"]
        )

        self.assertEqual(rev2.name, "PO-REV-TEST-0001/R01")
        self.assertEqual(rev2.od19_revision_of_id, rev1)
        self.assertEqual(rev2.od19_revision_no, 1)
        self.assertEqual(rev1.od19_revision_status, "superseded")
        self.assertEqual(po.od19_revision_status, "superseded")

        # Three documents share the same base reference.
        rev2.invalidate_recordset(["od19_revision_count"])
        self.assertEqual(rev2.od19_revision_count, 2)

    def test_superseded_is_locked(self):
        po = self._create_confirmed_po()
        po.with_user(self.director).action_create_revision()
        with self.assertRaises(UserError):
            po.write({"partner_ref": "changed"})

    def test_superseded_allows_safe_writes(self):
        po = self._create_confirmed_po()
        po.with_user(self.director).action_create_revision()
        # The revision status stays writable (driven by the revision flow).
        po.write({"od19_revision_status": "superseded"})
        # Mail bookkeeping keeps working on the archived document.
        po.message_subscribe(partner_ids=[self.env.user.partner_id.id])
        po.message_post(body="note on superseded document")
        self.assertEqual(po.od19_revision_status, "superseded")

    def test_cannot_revise_draft(self):
        po = self._create_po(name="PO-REV-TEST-0002")
        with self.assertRaises(UserError):
            po.with_user(self.director).action_create_revision()

    def test_cannot_revise_superseded(self):
        po = self._create_confirmed_po()
        po.with_user(self.director).action_create_revision()
        with self.assertRaises(UserError):
            po.with_user(self.director).action_create_revision()

    def test_access_denied_without_director_group(self):
        po = self._create_confirmed_po(name="PO-REV-TEST-0003")
        with self.assertRaises(AccessError):
            po.with_user(self.plain_user).action_create_revision()

    def test_report_shows_revision(self):
        po = self._create_confirmed_po()
        rev = self.env["purchase.order"].browse(
            po.with_user(self.director).action_create_revision()["res_id"]
        )
        report = self.env.ref("purchase.action_report_purchase_order")
        html, _content_type = report._render_qweb_html(report, rev.ids)
        self.assertIn(b"R00", html)
