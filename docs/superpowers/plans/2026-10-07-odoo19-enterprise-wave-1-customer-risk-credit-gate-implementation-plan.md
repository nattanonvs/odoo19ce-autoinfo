# Wave 1 Customer Risk and Credit Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Draft — รออนุมัติก่อน build

**Goal:** ส่งมอบ commercial guardrail สำหรับ Wave 1 ที่ (1) block ลูกค้า Blacklist ตั้งแต่ระดับ Quotation, (2) บังคับให้ลูกค้าที่ยังไม่ผ่านเครดิตขายได้เฉพาะ payment term แบบ non-credit, (3) แยก ownership ให้ Sales ขอเครดิตได้แต่ Accounting เท่านั้นที่อนุมัติ/ปฏิเสธ/แก้ Blacklist ได้ และ (4) มี KPI ขั้นต่ำสำหรับผู้บริหาร โดยไม่แก้ Odoo core

**Architecture:** ใช้ Odoo standard `sale_management`, `account` (payment terms), และ `mail` (chatter, tracking, activity, attachment) เป็นฐาน แล้วสร้าง custom addon เดียวคือ `od19_sales_customer_risk_gate` ที่ประกอบด้วย:
- `res.partner`: risk/credit state (source of truth ของสิทธิ์ขาย อ่านจาก `commercial_partner_id` เสมอ)
- `account.payment.term`: flag `od19_is_credit_term` (คำนวณค่าเริ่มต้นจาก lines, บัญชีแก้ทับได้)
- `sale.order`: gate ตอน create/write (draft) และ `action_confirm`, snapshot และ indicator
- `od19.credit.gate.event`: log การถูก block สำหรับ KPI (helper object ตาม spec 7.3)
- security group `Credit Reviewer` + menu/report ขั้นต่ำ

**Tech Stack:** Odoo 19 CE, Python, XML, PostgreSQL, Odoo test framework, Git, Markdown

## Discovery Evidence

- Approved spec: `docs/superpowers/specs/2026-10-07-odoo19-enterprise-wave-1-customer-risk-credit-gate-design.md`
- Standard/OCA fit-gap (ทำแล้ว 2026-10-11):
  - Odoo 19 CE ไม่มี credit limit/credit hold ใน CE; `res.partner` มีแค่ `sale_warn` (warning ไม่ใช่ gate) — ไม่พอสำหรับ hard block และไม่มี approval ownership
  - OCA `credit-control` (`partner_financial_risk`, `sale_financial_risk`) **ไม่มีใน workspace** และเป็น credit-limit/exposure engine ซึ่ง spec ย้ายไป Wave 2 — ไม่นำมาใช้ใน Wave 1
  - OCA `sale-workflow/sale_exception` + `server-tools/base_exception` ติดตั้งอยู่แล้วผ่าน `od19_sales_oca_bridge_workflow` แต่ออกแบบให้ "ignore exception" ได้ ซึ่งขัดกับ spec 6.8 (ห้าม exception แบบเปิดกว้าง) — ไม่ใช้เป็นกลไก gate
  - OCA `sale_order_approval_block` เป็น approval ระดับเอกสาร ไม่ใช่ระดับลูกค้า — ไม่ตรง
  - สรุป: custom addon บาง ๆ บน standard เป็นทางที่เหมาะสม
- Standard records ที่ใช้ใน test: `account.account_payment_term_immediate` (non-credit), `account.account_payment_term_30days` (credit)
- Payment term model (Odoo 19): `account.payment.term.line` มี `nb_days`, `delay_type` (`addons/account/models/account_payment_term.py`)
- Existing custom modules ที่ต้องไม่ชน: `od19_sales_oca_bridge_workflow` (มี `sale_exception` hook บน `action_confirm`), `od19_sales_contract_core`, `od19_sales_billing_evidence`, `od19_accounting_operational_closure`

## Design Decisions (ต้องการการยืนยันตอนอนุมัติ plan)

