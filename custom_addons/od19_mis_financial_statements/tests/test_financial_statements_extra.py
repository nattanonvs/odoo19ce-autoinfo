# -*- coding: utf-8 -*-
"""Test gate เพิ่มเติมของโมดูล od19_mis_financial_statements.

    A) งบกระแสเงินสด (วิธีทางอ้อม)
       เงินสดต้นงวด + กระแสเงินสดสุทธิ − เงินสดสิ้นงวด = 0 (บรรทัด cf_check)
    B) งบประมาณ เทียบผลจริง (Budget vs Actual)
       KPI งบกำไรขาดทุนตั้ง budgetable=True และคอลัมน์งบประมาณดึงยอดจาก mis.budget.item ได้

ทดสอบ A ด้วยบริษัทใหม่ที่ผังบัญชีถูกควบคุม (สร้างเอง) เพื่อให้ตัวเลข deterministic
ทดสอบ B ตรวจโครงสร้างข้อมูลที่โหลดจาก XML + ทดสอบ _query_kpi_data โดยตรง
"""
from datetime import date

from odoo import Command, fields
from odoo.tests.common import TransactionCase, tagged

CF_REPORT_XMLID = "od19_mis_financial_statements.mis_report_cash_flow"
CF_INSTANCE_XMLID = "od19_mis_financial_statements.mis_instance_cash_flow"
PL_REPORT_XMLID = "od19_mis_financial_statements.mis_report_profit_loss"
BUDGET_XMLID = "od19_mis_financial_statements.mis_budget_annual_pl"
BVA_INSTANCE_XMLID = "od19_mis_financial_statements.mis_instance_budget_vs_actual"

BUDGETABLE_KPI_NAMES = [
    "pl_4110", "pl_4120", "pl_5110", "pl_5120", "pl_4200", "pl_4300",
    "pl_5130", "pl_5210", "pl_5300", "pl_5400", "pl_5410", "pl_5420",
]


