from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, new_test_user


class TestPurchaseRevision(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Keep the order below the director threshold so a single approver
        # (manager level) is enough to confirm it.
        cls.env.company.od19_po_director_approval_threshold = 100000.0
        cls.director = new_test_user(
            cls.env,
            login="od19_revision_director",
            groups="base.group_user,"
                   "purchase.group_purchase_user,"
                   "purchase.group_purchase_manager,"
                   "od19_purchase_procurement_core.group_purchase_director",
        )
        cls.outsider = new_test_user(
            cls.env,
            login="od19_revision_outsider",
            groups="base.group_user",
        )
        cls.vendor = cls.env["res.partner"].create({"name": "Revision Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "Revision Product", "purchase_ok": True, "type": "service"}
        )

    def _create_order(self, name):
        order = self.env["purchase.order"].create(
            {"name": name, "partner_id": self.vendor.id}
        )
        self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": self.product.display_name,
                "product_id": self.product.id,
                "product_qty": 1.0,
                "price_unit": 10.0,
                "date_planned": "2026-10-16 00:00:00",
                "product_uom_id": self.product.uom_id.id,
            }
        )
        return order

    def _confirm(self, order):
        """Walk the project approval flow: submit, approve, then confirm."""
        order.action_od19_submit_for_approval()
        order.with_user(self.director).action_od19_approve()
        order.button_confirm()
        return order

    def _confirmed_order(self, name="PB2501-0001"):
        return self._confirm(self._create_order(name))

    def _create_revision(self, order):
        action = order.action_create_revision()
        return self.env["purchase.order"].browse(action["res_id"])

    # ------------------------------------------------------------------
    # Naming and chain
    # ------------------------------------------------------------------

    def test_first_revision_uses_r00_suffix(self):
        order = self._confirmed_order()
        revision = self._create_revision(order)

        self.assertEqual(revision.name, "PB2501-0001/R00")
        self.assertEqual(revision.od19_base_name, "PB2501-0001")
        self.assertEqual(revision.od19_revision_no, 0)
        self.assertTrue(revision.od19_is_revision)
        self.assertEqual(revision.od19_revision_of_id, order)

    def test_revision_chain_increments(self):
        order = self._confirmed_order()
        first = self._create_revision(order)
        self._confirm(first)
        second = self._create_revision(first)

        self.assertEqual(second.name, "PB2501-0001/R01")
        self.assertEqual(second.od19_revision_no, 1)
        self.assertEqual(second.od19_revision_of_id, first)
        self.assertEqual(second.od19_base_name, order.od19_base_name)

    def test_revision_drops_confirmation_and_approval(self):
        order = self._confirmed_order()
        revision = self._create_revision(order)

        self.assertEqual(revision.state, "draft")
        self.assertEqual(revision.od19_approval_state, "draft")
        self.assertFalse(revision.date_approve)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def test_status_flips_between_current_and_superseded(self):
        order = self._confirmed_order()
        self.assertEqual(order.od19_revision_status, "current")

        revision = self._create_revision(order)

        self.assertEqual(order.od19_revision_status, "superseded")
        self.assertEqual(revision.od19_revision_status, "current")

    def test_revision_count_covers_the_whole_chain(self):
        order = self._confirmed_order()
        first = self._create_revision(order)
        self._confirm(first)
        second = self._create_revision(first)

        self.assertEqual(order.od19_revision_count, 2)
        self.assertEqual(first.od19_revision_count, 2)
        self.assertEqual(second.od19_revision_count, 2)

    # ------------------------------------------------------------------
    # Locking
    # ------------------------------------------------------------------

    def test_superseded_document_refuses_business_writes(self):
        order = self._confirmed_order()
        self._create_revision(order)

        with self.assertRaises(UserError):
            order.write({"origin": "changed"})

    def test_superseded_document_accepts_safe_keys(self):
        order = self._confirmed_order()
        self._create_revision(order)

        order.message_post(body="Revision note")
        order.write({"od19_revision_status": "superseded"})
        order.with_context(od19_allow_superseded_write=True).write(
            {"origin": "bypass"}
        )

        self.assertEqual(order.origin, "bypass")

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------

    def test_draft_order_cannot_be_revised(self):
        draft = self._create_order("PB2501-0002")

        with self.assertRaises(UserError):
            draft.action_create_revision()

    def test_superseded_order_cannot_be_revised(self):
        order = self._confirmed_order()
        self._create_revision(order)

        with self.assertRaises(UserError):
            order.action_create_revision()

    def test_non_director_cannot_revise(self):
        order = self._confirmed_order()

        with self.assertRaises(AccessError):
            order.with_user(self.outsider).action_create_revision()

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def test_report_prints_the_revision(self):
        order = self._confirmed_order()
        revision = self._create_revision(order)

        html = self.env["ir.actions.report"]._render_qweb_html(
            "purchase.action_report_purchase_order", revision.ids
        )[0]
        if isinstance(html, bytes):
            html = html.decode()

        self.assertIn("R00", html)
