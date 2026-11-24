# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHrExpenseTierMoved(TransactionCase):
    """หลังย้ายสายอนุมัติไปที่หัวใบ od19.expense.claim
    hr.expense ต้องไม่มี tier.definition ที่ยัง active เหลืออยู่"""

    def test_no_active_tier_definition_on_hr_expense(self):
        defs = self.env["tier.definition"].search([
            ("model", "=", "hr.expense"),
            ("company_id", "=", False),
        ])
        self.assertFalse(defs)

    def test_ceo_group_still_exists(self):
        group = self.env.ref("od19_hr_expense_thai.group_od19_expense_ceo_approver")
        self.assertEqual(group.name, "Expense CEO Approver")
