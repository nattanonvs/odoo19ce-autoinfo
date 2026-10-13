from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestContractBudget(TransactionCase):
    """Tests for contract budget consumption, workflow and amendments."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contractor = cls.env["res.partner"].create({"name": "Contractor A"})
        cls.owner = cls.env["res.partner"].create(
            {
                "name": "Owner A",
                "is_company": True,
                "od19_is_project_owner": True,
            }
        )
        cls.project = cls.env["project.project"].create(
            {"name": "Metro Line", "project_owner_id": cls.owner.id}
        )
        cls.customer = cls.env["res.partner"].create(
            {"name": "Customer A", "is_company": True}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Service", "type": "service", "list_price": 500.0}
        )

    def _make_contract(self, limit=1000.0, policy="warn"):
        return self.env["od19.sales.contract"].create(
            {
                "name": "MC-0001",
                "partner_id": self.contractor.id,
                "od19_project_id": self.project.id,
                "limit_amount": limit,
                "over_limit_policy": policy,
            }
        )

    def _make_order(self, contract=None, qty=1):
        return self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "od19_contract_id": contract.id if contract else False,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": qty,
                        },
                    )
                ],
            }
        )

    def test_contract_default_state_is_draft(self):
        contract = self._make_contract()
        self.assertEqual(contract.state, "draft")

    def test_contract_workflow_approve_activate_close(self):
        contract = self._make_contract()
        contract.action_approve()
        self.assertEqual(contract.state, "approved")
        contract.action_activate()
        self.assertEqual(contract.state, "active")
        contract.action_close()
        self.assertEqual(contract.state, "closed")

    def test_contract_approve_only_from_draft(self):
        contract = self._make_contract()
        contract.action_approve()
        with self.assertRaises(UserError):
            contract.action_approve()

    def test_contract_dates_validation(self):
        contract = self._make_contract()
        contract.start_date = "2024-01-10"
        with self.assertRaises(ValidationError):
            contract.end_date = "2024-01-01"

    def test_contract_activity_block_policy(self):
        contract = self._make_contract(limit=1000.0, policy="block")
        self.env["od19.sales.contract.activity"].create(
            {
                "name": "ACT-001",
                "contract_id": contract.id,
                "amount_to_consume": 900.0,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["od19.sales.contract.activity"].create(
                {
                    "name": "ACT-002",
                    "contract_id": contract.id,
                    "amount_to_consume": 200.0,
                }
            )

    def test_order_confirm_adds_to_consumed_from_orders(self):
        contract = self._make_contract(limit=1000.0, policy="warn")
        order = self._make_order(contract=contract, qty=1)
        order.action_confirm()
        contract.invalidate_recordset()
        self.assertEqual(contract.consumed_from_orders, 500.0)
        self.assertEqual(contract.consumed_amount, 500.0)

    def test_order_confirm_block_policy_over_limit(self):
        contract = self._make_contract(limit=100.0, policy="block")
        order = self._make_order(contract=contract, qty=1)
        with self.assertRaises(UserError):
            order.action_confirm()

    def test_amendment_updates_limit_amount(self):
        contract = self._make_contract(limit=1000.0)
        self.assertEqual(contract.limit_amount, 1000.0)
        self.env["od19.sales.contract.amendment"].create(
            {
                "name": "AM-001",
                "contract_id": contract.id,
                "added_limit_amount": 500.0,
            }
        )
        self.assertEqual(contract.limit_amount, 1500.0)

    def test_contract_activity_has_order_line_field(self):
        # Ensure the Many2one field exists on sale.order.line
        self.assertIn(
            "od19_contract_activity_id", self.env["sale.order.line"]._fields
        )