1. **นิยาม credit term:** `od19_is_credit_term` = stored compute (`readonly=False`) — True ถ้ามี line ใดมี `nb_days > 0` หรือ `delay_type` ไม่ใช่ `days_after`; SO ที่ไม่มี payment term ถือเป็น non-credit (immediate). บัญชีแก้ flag ทับได้ในหน้าฟอร์ม payment term
2. **สถานะ `not_requested`** ปฏิบัติเหมือน `pending`/`rejected` (ขายได้เฉพาะ non-credit)
3. **Quotation level:** blacklist → block `create` และ `write` ที่เปลี่ยน partner; non-approved + credit term → block `create`/`write` ของ quotation (draft/sent) และ `action_confirm`
4. **Block event log:** การ raise `UserError` จะ rollback transaction ดังนั้น log ถูกเขียนผ่าน cursor แยก (`self.env.registry.cursor()`) — ใน test จะทดสอบ helper `_od19_log_gate_event` โดยตรง ไม่ assert log หลัง `assertRaises`
5. **Approver group:** สร้าง `od19_sales_customer_risk_gate.group_od19_credit_reviewer` และให้ `account.group_account_manager` imply group นี้; ผู้ใช้บัญชีระดับอื่นเพิ่มเข้า group เองได้
6. **Migration:** ค่า default `not_requested` / `normal` — ไม่มีลูกค้าเก่าคนไหนถูกถือว่า approved อัตโนมัติ; SO ที่ confirm แล้วไม่ถูก re-validate

---

## File Structure

**Create**
- `custom_addons/od19_sales_customer_risk_gate/__init__.py`
- `custom_addons/od19_sales_customer_risk_gate/__manifest__.py`
- `custom_addons/od19_sales_customer_risk_gate/models/__init__.py`
- `custom_addons/od19_sales_customer_risk_gate/models/account_payment_term.py`
- `custom_addons/od19_sales_customer_risk_gate/models/res_partner.py`
- `custom_addons/od19_sales_customer_risk_gate/models/sale_order.py`
- `custom_addons/od19_sales_customer_risk_gate/models/od19_credit_gate_event.py`
- `custom_addons/od19_sales_customer_risk_gate/security/od19_credit_gate_security.xml`
- `custom_addons/od19_sales_customer_risk_gate/security/ir.model.access.csv`
- `custom_addons/od19_sales_customer_risk_gate/views/account_payment_term_views.xml`
- `custom_addons/od19_sales_customer_risk_gate/views/res_partner_views.xml`
- `custom_addons/od19_sales_customer_risk_gate/views/sale_order_views.xml`
- `custom_addons/od19_sales_customer_risk_gate/views/od19_credit_gate_report_views.xml`
- `custom_addons/od19_sales_customer_risk_gate/tests/__init__.py`
- `custom_addons/od19_sales_customer_risk_gate/tests/common.py`
- `custom_addons/od19_sales_customer_risk_gate/tests/test_payment_term_classification.py`
- `custom_addons/od19_sales_customer_risk_gate/tests/test_credit_workflow.py`
- `custom_addons/od19_sales_customer_risk_gate/tests/test_sale_gate.py`
- `custom_addons/od19_sales_customer_risk_gate/tests/test_gate_kpi.py`

**Modify**
- `docs/superpowers/programs/odoo19-enterprise/backlog/domain-spec-index.md`
- `docs/superpowers/programs/odoo19-enterprise/backlog/domain-wave-matrix.md`

**Reuse Without Code Changes**
- `addons/sale/`, `addons/sale_management/`, `addons/account/`, `addons/mail/`
- `custom_addons/od19_sales_oca_bridge_workflow/` (regression test เท่านั้น)
- `custom_addons/od19_accounting_operational_closure/` (regression test เท่านั้น)

## Precondition

ทำงานใน dedicated worktree `C:\odoo-dev\odoo19\.worktrees\wave1-customer-risk-credit-gate` (branch `feature/wave1-customer-risk-credit-gate` จาก `19.0`)

