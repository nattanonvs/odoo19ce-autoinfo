# -*- coding: utf-8 -*-
"""Portal tests for cash advances (Phase 3 — ``/my/advances``).

The employee-facing advance route reuses the claim header with
``claim_type='advance'``; these tests cover list/new/detail/submit and the
owner-only access rule.
"""

import hashlib
import hmac
import time

from odoo import fields
from odoo.http import CSRF_TOKEN_SALT, STORED_SESSION_BYTES
from odoo.tests.common import HttpCase, TransactionCase, tagged

_ADVANCE_ACCOUNT_PARAM = "od19_hr_expense_portal.advance_account_id"


class TestAdvancePortalBase:
    """Shared fixtures for the portal advance tests."""

    @classmethod
    def _setup_advance_fixtures(cls):
        cls.company = cls.env.company
        cls.group_portal = cls.env.ref("base.group_portal")
        cls.advance_account = cls.env["account.account"].search(
            [("account_type", "=", "asset_current")], limit=1)
        if not cls.advance_account:
            cls.advance_account = cls.env["account.account"].create({
                "name": "Portal Employee Advance",
                "code": "119900",
                "account_type": "asset_current",
            })
        params = cls.env["ir.config_parameter"].sudo()
        params.set_param(_ADVANCE_ACCOUNT_PARAM, str(cls.advance_account.id))
        cls.addClassCleanup(
            lambda: cls.env["ir.config_parameter"].sudo().search(
                [("key", "=", _ADVANCE_ACCOUNT_PARAM)]).unlink())

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
    def _make_advance(cls, employee, purpose, amount):
        return cls.env["od19.expense.claim"].create({
            "employee_id": employee.id,
            "company_id": cls.company.id,
            "claim_type": "advance",
            "claim_source": "self_service",
            "payment_mode": "company_account",
            "amount": amount,
            "purpose": purpose,
            "advance_account_id": cls.advance_account.id,
        })


@tagged("post_install", "-at_install")
class TestAdvancePortalScope(TestAdvancePortalBase, TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_advance_fixtures()
        cls.user_a, cls.employee_a = cls._make_portal_employee("od19_adv_a")
        cls.user_b, cls.employee_b = cls._make_portal_employee("od19_adv_b")
        cls.advance_a = cls._make_advance(cls.employee_a, "Trip A", 1000.0)
        cls.advance_b = cls._make_advance(cls.employee_b, "Trip B", 2000.0)

    def test_advance_is_owner_scoped(self):
        seen = self.env["od19.expense.claim"].with_user(self.user_a).search(
            [("claim_type", "=", "advance")])
        self.assertIn(self.advance_a, seen)
        self.assertNotIn(self.advance_b, seen)


@tagged("post_install", "-at_install")
class TestAdvancePortalHttp(TestAdvancePortalBase, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_advance_fixtures()
        cls.user_a, cls.employee_a = cls._make_portal_employee("od19_adv_flow")
        cls.user_b, cls.employee_b = cls._make_portal_employee("od19_adv_other")
        cls.advance_other = cls._make_advance(cls.employee_b, "Other", 77.0)

    def _csrf_token(self):
        secret = self.env["ir.config_parameter"].sudo().get_param(
            "database.secret")
        max_ts = int(time.time() + CSRF_TOKEN_SALT)
        msg = f"{self.session.sid[:STORED_SESSION_BYTES]}{max_ts}".encode()
        digest = hmac.new(secret.encode("ascii"), msg, hashlib.sha1).hexdigest()
        return f"{digest}o{max_ts}"

    def test_advance_pages_accessible(self):
        self.authenticate("od19_adv_flow", "od19_adv_flow")
        self.assertEqual(self.url_open("/my/advances").status_code, 200)
        self.assertEqual(self.url_open("/my/advances/new").status_code, 200)

    def test_advance_request_flow(self):
        self.authenticate("od19_adv_flow", "od19_adv_flow")
        response = self.url_open("/my/advances/new", data={
            "csrf_token": self._csrf_token(),
            "advance_date": fields.Date.today().isoformat(),
            "amount": "1500.0",
            "purpose": "Portal advance request",
            "submit_now": "1",
        })
        self.assertEqual(response.status_code, 200)

        advance = self.env["od19.expense.claim"].search(
            [("purpose", "=", "Portal advance request")], limit=1)
        self.assertTrue(advance)
        self.assertEqual(advance.claim_type, "advance")
        self.assertEqual(advance.employee_id, self.employee_a)
        self.assertEqual(advance.amount, 1500.0)
        self.assertEqual(advance.advance_account_id, self.advance_account)
        self.assertEqual(advance.state, "submitted")

        detail = self.url_open("/my/advances/%s" % advance.id)
        self.assertEqual(detail.status_code, 200)
        self.assertIn(advance.name, detail.text)

    def test_advance_submit_route(self):
        self.authenticate("od19_adv_flow", "od19_adv_flow")
        advance = self._make_advance(
            self.employee_a, "Own draft advance", 500.0)
        self.assertEqual(advance.state, "draft")
        response = self.url_open(
            "/my/advances/%s/submit" % advance.id,
            data={"csrf_token": self._csrf_token()})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(advance.state, "submitted")

    def test_cannot_open_other_advance(self):
        self.authenticate("od19_adv_flow", "od19_adv_flow")
        response = self.url_open("/my/advances/%s" % self.advance_other.id)
        self.assertEqual(response.status_code, 404)
