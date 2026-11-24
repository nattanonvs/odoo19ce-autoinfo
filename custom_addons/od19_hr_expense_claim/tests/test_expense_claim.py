# -*- coding: utf-8 -*-
import ast
import base64

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestExpenseClaim(AccountTestInvoicingCommon):

    @classmethod
    def get_default_groups(cls):
        return (
            super().get_default_groups()
            | cls.env.ref("hr.group_hr_user")
            | cls.env.ref("hr_expense.group_hr_expense_user")
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Claim = cls.env["od19.expense.claim"]
        cls.supervisor = new_test_user(
            cls.env, login="od19_claim_supervisor",
            name="Claim Supervisor",
            groups="base.group_user,hr_expense.group_hr_expense_manager",
        )
        cls.accountant = new_test_user(
            cls.env, login="od19_claim_accountant",
            name="Claim Accountant",
            groups="base.group_user,account.group_account_manager",
        )
        cls.ceo = new_test_user(
            cls.env, login="od19_claim_ceo",
            name="Claim CEO",
            groups="base.group_user,od19_hr_expense_thai.group_od19_expense_ceo_approver",
        )
        cls.product = cls.env["product.product"].create({
            "name": "Claim Test Expense",
            "type": "service",
            "property_account_expense_id": cls.company_data["default_account_expense"].id,
            # ไม่ใช้ภาษีซื้อ เพื่อแยกการทดสอบ "หัวใบโพสต์บรรทัด" ออกจากข้อกำหนด
            # l10n_th_account_tax ที่บังคับเลข/วันที่ใบกำกับภาษีตอนโพสต์
            "supplier_taxes_id": [Command.clear()],
        })
        cls.employee_partner = cls.env["res.partner"].create({
            "name": "Claim Employee Contact",
        })
        cls.employee = cls.env["hr.employee"].create({
            "name": "Claim Employee",
            "work_contact_id": cls.employee_partner.id,
        })
        cls.analytic = cls.env["account.analytic.account"].create({
            "name": "Claim Analytic",
            "plan_id": cls.env.ref("analytic.analytic_plan_projects").id,
        })
        # บัญชีสำหรับสายเงินทดรอง/เงินสดย่อย (P2)
        cls.advance_account = cls.copy_account(
            cls.company_data["default_account_receivable"],
            {"name": "Claim Advance (Test)", "reconcile": True},
        )
        cls.expense_account = cls.copy_account(
            cls.company_data["default_account_expense"],
            {"name": "Claim Advance Expense (Test)"},
        )
        cls.advance_product = cls.env["product.product"].create({
            "name": "Claim Advance Expense Product",
            "type": "service",
            "property_account_expense_id": cls.expense_account.id,
            "supplier_taxes_id": [Command.clear()],
        })
        cls.bank_journal = cls.company_data["default_journal_bank"]
        cls.cash_journal = cls.company_data["default_journal_cash"]

    def _make_claim(self, lines=None, with_attachment=True):
        lines = lines or [{"name": "Line A", "total_amount": 100.0}]
        claim = self.Claim.create({
            "employee_id": self.employee.id,
            "company_id": self.env.company.id,
            "line_ids": [
                Command.create({
                    "name": line["name"],
                    "product_id": self.product.id,
                    "total_amount": line["total_amount"],
                    "employee_id": self.employee.id,
                    "payment_mode": "own_account",
                    "company_id": self.env.company.id,
                    "analytic_distribution": {str(self.analytic.id): 100.0},
                })
                for line in lines
            ],
        })
        if with_attachment:
            # หลักฐานค่าใช้จ่ายจริง (บังคับ ≥1 ไฟล์ตอน submit)
            self.env["ir.attachment"].create({
                "name": "receipt.pdf",
                "res_model": "od19.expense.claim",
                "res_id": claim.id,
                "datas": base64.b64encode(b"receipt"),
            })
        return claim

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------
    def _claim_definitions(self):
        return self.env["tier.definition"].search([
            ("model", "=", "od19.expense.claim"),
            ("company_id", "=", False),
        ])

    def _approve_claim(self, claim):
        claim.action_submit()
        claim.with_user(self.supervisor).validate_tier()
        claim.invalidate_recordset()
        claim.with_user(self.accountant).validate_tier()
        claim.invalidate_recordset()
        claim.with_user(self.ceo).validate_tier()
        claim.invalidate_recordset()
        return claim

    # ---------------------------------------------------------------
    # T1: ยอดรวมหัวใบ = ผลรวมบรรทัด
    # ---------------------------------------------------------------
    def test_claim_total_amount_is_sum_of_lines(self):
        claim = self._make_claim([
            {"name": "Line A", "total_amount": 100.0},
            {"name": "Line B", "total_amount": 250.0},
            {"name": "Line C", "total_amount": 50.0},
        ])
        self.assertEqual(len(claim.line_ids), 3)
        self.assertAlmostEqual(claim.total_amount, 400.0)
        self.assertTrue(claim.name.startswith("EXP/"))

    # ---------------------------------------------------------------
    # T2/T8: tier 3 ชั้นบนหัวใบ (และไม่มีบน hr.expense)
    # ---------------------------------------------------------------
    def test_tier_definition_model_names_include_claim(self):
        names = self.env["tier.definition"]._get_tier_validation_model_names()
        self.assertIn("od19.expense.claim", names)

    def test_three_tier_definitions_on_claim(self):
        defs = self._claim_definitions()
        self.assertEqual(len(defs), 3)

    def test_tier_definition_order_and_groups(self):
        defs = self._claim_definitions().sorted("sequence", reverse=True)
        self.assertEqual(defs.mapped("sequence"), [30, 20, 10])
        self.assertEqual(defs[0].reviewer_group_id,
                         self.env.ref("hr_expense.group_hr_expense_manager"))
        self.assertEqual(defs[1].reviewer_group_id,
                         self.env.ref("account.group_account_manager"))
        self.assertEqual(defs[2].reviewer_group_id,
                         self.env.ref("od19_hr_expense_thai.group_od19_expense_ceo_approver"))
        self.assertTrue(all(defs.mapped("approve_sequence")))
        self.assertTrue(all(defs.mapped("has_forward")))

    def test_no_tier_definition_on_hr_expense(self):
        """หลังย้าย tier ไปหัวใบ hr.expense ต้องไม่มี tier.definition แล้ว"""
        defs = self.env["tier.definition"].search([
            ("model", "=", "hr.expense"),
            ("company_id", "=", False),
        ])
        self.assertFalse(defs)

    def test_hr_expense_need_validation_is_false(self):
        expense = self.env["hr.expense"].create({
            "name": "Free Line", "product_id": self.product.id,
            "total_amount": 10.0, "employee_id": self.employee.id,
            "payment_mode": "own_account", "company_id": self.env.company.id,
        })
        self.assertFalse(expense.need_validation)

    # ---------------------------------------------------------------
    # T2: submit สร้าง review 3 รายการ เรียง seq 1,2,3
    # ---------------------------------------------------------------
    def test_submit_creates_three_reviews(self):
        claim = self._make_claim()
        # สเปก §6.1: _state_from=['submitted'] -> ยังอยู่ draft จึงยังไม่เข้าเงื่อนไขขอ validation
        self.assertEqual(claim.state, "draft")
        self.assertFalse(claim.review_ids)
        self.assertFalse(claim.need_validation)
        claim.action_submit()
        self.assertEqual(claim.state, "submitted")
        self.assertEqual(len(claim.review_ids), 3)
        self.assertEqual(
            claim.review_ids.sorted("sequence").mapped("sequence"), [1, 2, 3]
        )
        self.assertIn(claim.validation_status, ("pending", "waiting"))

    # ---------------------------------------------------------------
    # T3: อนุมัติข้ามขั้นไม่ได้
    # ---------------------------------------------------------------
    def test_cannot_approve_out_of_order(self):
        claim = self._make_claim()
        claim.action_submit()
        # CEO (ชั้น 3) พยายามอนุมัติก่อน -> ยังไม่ validated
        claim.with_user(self.ceo).validate_tier()
        claim.invalidate_recordset()
        self.assertNotEqual(claim.validation_status, "validated")
        self.assertEqual(claim.state, "submitted")

    # ---------------------------------------------------------------
    # T4 + T5: อนุมัติครบ 3 ชั้น -> หัวใบ approved + บรรทัด approved
    # ---------------------------------------------------------------
    def test_full_approval_sets_header_and_lines_approved(self):
        claim = self._make_claim([
            {"name": "Line A", "total_amount": 100.0},
            {"name": "Line B", "total_amount": 200.0},
            {"name": "Line C", "total_amount": 300.0},
        ])
        self._approve_claim(claim)
        self.assertEqual(claim.state, "approved")
        self.assertTrue(claim.approval_date)
        for line in claim.line_ids:
            self.assertEqual(line.approval_state, "approved")
            self.assertEqual(line.state, "approved")

    def test_approval_count_is_three_not_per_line(self):
        """จำนวนครั้งที่อนุมัติ (tier.review ที่ approved) = 3 ต่อใบ."""
        claim = self._make_claim([
            {"name": "Line A", "total_amount": 100.0},
            {"name": "Line B", "total_amount": 200.0},
        ])
        self._approve_claim(claim)
        self.assertEqual(len(claim.review_ids), 3)
        self.assertTrue(all(r.status == "approved" for r in claim.review_ids))

    # ---------------------------------------------------------------
    # T6: ปฏิเสธที่หัวใบ -> บรรทัดทุกตัว refused
    # ---------------------------------------------------------------
    def test_refuse_propagates_to_lines(self):
        claim = self._make_claim([
            {"name": "A", "total_amount": 10.0},
            {"name": "B", "total_amount": 20.0},
        ])
        claim.action_submit()
        claim.action_refuse()
        self.assertEqual(claim.state, "refused")
        self.assertTrue(all(l.approval_state == "refused" for l in claim.line_ids))

    def test_reset_after_refuse(self):
        claim = self._make_claim()
        claim.action_submit()
        claim.action_refuse()
        claim.action_reset()
        self.assertEqual(claim.state, "draft")
        self.assertTrue(all(not l.approval_state for l in claim.line_ids))

    # ---------------------------------------------------------------
    # T7: โพสต์บรรทัดจากหัวใบเมื่ออนุมัติครบ + ส่งบัญชีแล้ว
    # ---------------------------------------------------------------
    def test_post_after_approval(self):
        claim = self._make_claim([
            {"name": "A", "total_amount": 100.0},
        ])
        self._approve_claim(claim)
        self.assertEqual(claim.state, "approved")
        claim.action_send_to_accounting()
        self.assertEqual(claim.state, "sent")
        self.assertTrue(claim.transfer_date)
        claim.action_post()
        self.assertEqual(claim.state, "posted")
        self.assertTrue(all(l.state in ("posted", "paid") for l in claim.line_ids))

    def test_post_before_approval_raises(self):
        claim = self._make_claim()
        with self.assertRaises(UserError):
            claim.action_post()

    def test_post_requires_sent_not_just_approved(self):
        """บันทึกบัญชีได้เฉพาะใบที่พนักงานยืนยันส่งบัญชีแล้ว (state=sent)."""
        claim = self._make_claim()
        self._approve_claim(claim)
        self.assertEqual(claim.state, "approved")
        with self.assertRaises(UserError):
            claim.action_post()

    def test_post_all_lines_headless_in_one_click(self):
        """Posting UX: 1 คลิกที่หัวใบ โพสต์ทุกบรรทัดแบบ headless (ไม่มี wizard ค้าง)."""
        claim = self._make_claim([
            {"name": "A", "total_amount": 100.0},
            {"name": "B", "total_amount": 200.0},
        ])
        self._approve_claim(claim)
        claim.action_send_to_accounting()
        claim.action_post()
        self.assertEqual(claim.state, "posted")
        self.assertEqual(len(claim.line_ids), 2)
        # ทุกบรรทัดถูกโพสต์จริง (มี account.move) ไม่ใช่ค้างรอ wizard
        self.assertTrue(all(l.account_move_id for l in claim.line_ids))
        self.assertTrue(all(l.state in ("posted", "paid") for l in claim.line_ids))

    # ---------------------------------------------------------------
    # รอยต่อ: พนักงานยืนยันส่งบัญชี + ส่งได้โดยไม่ต้องแนบหลักฐาน
    # ---------------------------------------------------------------
    def test_submit_without_attachment(self):
        """ส่งขออนุมัติได้แม้ไม่มีไฟล์แนบ (บังคับแนบถูกยกเลิกแล้ว)."""
        claim = self._make_claim(with_attachment=False)
        claim.action_submit()
        self.assertEqual(claim.state, "submitted")
        self.assertEqual(len(claim.review_ids), 3)

    def test_send_to_accounting_requires_approved(self):
        claim = self._make_claim()
        claim.action_submit()
        self.assertEqual(claim.state, "submitted")
        with self.assertRaises(UserError):
            claim.action_send_to_accounting()

    # ---------------------------------------------------------------
    # เอกสารเบิก: พิมพ์ได้ โดยแสดงผู้อนุมัติครบทั้ง 3 ชั้น
    # ---------------------------------------------------------------
    def test_print_expense_claim_document(self):
        claim = self._make_claim([{"name": "A", "total_amount": 100.0}])
        self._approve_claim(claim)
        html, _ = self.env["ir.actions.report"]._render_qweb_html(
            "od19_hr_expense_claim.od19_expense_claim_document", claim.ids)
        text = html.decode("utf-8") if isinstance(html, bytes) else html
        self.assertIn(claim.name, text)
        self.assertIn("Approval Trail", text)
        for review in claim.review_ids:
            self.assertIn(review.done_by.name, text)

    # ---------------------------------------------------------------
    # K6: ใบเดียวห้ามผสม payment_mode
    # ---------------------------------------------------------------
    def test_mixed_payment_mode_raises(self):
        with self.assertRaises(ValidationError):
            self.Claim.create({
                "employee_id": self.employee.id,
                "company_id": self.env.company.id,
                "line_ids": [
                    Command.create({
                        "name": "Own", "product_id": self.product.id,
                        "total_amount": 10.0, "employee_id": self.employee.id,
                        "payment_mode": "own_account",
                        "company_id": self.env.company.id,
                    }),
                    Command.create({
                        "name": "Company", "product_id": self.product.id,
                        "total_amount": 20.0, "employee_id": self.employee.id,
                        "payment_mode": "company_account",
                        "company_id": self.env.company.id,
                    }),
                ],
            })

    # ---------------------------------------------------------------
    # T9: พนักงานเห็นเฉพาะใบเบิกของตัวเอง (หลังบ้าน)
    # ---------------------------------------------------------------
    def test_employee_sees_only_own_claims(self):
        employee_user = new_test_user(
            self.env, login="od19_claim_emp",
            name="Claim Employee User",
            groups="base.group_user,hr_expense.group_hr_expense_user",
        )
        other_employee = self.env["hr.employee"].create({
            "name": "Other Employee",
            "user_id": employee_user.id,
        })
        own = self._make_claim()          # employee = self.employee (user = test user หลัก)
        own.write({"employee_id": other_employee.id})
        foreign = self._make_claim([
            {"name": "Foreign", "total_amount": 10.0},
        ])
        visible = self.Claim.with_user(employee_user).search([])
        self.assertIn(own, visible)
        self.assertNotIn(foreign, visible)

    # ---------------------------------------------------------------
    # P2: เงินทดรอง (advance) — lifecycle ครบวงจร
    # ---------------------------------------------------------------
    def _make_advance(self, amount=10000.0, purpose="Site visit",
                      claim_type="advance", claim_source="self_service", **kw):
        vals = {
            "employee_id": self.employee.id,
            "company_id": self.env.company.id,
            "claim_type": claim_type,
            "claim_source": claim_source,
            "payment_mode": "company_account",
            "amount": amount,
            "purpose": purpose,
            "advance_account_id": self.advance_account.id,
        }
        vals.update(kw)
        return self.Claim.create(vals)

    def _approve_claim_tiers(self, claim, tiers=3):
        claim.action_submit()
        claim.with_user(self.supervisor).validate_tier()
        claim.invalidate_recordset()
        claim.with_user(self.accountant).validate_tier()
        claim.invalidate_recordset()
        if tiers >= 3:
            claim.with_user(self.ceo).validate_tier()
            claim.invalidate_recordset()
        return claim

    def _make_advance_expense(self, amount):
        return self.env["hr.expense"].create({
            "name": "Advance Clearing Expense",
            "employee_id": self.employee.id,
            "product_id": self.advance_product.id,
            "total_amount": amount,
            "payment_mode": "own_account",
            "company_id": self.env.company.id,
        })

    def test_advance_requires_company_account(self):
        with self.assertRaises(ValidationError):
            self.Claim.create({
                "employee_id": self.employee.id,
                "company_id": self.env.company.id,
                "claim_type": "advance",
                "payment_mode": "own_account",
                "amount": 100.0,
                "purpose": "Test",
                "advance_account_id": self.advance_account.id,
            })

    def test_advance_submit_requires_amount(self):
        claim = self._make_advance(amount=0.0)
        with self.assertRaises(UserError):
            claim.action_submit()

    def test_advance_full_lifecycle(self):
        claim = self._make_advance(10000.0)
        self._approve_claim_tiers(claim)
        self.assertEqual(claim.state, "approved")
        claim.action_pay()
        claim.invalidate_recordset()
        self.assertEqual(claim.state, "paid")
        self.assertEqual(claim.cash_state, "issued")
        self.assertTrue(claim.payment_id)
        self.assertAlmostEqual(claim.remaining_amount, 10000.0)

        expense = self._make_advance_expense(10000.0)
        wizard = self.env["od19.expense.claim.clear"].create({
            "claim_id": claim.id,
            "clear_date": fields.Date.context_today(self.env.user),
            "expense_ids": [Command.set([expense.id])],
        })
        wizard.action_clear()
        claim.invalidate_recordset()
        self.assertEqual(claim.state, "cleared")
        self.assertEqual(claim.cash_state, "settled")
        self.assertAlmostEqual(claim.remaining_amount, 0.0)
        self.assertEqual(expense.od19_hr_advance_id, claim)
        self.assertTrue(claim.clear_move_id)

    def test_advance_partial_clear_sets_partially_used(self):
        claim = self._make_advance(10000.0)
        self._approve_claim_tiers(claim)
        claim.action_pay()
        claim.invalidate_recordset()
        expense = self._make_advance_expense(4000.0)
        wizard = self.env["od19.expense.claim.clear"].create({
            "claim_id": claim.id,
            "clear_date": fields.Date.context_today(self.env.user),
            "expense_ids": [Command.set([expense.id])],
        })
        wizard.action_clear()
        claim.invalidate_recordset()
        self.assertEqual(claim.state, "paid")
        self.assertEqual(claim.cash_state, "partially_used")
        self.assertAlmostEqual(claim.remaining_amount, 6000.0)

    def test_advance_clear_with_returned_cash(self):
        claim = self._make_advance(10000.0)
        self._approve_claim_tiers(claim)
        claim.action_pay()
        claim.invalidate_recordset()
        expense = self._make_advance_expense(8000.0)
        wizard = self.env["od19.expense.claim.clear"].create({
            "claim_id": claim.id,
            "clear_date": fields.Date.context_today(self.env.user),
            "journal_id": self.bank_journal.id,
            "expense_ids": [Command.set([expense.id])],
            "returned_amount": 2000.0,
        })
        wizard.action_clear()
        claim.invalidate_recordset()
        self.assertEqual(claim.state, "cleared")
        self.assertAlmostEqual(claim.remaining_amount, 0.0)

    def test_advance_clear_exceeding_remaining_raises(self):
        claim = self._make_advance(10000.0)
        self._approve_claim_tiers(claim)
        claim.action_pay()
        claim.invalidate_recordset()
        expense = self._make_advance_expense(15000.0)
        wizard = self.env["od19.expense.claim.clear"].create({
            "claim_id": claim.id,
            "clear_date": fields.Date.context_today(self.env.user),
            "expense_ids": [Command.set([expense.id])],
        })
        with self.assertRaises(UserError):
            wizard.action_clear()

    def test_advance_clear_requires_paid(self):
        claim = self._make_advance(10000.0)
        self._approve_claim_tiers(claim)
        expense = self._make_advance_expense(10000.0)
        wizard = self.env["od19.expense.claim.clear"].create({
            "claim_id": claim.id,
            "clear_date": fields.Date.context_today(self.env.user),
            "expense_ids": [Command.set([expense.id])],
        })
        with self.assertRaises(UserError):
            wizard.action_clear()

    def test_advance_pay_requires_approved(self):
        claim = self._make_advance(10000.0)
        with self.assertRaises(UserError):
            claim.action_pay()

    def test_pay_rejected_for_reimbursement(self):
        claim = self._make_claim()
        self._approve_claim(claim)
        with self.assertRaises(UserError):
            claim.action_pay()

    # ---------------------------------------------------------------
    # P2: เงินสดย่อย (petty_cash) — อนุมัติเบา 2 ชั้น (ข้าม CEO)
    # ---------------------------------------------------------------
    def _make_petty_cash(self, amount=5000.0):
        return self.Claim.create({
            "employee_id": self.employee.id,
            "company_id": self.env.company.id,
            "claim_type": "petty_cash",
            "claim_source": "on_behalf",
            "submitted_for_id": self.employee.id,
            "payment_mode": "company_account",
            "amount": amount,
            "cash_fund_id": self.cash_journal.id,
            "advance_account_id": self.advance_account.id,
            "line_ids": [
                Command.create({
                    "name": "Petty Cash Expense",
                    "product_id": self.product.id,
                    "total_amount": amount,
                    "employee_id": self.employee.id,
                    "payment_mode": "company_account",
                    "company_id": self.env.company.id,
                    "analytic_distribution": {str(self.analytic.id): 100.0},
                })
            ],
        })

    def test_petty_cash_requires_on_behalf(self):
        with self.assertRaises(ValidationError):
            self.Claim.create({
                "employee_id": self.employee.id,
                "company_id": self.env.company.id,
                "claim_type": "petty_cash",
                "claim_source": "self_service",
                "amount": 100.0,
                "cash_fund_id": self.cash_journal.id,
            })

    def test_petty_cash_submit_creates_two_reviews(self):
        claim = self._make_petty_cash()
        claim.action_submit()
        self.assertEqual(claim.state, "submitted")
        self.assertEqual(len(claim.review_ids), 2)

    def test_petty_cash_approved_after_two_tiers(self):
        claim = self._make_petty_cash()
        self._approve_claim_tiers(claim, tiers=2)
        self.assertEqual(claim.state, "approved")

    # ---------------------------------------------------------------
    # P4: ศูนย์งานฝ่ายบัญชี + เมนู (ซ่อนเมนูเดิม) — §10
    # ---------------------------------------------------------------
    def _action_domain(self, action):
        return ast.literal_eval(action.domain or "[]")

    def _action_context(self, action):
        return ast.literal_eval(action.context or "{}")

    def test_accounting_menu_points_to_claim_action(self):
        """Employee Expenses (vendor) ถูกดัดแปลงเป็นศูนย์งานฝ่ายบัญชีของ claim."""
        menu = self.env.ref(
            "hr_expense.menu_hr_expense_account_employee_expenses")
        action = menu.action
        self.assertEqual(action.res_model, "od19.expense.claim")
        self.assertEqual(
            action,
            self.env.ref(
                "od19_hr_expense_claim.action_od19_expense_claim_accounting"),
        )

    def test_accounting_action_defaults_on_behalf(self):
        """สร้างใบเบิกแทนพนักงาน: ปุ่มสร้างจากศูนย์งานฝ่ายบัญชี -> on_behalf."""
        action = self.env.ref(
            "od19_hr_expense_claim.action_od19_expense_claim_accounting")
        ctx = self._action_context(action)
        self.assertEqual(ctx.get("default_claim_source"), "on_behalf")
        self.assertEqual(ctx.get("search_default_accounting_todo"), 1)

    def test_advance_menu_filter_and_defaults(self):
        action = self.env.ref(
            "od19_hr_expense_claim.action_od19_expense_claim_advance")
        self.assertEqual(action.res_model, "od19.expense.claim")
        self.assertIn(("claim_type", "=", "advance"), self._action_domain(action))
        self.assertEqual(
            self._action_context(action).get("default_claim_type"), "advance")
        menu = self.env.ref(
            "od19_hr_expense_claim.menu_od19_expense_claim_advance")
        self.assertEqual(menu.action, action)

    def test_petty_cash_menu_filter_and_defaults(self):
        action = self.env.ref(
            "od19_hr_expense_claim.action_od19_expense_claim_petty_cash")
        self.assertIn(
            ("claim_type", "=", "petty_cash"), self._action_domain(action))
        ctx = self._action_context(action)
        self.assertEqual(ctx.get("default_claim_type"), "petty_cash")
        self.assertEqual(ctx.get("default_claim_source"), "on_behalf")
        menu = self.env.ref(
            "od19_hr_expense_claim.menu_od19_expense_claim_petty_cash")
        self.assertEqual(menu.action, action)

    # ---------------------------------------------------------------
    # P4: "รออนุมัติฝ่ายบัญชี" (tier ชั้นบัญชี = current) — ตัวกรองพร้อมใช้
    # ---------------------------------------------------------------
    def test_waiting_accounting_approval_flag(self):
        claim = self._make_claim()
        claim.action_submit()
        # ค้างที่ชั้น 1 (หัวหน้าแผนก) -> ยังไม่ใช่รอฝ่ายบัญชี
        self.assertFalse(claim.od19_waiting_accounting_approval)
        claim.with_user(self.supervisor).validate_tier()
        claim.invalidate_recordset()
        # ค้างที่ชั้น 2 (ฝ่ายบัญชี)
        self.assertTrue(claim.od19_waiting_accounting_approval)
        claim.with_user(self.accountant).validate_tier()
        claim.invalidate_recordset()
        self.assertFalse(claim.od19_waiting_accounting_approval)

    def test_waiting_accounting_approval_search(self):
        claim = self._make_claim()
        claim.action_submit()
        claim.with_user(self.supervisor).validate_tier()
        claim.invalidate_recordset()
        found = self.Claim.search(
            [("od19_waiting_accounting_approval", "=", True)])
        self.assertIn(claim, found)
        not_found = self.Claim.search(
            [("od19_waiting_accounting_approval", "=", False)])
        self.assertNotIn(claim, not_found)

    # ---------------------------------------------------------------
    # P4: ฟิลด์อ้างอิงเอกสารรายบรรทัด (§5.3) อยู่บน hr.expense
    # ---------------------------------------------------------------
    def test_supplier_doc_fields_on_expense(self):
        fields = self.env["hr.expense"]._fields
        for fname in ("od19_supplier_doc_number", "od19_supplier_doc_date",
                      "od19_supplier_tax_id"):
            self.assertIn(fname, fields)
