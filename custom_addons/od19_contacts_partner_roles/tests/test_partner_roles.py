from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestPartnerRoles(TransactionCase):
    def test_commercial_customer_requires_contact_channel(self):
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "No Channel Customer",
                    "company_type": "company",
                    "od19_is_commercial_customer": True,
                }
            )

    def test_multiple_roles_are_allowed_when_constraints_are_met(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Integrated Partner",
                "is_company": True,
                "mobile": "0812345678",
                "od19_is_commercial_customer": True,
                "od19_is_project_owner": True,
                "od19_is_contractor": True,
            }
        )

        self.assertTrue(partner.od19_is_commercial_customer)
        self.assertTrue(partner.od19_is_project_owner)
        self.assertTrue(partner.od19_is_contractor)

    def test_project_owner_must_be_company(self):
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "Owner Contact",
                    "company_type": "person",
                    "od19_is_project_owner": True,
                }
            )

    def test_contractor_must_be_company(self):
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "Contractor Contact",
                    "company_type": "person",
                    "od19_is_contractor": True,
                }
            )