```powershell
git worktree add .worktrees\wave1-customer-risk-credit-gate -b feature/wave1-customer-risk-credit-gate 19.0
```

รัน Odoo จาก worktree โดย override `--addons-path` ให้ชี้ `custom_addons` ของ worktree และ OCA paths จาก main workspace:

```powershell
..\..\venv19\Scripts\python.exe .\odoo-bin -c ..\..\odoo.conf --addons-path "C:\odoo-dev\odoo19\.worktrees\wave1-customer-risk-credit-gate\addons,C:\odoo-dev\odoo19\.worktrees\wave1-customer-risk-credit-gate\odoo\addons,C:\odoo-dev\odoo19\.worktrees\wave1-customer-risk-credit-gate\custom_addons,C:\odoo-dev\odoo19\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\third_party\oca\server-backend,C:\odoo-dev\odoo19\third_party\oca\server-tools,C:\odoo-dev\odoo19\third_party\oca\server-ux" -d odoo19_pdev -i od19_sales_customer_risk_gate --test-enable --test-tags /od19_sales_customer_risk_gate --stop-after-init --log-level=test
```

หมายเหตุ: `odoo19_pdev` ใช้ภาษีไทย 7% — test ห้าม assert ยอดที่รวมภาษี

---

### Task 1: Scaffold addon + payment term classification

**Files:**
- Create: `__init__.py`, `__manifest__.py`, `models/__init__.py`, `models/account_payment_term.py`, `views/account_payment_term_views.xml`, `tests/__init__.py`, `tests/common.py`, `tests/test_payment_term_classification.py`

- [ ] **Step 1: Write the failing test**

`tests/common.py`:

```python
from odoo.tests import TransactionCase, new_test_user


class CreditGateCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.term_immediate = cls.env.ref("account.account_payment_term_immediate")
        cls.term_30 = cls.env.ref("account.account_payment_term_30days")
        cls.sales_user = new_test_user(
            cls.env, login="od19_gate_sales", groups="sales_team.group_sale_salesman"
        )
        cls.reviewer = new_test_user(
            cls.env,
            login="od19_gate_reviewer",
            groups="sales_team.group_sale_salesman,"
            "od19_sales_customer_risk_gate.group_od19_credit_reviewer",
        )
        cls.customer = cls.env["res.partner"].create(
            {"name": "Gate Customer", "company_type": "company"}
        )
        cls.contact = cls.env["res.partner"].create(
            {"name": "Gate Contact", "parent_id": cls.customer.id}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Gate Service", "type": "service", "list_price": 100.0}
        )

    def _quotation_vals(self, partner=None, term=None):
        return {
            "partner_id": (partner or self.customer).id,
            "payment_term_id": term.id if term else False,
            "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 1})],
        }
```

`tests/test_payment_term_classification.py`:

```python
from odoo.tests import tagged

from .common import CreditGateCommon


@tagged("post_install", "-at_install")
class TestPaymentTermClassification(CreditGateCommon):
    def test_immediate_term_is_non_credit(self):
        self.assertFalse(self.term_immediate.od19_is_credit_term)

    def test_thirty_days_term_is_credit(self):
        self.assertTrue(self.term_30.od19_is_credit_term)

    def test_accounting_can_override_classification(self):
        self.term_30.od19_is_credit_term = False
        self.assertFalse(self.term_30.od19_is_credit_term)
```

- [ ] **Step 2: Run test — expect FAIL** (module/field ยังไม่มี)
- [ ] **Step 3: Implement**
  - `__manifest__.py`: `depends = ["sale_management", "account", "mail"]`, data: security xml, access csv, views; `license LGPL-3`, `version 19.0.1.0.0`
  - `account.payment.term`: `od19_is_credit_term = fields.Boolean(compute="_compute_od19_is_credit_term", store=True, readonly=False)`; `@api.depends("line_ids.nb_days", "line_ids.delay_type")` → `any(l.nb_days > 0 or l.delay_type != "days_after" for l in line_ids)`
  - form view: เพิ่ม field หลัง `name` (แก้ได้เฉพาะ `account.group_account_manager`)
