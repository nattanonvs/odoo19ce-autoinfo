# -*- coding: utf-8 -*-
"""Tests for the quick expense submission wizard."""

import base64

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestQuickCreate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.od19_mileage_rate = 5.0
        cls.user = cls.env["res.users"].create({
            "name": "Wizard User",
            "login": "od19_wizard_user",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.employee = cls.env["hr.employee"].create({
            "name": "Wizard Employee",
            "user_id": cls.user.id,
        })
        cls.analytic_account = cls.env["account.analytic.account"].create({
            "name": "Wizard Analytic",
            "plan_id": cls.env.ref("analytic.analytic_plan_projects").id,
        })
        cls.category = cls.env["product.product"].create({
            "name": "Wizard plain category",
            "type": "service",
            "standard_price": 0.0,
            "can_be_expensed": True,
        })
        cls.mileage_category = cls.env["product.product"].create({
            "name": "Wizard mileage category",
            "type": "service",
            "standard_price": 0.0,
            "can_be_expensed": True,
            "od19_is_mileage_category": True,
        })

    def _wizard(self, **vals):
        base = {
            "employee_id": self.employee.id,
            "analytic_account_id": self.analytic_account.id,
            "submit_now": False,
        }
        base.update(vals)
        return self.env["od19.expense.quick.create"].with_user(
            self.user).create(base)

    def test_plain_expense_created(self):
        wiz = self._wizard(expense_category_id=self.category.id, amount=250.0)
        self.assertFalse(wiz.od19_is_mileage)
        action = wiz.action_create_expense()
        self.assertEqual(action["res_model"], "od19.expense.claim")
        claim = self.env["od19.expense.claim"].browse(action["res_id"])
        line = claim.line_ids
        self.assertEqual(len(line), 1)
        self.assertEqual(line.total_amount, 250.0)
        self.assertEqual(line.employee_id, self.employee)
        self.assertEqual(line.product_id, self.category)
        self.assertEqual(line.state, "draft")
        self.assertEqual(
            line.analytic_distribution,
            {str(self.analytic_account.id): 100.0},
        )

    def test_mileage_expense_created(self):
        wiz = self._wizard(
            expense_category_id=self.mileage_category.id, distance_km=20.0)
        self.assertTrue(wiz.od19_is_mileage)
        self.assertEqual(wiz.total_amount, 100.0)
        action = wiz.action_create_expense()
        self.assertEqual(action["res_model"], "od19.expense.claim")
        line = self.env["od19.expense.claim"].browse(action["res_id"]).line_ids
        self.assertTrue(line.od19_is_mileage)
        self.assertEqual(line.quantity, 20.0)
        self.assertEqual(line.total_amount, 100.0)
        self.assertEqual(line.price_unit, 5.0)

    def test_submit_now_submits(self):
        wiz = self._wizard(
            expense_category_id=self.category.id, amount=100.0, submit_now=True,
            attachment=base64.b64encode(b"receipt"),
            attachment_filename="receipt.png")
        action = wiz.action_create_expense()
        claim = self.env["od19.expense.claim"].browse(action["res_id"])
        self.assertNotEqual(claim.state, "draft")
        self.assertEqual(
            self.env["ir.attachment"].search_count([
                ("res_model", "=", "od19.expense.claim"),
                ("res_id", "=", claim.id),
            ]),
            1,
        )

    def test_submit_now_without_attachment(self):
        """ส่งอนุมัติทันทีได้โดยไม่ต้องแนบไฟล์แนบ (บังคับแนบถูกยกเลิกแล้ว)."""
        wiz = self._wizard(
            expense_category_id=self.category.id, amount=100.0, submit_now=True)
        action = wiz.action_create_expense()
        claim = self.env["od19.expense.claim"].browse(action["res_id"])
        self.assertNotEqual(claim.state, "draft")

    def test_analytic_account_is_required(self):
        """Without an analytic account the wizard refuses to create the claim."""
        with self.assertRaises(Exception):
            self._wizard(
                expense_category_id=self.category.id, amount=10.0,
                analytic_account_id=False)