@tagged("post_install", "-at_install")
class TestCashFlowStatement(TransactionCase):
    """งบกระแสเงินสด — ตรวจว่าสมการเงินสดปิด (cf_check = 0)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env["res.company"].create({"name": "OD19 CF Test Co"})
        cls.env = cls.env(
            context=dict(cls.env.context, allowed_company_ids=cls.company.ids)
        )

        cls.year = date.today().year - 1
        cls.date_from = date(cls.year, 1, 1)
        cls.date_to = date(cls.year, 12, 31)

        # ผังบัญชีควบคุม: ครอบคลุมทุก account_type ที่งบกระแสเงินสดอ้างอิง
        # (ไม่สร้าง off_balance เพื่อให้ผลรวม variation ของทุกประเภท = 0)
        specs = [
            ("1010.00", "เงินสด", "asset_cash"),
            ("1121.00", "ลูกหนี้การค้า", "asset_receivable"),
            ("1140.00", "สินค้าคงเหลือ", "asset_current"),
            ("1310.00", "อาคารและอุปกรณ์", "asset_fixed"),
            ("2130.00", "เจ้าหนี้การค้า", "liability_payable"),
            ("2210.00", "ค่าใช้จ่ายค้างจ่าย", "liability_current"),
            ("2310.00", "เงินกู้ยืมระยะยาว", "liability_non_current"),
            ("3100.00", "ทุนเรือนหุ้น", "equity"),
            ("4110.00", "รายได้จากการขาย", "income"),
            ("5110.00", "ต้นทุนขาย", "expense_direct_cost"),
            ("5210.00", "ค่าใช้จ่ายในการขาย", "expense"),
            ("5300.00", "ค่าเสื่อมราคา", "expense_depreciation"),
        ]
        cls.accounts = {}
        for code, name, account_type in specs:
            cls.accounts[code] = cls.env["account.account"].with_company(
                cls.company
            ).create(
                {
                    "company_ids": cls.company.ids,
                    "code": code,
                    "name": name,
                    "account_type": account_type,
                }
            )

        cls.journal = cls.env["account.journal"].with_company(cls.company).create(
            {
                "company_id": cls.company.id,
                "name": "CF Test Journal",
                "code": "CFT",
                "type": "general",
            }
        )

        moves = [
            [("1010.00", 1_000_000, 0), ("3100.00", 0, 1_000_000)],  # เงินลงทุน
            [("1010.00", 500_000, 0), ("2310.00", 0, 500_000)],  # เงินกู้ระยะยาว
            [("1310.00", 200_000, 0), ("2130.00", 0, 200_000)],  # ซื้ออุปกรณ์เชื่อ
            [("1140.00", 300_000, 0), ("2130.00", 0, 300_000)],  # ซื้อสินค้าเชื่อ
            [("1121.00", 500_000, 0), ("4110.00", 0, 500_000)],  # ขายเชื่อ
            [("1010.00", 500_000, 0), ("1121.00", 0, 500_000)],  # รับชำระลูกหนี้
            [("1010.00", 120_000, 0), ("4110.00", 0, 120_000)],  # ขายสด
            [("5110.00", 300_000, 0), ("1140.00", 0, 300_000)],  # ต้นทุนขาย
            [("5210.00", 50_000, 0), ("1010.00", 0, 50_000)],  # ค่าใช้จ่ายจ่ายสด
            [("5300.00", 20_000, 0), ("1310.00", 0, 20_000)],  # ค่าเสื่อมราคา
            [("2130.00", 300_000, 0), ("1010.00", 0, 300_000)],  # จ่ายเจ้าหนี้
            [("5210.00", 10_000, 0), ("2210.00", 0, 10_000)],  # ค่าใช้จ่ายค้างจ่าย
        ]
        for idx, lines in enumerate(moves, start=1):
            cls._post_move(date(cls.year, 1, min(idx, 28)), lines)

    @classmethod
    def _post_move(cls, move_date, lines):
        move = cls.env["account.move"].with_company(cls.company).create(
            {
                "journal_id": cls.journal.id,
                "date": fields.Date.to_string(move_date),
                "line_ids": [
                    Command.create(
                        {
                            "name": "/",
                            "account_id": cls.accounts[code].id,
                            "debit": debit,
                            "credit": credit,
                        }
                    )
                    for code, debit, credit in lines
                ],
            }
        )
        move._post()
        return move

    def _cf(self):
        report = self.env.ref(CF_REPORT_XMLID)
        aep = report._prepare_aep(self.company)
        return report.evaluate(
            aep,
            fields.Date.to_string(self.date_from),
            fields.Date.to_string(self.date_to),
            target_move="posted",
        )

    # ---------------------------------------------------- A1 : สมการปิด
    def test_a1_cash_flow_identity_closes(self):
        """A1: cf_check = เงินสดต้นงวด + กระแสเงินสดสุทธิ − เงินสดสิ้นงวด = 0."""
        cf = self._cf()
        self.assertLess(
            abs(cf["cf_check"]),
            0.005,
            "cf_check ต้องเป็น 0 แต่ได้ %s" % cf["cf_check"],
        )

    # ---------------------------------------------------- A2 : เงินสดต้น+สุทธิ=ปลาย
    def test_a2_begin_plus_net_equals_end(self):
        """A2: เงินสดต้นงวด + กระแสเงินสดสุทธิ = เงินสดสิ้นงวด และยกมาต้นงวด = 0."""
        cf = self._cf()
        self.assertAlmostEqual(cf["cf_cash_begin"], 0.0, places=2)
        self.assertAlmostEqual(cf["cf_cash_end"], 1_770_000.0, places=2)
        self.assertAlmostEqual(
            cf["cf_cash_begin"] + cf["cf_net_change"],
            cf["cf_cash_end"],
            places=2,
        )
        self.assertAlmostEqual(cf["cf_net_change"], cf["cf_cash_end"], places=2)

    # ---------------------------------------------------- A3 : ยอดแต่ละกิจกรรม
    def test_a3_activity_totals(self):
        """A3: ยอดสุทธิแต่ละกิจกรรมตรงกับที่คำนวณมือจากรายการที่ตั้งไว้."""
        cf = self._cf()
        # กำไรสุทธิสำหรับงวด = 620,000 − 300,000 − 60,000 − 20,000 = 240,000
        self.assertAlmostEqual(cf["cf_op_result"], 240_000.0, places=2)
        # ดำเนินงาน = 240,000 + ค่าเสื่อม 20,000 + เจ้าหนี้เพิ่ม 200,000 + ค้างจ่าย 10,000
        self.assertAlmostEqual(cf["cf_op_total"], 470_000.0, places=2)
        # ลงทุน = −(ซื้ออุปกรณ์ 200,000) (ค่าเสื่อมถูกบวกกลับแล้ว)
        self.assertAlmostEqual(cf["cf_inv_total"], -200_000.0, places=2)
        # จัดหาเงิน = เงินกู้ 500,000 + เงินลงทุน 1,000,000
        self.assertAlmostEqual(cf["cf_fin_total"], 1_500_000.0, places=2)

    # ---------------------------------------------------- A4 : โครงสร้าง instance
    def test_a4_instance_has_three_periods(self):
        """A4: instance งบกระแสเงินสดมี 3 คอลัมน์ (เดือนปัจจุบัน/ก่อน/ปีก่อน)."""
        instance = self.env.ref(CF_INSTANCE_XMLID)
        self.assertEqual(instance.report_id, self.env.ref(CF_REPORT_XMLID))
        self.assertEqual(len(instance.period_ids), 3)


@tagged("post_install", "-at_install")
class TestBudgetVsActual(TransactionCase):
    """งบประมาณ เทียบผลจริง — KPI budgetable + คอลัมน์งบประมาณจาก mis.budget.item."""

    def test_b1_pl_kpis_are_budgetable(self):
        """B1: KPI ใบงบกำไรขาดทุน 12 ตัวต้องตั้ง budgetable=True."""
        kpis = self.env.ref(PL_REPORT_XMLID).kpi_ids
        for name in BUDGETABLE_KPI_NAMES:
            kpi = kpis.filtered(lambda k: k.name == name)
            self.assertTrue(kpi, "ไม่พบ KPI %s" % name)
            self.assertTrue(kpi.budgetable, "KPI %s ต้องเป็น budgetable" % name)

    def test_b2_budget_structure_loaded(self):
        """B2: งบประมาณ + 12 บรรทัดถูกโหลด และทุกบรรทัดอ้าง KPI ของใบ PL."""
        budget = self.env.ref(BUDGET_XMLID)
        pl_report = self.env.ref(PL_REPORT_XMLID)
        self.assertEqual(budget.report_id, pl_report)
        self.assertEqual(len(budget.item_ids), len(BUDGETABLE_KPI_NAMES))
        item_kpis = budget.item_ids.mapped("kpi_expression_id.kpi_id.name")
        self.assertEqual(sorted(item_kpis), sorted(BUDGETABLE_KPI_NAMES))

    def test_b3_budget_column_pulls_amount(self):
        """B3: _query_kpi_data คืนจำนวนเงินงบประมาณของ KPI ตามช่วงวันที่."""
        pl_report = self.env.ref(PL_REPORT_XMLID)
        kpi_4110 = pl_report.kpi_ids.filtered(lambda k: k.name == "pl_4110")
        expression = kpi_4110.expression_ids[:1]
        self.assertTrue(expression, "KPI pl_4110 ต้องมี expression")

        year = date.today().year
        date_from = fields.Date.to_string(date(year, 1, 1))
        date_to = fields.Date.to_string(date(year, 12, 31))

        budget = self.env["mis.budget"].create(
            {
                "name": "UT Budget (Budget vs Actual test)",
                "report_id": pl_report.id,
                "date_from": date_from,
                "date_to": date_to,
            }
        )
        self.env["mis.budget.item"].create(
            {
                "budget_id": budget.id,
                "kpi_expression_id": expression.id,
                "date_from": date_from,
                "date_to": date_to,
                "amount": 2500.0,
            }
        )
        result = self.env["mis.budget.item"]._query_kpi_data(
            date_from, date_to, [("budget_id", "=", budget.id)]
        )
        self.assertAlmostEqual(result.get(expression), 2500.0, places=2)

    def test_b4_instance_has_budget_period(self):
        """B4: instance งบประมาณเทียบผลจริงมีคอลัมน์ที่ดึงจาก mis.budget."""
        instance = self.env.ref(BVA_INSTANCE_XMLID)
        budget = self.env.ref(BUDGET_XMLID)
        budget_periods = instance.period_ids.filtered(
            lambda p: p.source == "mis_budget"
        )
        self.assertTrue(budget_periods, "ต้องมีคอลัมน์ source=mis_budget")
        self.assertEqual(
            set(budget_periods.mapped("source_mis_budget_id").ids), {budget.id}
        )