- [ ] **Step 4: Run test — expect PASS**
- [ ] **Step 5: Commit** `feat(credit-gate): scaffold addon and classify credit payment terms`

### Task 2: Partner risk/credit state + security

**Files:**
- Create: `models/res_partner.py`, `security/od19_credit_gate_security.xml`, `security/ir.model.access.csv`, `views/res_partner_views.xml`, `tests/test_credit_workflow.py`

- [ ] **Step 1: Write the failing test**

```python
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import CreditGateCommon


@tagged("post_install", "-at_install")
class TestCreditWorkflow(CreditGateCommon):
    def test_defaults_are_non_credit(self):
        self.assertEqual(self.customer.od19_blacklist_status, "normal")
        self.assertEqual(self.customer.od19_credit_request_state, "not_requested")
        self.assertFalse(self.customer.od19_credit_sale_allowed)

    def test_sales_can_request_credit(self):
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        self.assertEqual(self.customer.od19_credit_request_state, "pending")
        self.assertEqual(self.customer.od19_credit_requested_by, self.sales_user)
        self.assertTrue(self.customer.od19_credit_request_date)

    def test_request_schedules_activity_for_review_owner(self):
        self.customer.od19_credit_review_owner_id = self.reviewer
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        self.assertTrue(
            self.customer.activity_ids.filtered(lambda a: a.user_id == self.reviewer)
        )

    def test_sales_cannot_approve_or_edit_protected_fields(self):
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        with self.assertRaises(AccessError):
            self.customer.with_user(self.sales_user).action_od19_approve_credit()
        with self.assertRaises(AccessError):
            self.customer.with_user(self.sales_user).write(
                {"od19_credit_request_state": "approved"}
            )
        with self.assertRaises(AccessError):
            self.customer.with_user(self.sales_user).write(
                {"od19_blacklist_status": "blacklisted"}
            )

    def test_reviewer_approves_with_note_and_audit(self):
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        self.customer.od19_credit_review_note = "Docs complete"
        self.customer.with_user(self.reviewer).action_od19_approve_credit()
        self.assertEqual(self.customer.od19_credit_request_state, "approved")
        self.assertTrue(self.customer.od19_credit_sale_allowed)
        self.assertEqual(self.customer.od19_credit_review_owner_id, self.reviewer)
        self.assertTrue(self.customer.od19_credit_review_date)

    def test_approve_requires_review_note(self):
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        with self.assertRaises(UserError):
            self.customer.with_user(self.reviewer).action_od19_approve_credit()

    def test_reject_then_rerequest(self):
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        self.customer.od19_credit_review_note = "Missing docs"
        self.customer.with_user(self.reviewer).action_od19_reject_credit()
        self.assertEqual(self.customer.od19_credit_request_state, "rejected")
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        self.assertEqual(self.customer.od19_credit_request_state, "pending")

    def test_only_pending_can_be_reviewed(self):
        with self.assertRaises(UserError):
            self.customer.with_user(self.reviewer).action_od19_approve_credit()

    def test_blacklist_requires_reason_and_reviewer(self):
        with self.assertRaises(UserError):
            self.customer.with_user(self.reviewer).action_od19_set_blacklist()
        self.customer.with_user(self.reviewer).write({"od19_blacklist_reason": "Fraud"})
        self.customer.with_user(self.reviewer).action_od19_set_blacklist()
        self.assertEqual(self.customer.od19_blacklist_status, "blacklisted")

    def test_child_contact_reads_commercial_partner_state(self):
        self.customer.od19_credit_review_note = "ok"
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        self.customer.with_user(self.reviewer).action_od19_approve_credit()
        self.assertTrue(self.contact.commercial_partner_id.od19_credit_sale_allowed)
```

