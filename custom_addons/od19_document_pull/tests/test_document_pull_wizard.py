# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestDocumentPullWizard(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Confirming the purchase order creates a receipt. The delivery-label
        # module installed in this database requires a DEPT department code,
        # resolved from the current user's employee record.
        cls.department = cls.env["hr.department"].sudo().create(
            {"name": "Pull Test", "code": "PT"}
        )
        cls.env["hr.employee"].sudo().create(
            {
                "name": "Pull Test Employee",
                "user_id": cls.env.uid,
                "department_id": cls.department.id,
            }
        )
        cls.vendor = cls.partner_a
        cls.product = cls.product_a
        # Candidate lines are filtered on ``qty_to_invoice > 0``. With the
        # default "on received quantities" control policy that quantity stays 0
        # until the receipt is validated, so the fixture bills on ordered
        # quantities instead - the pull mechanism, not the control policy, is
        # what these tests exercise.
        cls.product.purchase_method = "purchase"
        cls.po = cls._create_confirmed_po([5.0])

    @classmethod
    def _create_confirmed_po(cls, quantities):
        """Create and confirm a purchase order carrying one line per quantity.

        The lines are added while the order is still in draft: the procurement
        module that ships with this database blocks adding lines to a confirmed
        order, so a multi-line fixture has to be built up-front.
        ``button_confirm`` is itself gated by the procurement approval flow
        (od19_purchase_procurement_core), hence the submit/approve calls.
        """
        po = cls.env["purchase.order"].sudo().create(
            {
                "partner_id": cls.vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_qty": qty,
                            "price_unit": 100.0,
                            "name": cls.product.name,
                            "date_planned": "2026-01-01",
                        },
                    )
                    for qty in quantities
                ],
            }
        )
        po.action_od19_submit_for_approval()
        po.action_od19_approve()
        po.button_confirm()
        return po

    def _new_bill(self):
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2026-02-01",
            }
        )

    def _open_wizard(self, bill, **overrides):
        vals = {
            "res_model": "account.move",
            "res_id": bill.id,
        }
        vals.update(overrides)
        return self.env["od19.document.pull.wizard"].create(vals)

    def _select_source(self, wizard, source):
        """Tick the wizard row that points at ``source`` and rebuild lines."""
        wizard.source_ids.filtered(
            lambda row: row.source_model == source._name
            and row.source_id == source.id
        ).selected = True
        wizard._onchange_source_ids()

    def test_source_rows_list_bill_sources(self):
        bill = self._new_bill()
        wizard = self._open_wizard(bill)
        self.assertEqual(wizard.partner_id, self.vendor)
        row = wizard.source_ids.filtered(
            lambda r: r.source_model == "purchase.order"
            and r.source_id == self.po.id
        )
        self.assertTrue(row)
        self.assertEqual(row.remaining, 1)

    def test_source_type_filter_narrows_source_rows(self):
        """Choosing a pull type keeps only the matching source rows."""
        bill = self._new_bill()
        wizard = self._open_wizard(bill)
        self.assertTrue(
            wizard.source_ids.filtered(
                lambda r: r.source_model == "purchase.order"
            )
        )
        wizard.source_type_filter = "purchase.request"
        wizard._onchange_source_type_filter()
        self.assertFalse(wizard.source_ids)
        self.assertFalse(wizard.line_ids)
        wizard.source_type_filter = "purchase.order"
        wizard._onchange_source_type_filter()
        self.assertTrue(
            wizard.source_ids.filtered(
                lambda r: r.source_model == "purchase.order"
                and r.source_id == self.po.id
            )
        )

    def test_onchange_source_builds_lines_with_all_order_mode(self):
        bill = self._new_bill()
        wizard = self._open_wizard(bill)
        self._select_source(wizard, self.po)
        self.assertEqual(len(wizard.line_ids), 1)
        line = wizard.line_ids
        self.assertEqual(line.res_model, "purchase.order.line")
        self.assertEqual(line.res_id, self.po.order_line.id)
        self.assertAlmostEqual(line.qty_to_pull, 5.0)

    def test_action_pull_all_order_creates_lines(self):
        bill = self._new_bill()
        wizard = self._open_wizard(bill)
        self._select_source(wizard, self.po)
        wizard.action_pull()
        self.assertEqual(len(bill.invoice_line_ids), 1)
        self.assertEqual(bill.invoice_line_ids.purchase_line_id, self.po.order_line)
        self.assertAlmostEqual(bill.invoice_line_ids.quantity, 5.0)
        self.assertAlmostEqual(bill.invoice_line_ids.price_unit, 100.0)

    def test_action_pull_select_mode_only_selected(self):
        po = self._create_confirmed_po([5.0, 2.0])
        bill = self._new_bill()
        wizard = self._open_wizard(bill, mode="select")
        self._select_source(wizard, po)
        self.assertEqual(len(wizard.line_ids), 2)
        first = wizard.line_ids[0]
        wizard.line_ids.write({"selected": False})
        first.selected = True
        wizard.action_pull()
        self.assertEqual(len(bill.invoice_line_ids), 1)
        self.assertEqual(
            bill.invoice_line_ids.purchase_line_id,
            first._od19_get_source_line(),
        )

    def test_action_pull_raises_without_source(self):
        bill = self._new_bill()
        wizard = self._open_wizard(bill)
        with self.assertRaises(UserError):
            wizard.action_pull()

    def test_action_pull_raises_when_nothing_selected(self):
        bill = self._new_bill()
        wizard = self._open_wizard(bill, mode="select")
        self._select_source(wizard, self.po)
        wizard.line_ids.write({"selected": False})
        with self.assertRaises(UserError):
            wizard.action_pull()

    def test_pull_twice_does_not_duplicate(self):
        bill = self._new_bill()
        wizard = self._open_wizard(bill)
        self._select_source(wizard, self.po)
        wizard.action_pull()
        wizard2 = self._open_wizard(bill)
        self._select_source(wizard2, self.po)
        self.assertEqual(len(wizard2.line_ids), 0)

    def test_action_pull_from_previous_bill(self):
        """Flow 2: a new bill can pull the lines of a previous vendor bill."""
        posted = self.init_invoice(
            "in_invoice", partner=self.vendor, post=True, amounts=[100.0]
        )
        source_lines = posted.invoice_line_ids.filtered(
            lambda l: l.display_type == "product"
        )
        bill = self._new_bill()
        wizard = self._open_wizard(bill)
        self._select_source(wizard, posted)
        self.assertEqual(len(wizard.line_ids), 1)

        wizard.action_pull()
        self.assertEqual(len(bill.invoice_line_ids), 1)
        self.assertEqual(
            bill.invoice_line_ids.od19_source_move_line_id, source_lines
        )
        self.assertAlmostEqual(
            bill.invoice_line_ids.price_unit, source_lines.price_unit
        )
        self.assertEqual(bill.od19_pull_source_label, posted.display_name + " (1)")

    def _create_confirmed_so(self, quantity):
        """Create and confirm a small sale order (< approval threshold)."""
        so = self.env["sale.order"].sudo().create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": quantity,
                            "price_unit": 100.0,
                            "name": self.product.name,
                        },
                    )
                ],
            }
        )
        so.action_confirm()
        self.assertEqual(so.state, "sale")
        return so

    def test_action_pull_from_sale_order(self):
        """Flow 3: a customer invoice can pull the lines of a sale order."""
        self.product.invoice_policy = "order"
        so = self._create_confirmed_so(3.0)
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-02-01",
            }
        )
        wizard = self._open_wizard(invoice)
        self._select_source(wizard, so)
        self.assertEqual(len(wizard.line_ids), 1)

        wizard.action_pull()
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertEqual(invoice.invoice_line_ids.sale_line_ids, so.order_line)
        self.assertAlmostEqual(invoice.invoice_line_ids.quantity, 3.0)
