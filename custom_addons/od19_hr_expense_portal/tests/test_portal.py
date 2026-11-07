# -*- coding: utf-8 -*-
"""Portal tests for HR expense claims (Phase 3).

T4 — a portal user only ever sees his own expenses (ORM ir.rule + controller).
T8 — a portal user can file an expense claim through ``/my/expenses`` (HTTP).
"""

import hashlib
import hmac
import time

from odoo import fields
from odoo.exceptions import AccessError
from odoo.http import CSRF_TOKEN_SALT, STORED_SESSION_BYTES
from odoo.tests.common import HttpCase, TransactionCase, tagged


class TestExpensePortalBase:
    """Shared fixtures for the portal expense tests."""

    @classmethod
    def _setup_portal_fixtures(cls):
        cls.company = cls.env.company
        cls.company.od19_mileage_rate = 5.0
        cls.group_portal = cls.env.ref("base.group_portal")
        cls.category = cls.env["product.product"].create({
            "name": "Portal expense category",
            "type": "service",
            "standard_price": 0.0,
            "can_be_expensed": True,
        })

    @classmethod
    def _make_portal_employee(cls, login):
        user = cls.env["res.users"].create({
            "name": login,
            "login": login,
            "password": login,
            "group_ids": [(6, 0, [cls.group_portal.id])],
        })
        employee = cls.env["hr.employee"].create({
            "name": login + " employee",
            "user_id": user.id,
        })
        return user, employee

    @classmethod
    def _make_expense(cls, employee, name, amount):
        return cls.env["hr.expense"].create({
            "employee_id": employee.id,
            "product_id": cls.category.id,
            "name": name,
            "total_amount": amount,
        })


@tagged("post_install", "-at_install")
class TestExpensePortalAccess(TestExpensePortalBase, TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_portal_fixtures()
        cls.user_a, cls.employee_a = cls._make_portal_employee("od19_portal_a")
        cls.user_b, cls.employee_b = cls._make_portal_employee("od19_portal_b")
        cls.expense_a = cls._make_expense(cls.employee_a, "Expense A", 100.0)
        cls.expense_b = cls._make_expense(cls.employee_b, "Expense B", 200.0)

    def test_t4_portal_user_sees_only_own_expenses(self):
        seen = self.env["hr.expense"].with_user(self.user_a).search([])
        self.assertIn(self.expense_a, seen)
        self.assertNotIn(self.expense_b, seen)

    def test_t4_portal_user_cannot_read_other_expense(self):
        with self.assertRaises(AccessError):
            self.expense_b.with_user(self.user_a).read(["name"])


@tagged("post_install", "-at_install")
class TestExpensePortalHttp(TestExpensePortalBase, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_portal_fixtures()
        cls.user_a, cls.employee_a = cls._make_portal_employee("od19_portal_flow")
        cls.user_b, cls.employee_b = cls._make_portal_employee("od19_portal_other")
        cls.expense_other = cls._make_expense(
            cls.employee_b, "Other expense", 55.0)

    def _csrf_token(self):
        secret = self.env["ir.config_parameter"].sudo().get_param(
            "database.secret")
        max_ts = int(time.time() + CSRF_TOKEN_SALT)
        msg = f"{self.session.sid[:STORED_SESSION_BYTES]}{max_ts}".encode()
        digest = hmac.new(secret.encode("ascii"), msg, hashlib.sha1).hexdigest()
        return f"{digest}o{max_ts}"

    def test_t8_portal_expense_flow(self):
        self.authenticate("od19_portal_flow", "od19_portal_flow")

        self.assertEqual(self.url_open("/my/expenses").status_code, 200)
        self.assertEqual(self.url_open("/my/expenses/new").status_code, 200)

        response = self.url_open("/my/expenses/new", data={
            "csrf_token": self._csrf_token(),
            "expense_category_id": self.category.id,
            "expense_date": fields.Date.today().isoformat(),
            "description": "Portal expense",
            "amount": "123.0",
        })
        self.assertEqual(response.status_code, 200)

        expense = self.env["hr.expense"].search(
            [("name", "=", "Portal expense")], limit=1)
        self.assertTrue(expense)
        self.assertEqual(expense.employee_id, self.employee_a)
        self.assertEqual(expense.total_amount, 123.0)

    def test_t8_cannot_open_other_expense(self):
        self.authenticate("od19_portal_flow", "od19_portal_flow")
        response = self.url_open("/my/expenses/%s" % self.expense_other.id)
        self.assertEqual(response.status_code, 404)

    # ------------------------------------------------------------------
    # Phase 4a — offline-tolerant draft (localStorage)
    # ------------------------------------------------------------------
    def test_p4a_draft_autosave_markers_present(self):
        self.authenticate("od19_portal_flow", "od19_portal_flow")
        html = self.url_open("/my/expenses/new").text
        self.assertIn('id="od19_expense_form"', html)
        self.assertIn("od19_expense_draft", html)

    def test_p4a_draft_cleared_on_detail(self):
        self.authenticate("od19_portal_flow", "od19_portal_flow")
        expense = self._make_expense(self.employee_a, "Own draft", 12.0)
        response = self.url_open("/my/expenses/%s" % expense.id)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "localStorage.removeItem('od19_expense_draft')", response.text)

    # ------------------------------------------------------------------
    # Phase 4b — optional map distance (server-side, disabled by default)
    # ------------------------------------------------------------------
    def test_p4b_map_button_hidden_by_default(self):
        self.authenticate("od19_portal_flow", "od19_portal_flow")
        html = self.url_open("/my/expenses/new").text
        self.assertNotIn('id="od19_expense_map_button"', html)

    def test_p4b_distance_route_disabled_by_default(self):
        self.authenticate("od19_portal_flow", "od19_portal_flow")
        response = self.url_open("/my/expenses/distance", data={
            "csrf_token": self._csrf_token(),
            "origin": "Bangkok",
            "destination": "Chiang Mai",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.text)

    def test_p4b_map_button_shown_when_configured(self):
        params = self.env["ir.config_parameter"].sudo()
        keys = [
            "od19_hr_expense_portal.map_provider",
            "od19_hr_expense_portal.map_api_key",
        ]
        params.set_param(keys[0], "ors")
        params.set_param(keys[1], "test-key")
        self.addCleanup(lambda: params.search([("key", "in", keys)]).unlink())
        self.authenticate("od19_portal_flow", "od19_portal_flow")
        html = self.url_open("/my/expenses/new").text
        self.assertIn('id="od19_expense_map_button"', html)