- [ ] **Step 2: Run test — expect FAIL**
- [ ] **Step 3: Implement**
  - security xml: `res.groups` `group_od19_credit_reviewer` (privilege ภายใต้ Accounting); `account.group_account_manager` → `implied_ids` เพิ่ม reviewer group
  - `res.partner` fields (ทุกตัว `tracking=True`, `copy=False`):
    - `od19_blacklist_status` selection `normal|blacklisted` default `normal`
    - `od19_blacklist_reason` Text
    - `od19_credit_request_state` selection `not_requested|pending|approved|rejected` default `not_requested`
    - `od19_credit_sale_allowed` Boolean compute stored = `state == "approved"`
    - `od19_credit_requested_by` m2o `res.users`, `od19_credit_request_date` Datetime
    - `od19_credit_review_owner_id` m2o `res.users`, `od19_credit_review_date` Datetime, `od19_credit_review_note` Text
  - `_OD19_PROTECTED_FIELDS = {od19_blacklist_status, od19_blacklist_reason, od19_credit_request_state, od19_credit_review_date}`; override `write()` → ถ้าแตะ protected fields และ user ไม่มี reviewer group และไม่ใช่ `self.env.su` → `AccessError`. action ของ sales (`action_od19_request_credit`) เขียนผ่าน `sudo()` เฉพาะ field ที่อนุญาต
  - actions: `action_od19_request_credit` (state ใดก็ได้ยกเว้น pending/approved → pending, schedule `mail.mail_activity_data_todo` ให้ review owner ถ้ามี), `action_od19_approve_credit` / `action_od19_reject_credit` (reviewer only, ต้อง pending, ต้องมี note, set owner=current user/date, ปิด activity ที่ค้าง), `action_od19_set_blacklist` (ต้องมี reason) / `action_od19_clear_blacklist`
  - ทำงานบน `commercial_partner_id` เสมอ; field แสดงบน contact ลูกเป็น readonly
  - view: tab "Credit & Risk" บน partner form, header buttons ตาม group, ribbon "Blacklisted"; ไฟล์แนบใช้ chatter มาตรฐาน
- [ ] **Step 4: Run test — expect PASS**
- [ ] **Step 5: Commit** `feat(credit-gate): partner risk state with accounting-owned approval`

### Task 3: Sale order gate (quotation + confirm)

**Files:**
- Create: `models/sale_order.py`, `views/sale_order_views.xml`, `tests/test_sale_gate.py`

- [ ] **Step 1: Write the failing test**

