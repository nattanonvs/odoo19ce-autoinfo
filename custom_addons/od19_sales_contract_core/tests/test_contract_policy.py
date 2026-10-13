from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestContractPolicy(TransactionCase):
    def setUp(self):
        super().setUp()
        self.contractor = self.env["res.partner"].create({"name": "Contractor A"})
        self.owner = self.env["res.partner"].create(
            {
                "name": "Owner A",
                "is_company": True,
                "od19_is_project_owner": True,
            }
        )
        self.project = self.env["project.project"].create(
            {"name": "Metro Line", "project_owner_id": self.owner.id}
        )

    def test_activity_must_respect_block_policy(self):
        contract = self.env["od19.sales.contract"].create(
            {
                "name": "MC-0001",
                "partner_id": self.contractor.id,
                "od19_project_id": self.project.id,
                "limit_amount": 1000.0,
                "over_limit_policy": "block",
            }
        )

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
