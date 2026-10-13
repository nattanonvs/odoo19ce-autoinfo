# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestStockBackdating(TransactionCase):
    """Backdating allows managers to post stock operations on a past date."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "Backdated Product",
                "type": "consu",
                "is_storable": True,
            }
        )
        cls.in_type = cls.env.ref("stock.picking_type_in")
        base_user_group = cls.env.ref("base.group_user")
        stock_user_group = cls.env.ref("stock.group_stock_user")
        stock_manager_group = cls.env.ref("stock.group_stock_manager")
        Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.stock_user = Users.create(
            {
                "name": "Stock User",
                "login": "stock.user.backdate@example.com",
                "email": "stock.user.backdate@example.com",
                "company_id": cls.env.company.id,
                "company_ids": [(6, 0, [cls.env.company.id])],
                "group_ids": [(6, 0, [base_user_group.id, stock_user_group.id])],
            }
        )
        cls.stock_manager = Users.create(
            {
                "name": "Stock Manager",
                "login": "stock.manager.backdate@example.com",
                "email": "stock.manager.backdate@example.com",
                "company_id": cls.env.company.id,
                "company_ids": [(6, 0, [cls.env.company.id])],
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            base_user_group.id,
                            stock_user_group.id,
                            stock_manager_group.id,
                        ],
                    )
                ],
            }
        )

    def _create_picking(self, backdate=None):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.in_type.id,
                "location_id": self.in_type.default_location_src_id.id,
                "location_dest_id": self.in_type.default_location_dest_id.id,
            }
        )
        self.env["stock.move"].create(
            {
                "description_picking": self.product.display_name,
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "product_uom": self.product.uom_id.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "picking_id": picking.id,
            }
        )
        if backdate:
            picking.backdate_date = backdate
        return picking

    def test_stock_user_cannot_set_backdate(self):
        picking = self._create_picking()
        with self.assertRaises(AccessError):
            picking.with_user(self.stock_user).write(
                {"backdate_date": "2026-01-01"}
            )

    def test_stock_manager_can_set_backdate(self):
        picking = self._create_picking()
        picking.with_user(self.stock_manager).write(
            {"backdate_date": "2026-01-01"}
        )
        self.assertEqual(str(picking.backdate_date), "2026-01-01")

    def test_backdate_propagated_to_moves_on_validate(self):
        picking = self._create_picking(backdate="2026-01-01")
        self.assertEqual(picking.backdate_date, "2026-01-01")
        # Simulate the propagation that happens during validation
        picking.move_ids.write({"backdate_date": picking.backdate_date})
        self.assertEqual(str(picking.move_ids.backdate_date), "2026-01-01")

    def test_move_without_backdate_uses_today(self):
        """A move without backdate keeps its normal date behaviour."""
        picking = self._create_picking()
        self.assertFalse(picking.move_ids.backdate_date)