```python
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import CreditGateCommon


@tagged("post_install", "-at_install")
class TestSaleGate(CreditGateCommon):
    def _approve(self):
        self.customer.od19_credit_review_note = "ok"
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        self.customer.with_user(self.reviewer).action_od19_approve_credit()

    def _blacklist(self):
        self.customer.od19_blacklist_reason = "Bad debt"
        self.customer.with_user(self.reviewer).action_od19_set_blacklist()

    def test_blacklisted_cannot_create_quotation(self):
        self._blacklist()
        with self.assertRaisesRegex(UserError, "Blacklist"):
            self.env["sale.order"].create(self._quotation_vals(self.contact))

    def test_blacklist_after_quotation_blocks_confirm(self):
        order = self.env["sale.order"].create(self._quotation_vals(term=self.term_immediate))
        self._blacklist()
        with self.assertRaisesRegex(UserError, "Blacklist"):
            order.action_confirm()

    def test_not_approved_non_credit_quotation_confirms(self):
        order = self.env["sale.order"].create(self._quotation_vals(term=self.term_immediate))
        order.action_confirm()
        self.assertEqual(order.state, "sale")
        self.assertFalse(order.od19_is_credit_sale)

    def test_not_approved_credit_term_quotation_blocked(self):
        for state in ("not_requested", "pending", "rejected"):
            self.customer.sudo().od19_credit_request_state = state
            with self.assertRaisesRegex(UserError, "credit"):
                self.env["sale.order"].create(self._quotation_vals(term=self.term_30))

    def test_switching_to_credit_term_blocked(self):
        order = self.env["sale.order"].create(self._quotation_vals(term=self.term_immediate))
        with self.assertRaisesRegex(UserError, "credit"):
            order.payment_term_id = self.term_30

    def test_approved_customer_credit_sale_confirms_with_snapshot(self):
        self._approve()
        order = self.env["sale.order"].create(self._quotation_vals(self.contact, self.term_30))
        order.action_confirm()
        self.assertTrue(order.od19_is_credit_sale)
        self.assertEqual(order.od19_credit_state_snapshot, "approved")
        self.assertEqual(order.od19_risk_status_snapshot, "normal")

    def test_rejected_after_quotation_blocks_credit_confirm(self):
        self._approve()
        order = self.env["sale.order"].create(self._quotation_vals(term=self.term_30))
        self.customer.sudo().od19_credit_request_state = "rejected"
        with self.assertRaisesRegex(UserError, "credit"):
            order.action_confirm()

    def test_blocked_reason_visible_on_order(self):
        order = self.env["sale.order"].create(self._quotation_vals(term=self.term_immediate))
        self._blacklist()
        self.assertIn("Blacklist", order.od19_gate_blocked_reason)

    def test_confirmed_orders_not_revalidated(self):
        order = self.env["sale.order"].create(self._quotation_vals(term=self.term_immediate))
        order.action_confirm()
        self._blacklist()
        order.write({"note": "after blacklist"})
        self.assertEqual(order.state, "sale")
```

- [ ] **Step 2: Run test — expect FAIL**
- [ ] **Step 3: Implement**
  - fields: `od19_is_credit_sale` (compute stored จาก `payment_term_id.od19_is_credit_term`), `od19_risk_status_snapshot` / `od19_credit_state_snapshot` (selection, เขียนตอน confirm สำเร็จ, `copy=False`), `od19_gate_blocked_reason` (compute non-stored จากสถานะปัจจุบันของ `partner_id.commercial_partner_id`)
  - `_od19_check_customer_gate(stage)` คืนค่า `(reason_code, message)`: blacklist → `"blacklist"`; ไม่ approved + credit term → `"credit"`; ข้อความภาษาไทย/อังกฤษชัดเจน มีคำว่า `Blacklist` / `credit`
  - `create` (ตรวจหลัง super ใน `@api.model_create_multi`), `write` (เฉพาะ order ใน `draft`/`sent` และเมื่อ `partner_id` หรือ `payment_term_id` เปลี่ยน), `action_confirm` (ตรวจก่อน super) → log event แล้ว raise `UserError`
  - ไม่ใช้ `sale_exception` และวางลำดับ `super()` ให้ทำงานร่วมกับ `od19_sales_oca_bridge_workflow` ได้
  - view: alert banner แสดง `od19_gate_blocked_reason`, badge Credit/Non-credit sale, snapshot ในแท็บ Other Info; list filter "Credit sale"
- [ ] **Step 4: Run test — expect PASS**
- [ ] **Step 5: Commit** `feat(credit-gate): block blacklisted and unapproved credit sales`

### Task 4: Gate event log + owner KPIs

**Files:**
- Create: `models/od19_credit_gate_event.py`, `views/od19_credit_gate_report_views.xml`, `tests/test_gate_kpi.py`; Modify: `security/ir.model.access.csv`

- [ ] **Step 1: Write the failing test**

```python
from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import CreditGateCommon


@tagged("post_install", "-at_install")
class TestGateKpi(CreditGateCommon):
    def test_log_gate_event_helper(self):
        self.env["sale.order"]._od19_log_gate_event(
            self.customer, "blacklist", "quotation_create"
        )
        event = self.env["od19.credit.gate.event"].search(
            [("partner_id", "=", self.customer.id)]
        )
        self.assertEqual(event.reason_code, "blacklist")
        self.assertEqual(event.stage, "quotation_create")

    def test_kpis(self):
        other = self.env["res.partner"].create({"name": "Rejected Co"})
        self.customer.sudo().write(
            {
                "od19_credit_request_state": "pending",
                "od19_credit_request_date": fields.Datetime.now() - timedelta(days=4),
            }
        )
        other.sudo().od19_credit_request_state = "rejected"
        Event = self.env["od19.credit.gate.event"]
        Event.create({"partner_id": self.customer.id, "reason_code": "blacklist", "stage": "quotation_create"})
        Event.create({"partner_id": self.customer.id, "reason_code": "credit", "stage": "order_confirm"})
        kpi = self.env["res.partner"].od19_credit_gate_kpis()
        self.assertGreaterEqual(kpi["pending_count"], 1)
        self.assertGreaterEqual(kpi["pending_avg_age_days"], 4)
        self.assertGreaterEqual(kpi["rejected_count"], 1)
        self.assertGreaterEqual(kpi["blocked_blacklist_count"], 1)
        self.assertGreaterEqual(kpi["blocked_credit_count"], 1)
```

- [ ] **Step 2: Run test — expect FAIL**
- [ ] **Step 3: Implement**
  - `od19.credit.gate.event`: `partner_id`, `user_id` (default current user), `company_id`, `reason_code` (`blacklist|credit`), `stage` (`quotation_create|quotation_write|order_confirm`), `order_ref` Char, `create_date`; read: sales manager + reviewer, create: system/sudo เท่านั้น
  - `sale.order._od19_log_gate_event(partner, reason, stage, order_ref=False)`: เขียนด้วย `self.env.registry.cursor()` แยก + `api.Environment(cr, SUPERUSER_ID, {})` เพื่อให้ log อยู่รอดหลัง `UserError` rollback (ยกเว้นเมื่อ `self.env.registry.in_test_mode()` ให้เขียนใน env ปัจจุบันด้วย sudo)
  - `res.partner.od19_credit_gate_kpis()` (`@api.model`): pending count, average age (days) ของคำขอที่ค้าง, rejected count, blocked counts แยก reason
  - menu `Sales > Reporting > Credit Gate`: (a) list/pivot/graph ของ gate events, (b) list ลูกค้า Credit Pending พร้อม request date/owner, filter Rejected/Blacklisted
- [ ] **Step 4: Run test — expect PASS**
- [ ] **Step 5: Commit** `feat(credit-gate): log gate blocks and expose owner KPIs`

### Task 5: Regression + docs + merge

- [ ] **Step 1:** รัน regression รวมบน `odoo19_pdev`:

```powershell
.\venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev -u od19_sales_customer_risk_gate,od19_sales_oca_bridge_workflow,od19_accounting_operational_closure,od19_sales_reporting --test-enable --test-tags "/od19_sales_customer_risk_gate,/od19_sales_oca_bridge_workflow,/od19_accounting_operational_closure,/od19_accounting_reporting,/od19_sales_reporting" --stop-after-init --log-level=test --logfile=$env:TEMP\od19_credit_gate_test.log
```

  ถ้า test เดิมสร้าง SO ด้วย credit term ให้ลูกค้าที่ไม่ approved แล้ว fail → แก้ fixture ของ test นั้น (ตั้งลูกค้าเป็น approved ใน setUp) ไม่ผ่อน gate
- [ ] **Step 2:** อัปเดต `domain-spec-index.md` และ `domain-wave-matrix.md` (Sales row: implemented/verified; Wave 1 register gate)
- [ ] **Step 3:** Commit docs, merge `feature/wave1-customer-risk-credit-gate` → `19.0` (`--no-ff`), รัน Step 1 ซ้ำบน mainline, ลบ worktree

## Out of Scope (Wave 2)

- credit limit / exposure / overdue check (OCA `credit-control` จะประเมินใหม่ใน Wave 2)
- exception/override approval tiers
- การ re-validate SO ที่ confirm แล้ว หรือ block invoice/delivery
