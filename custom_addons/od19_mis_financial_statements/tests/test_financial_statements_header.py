# -*- coding: utf-8 -*-
"""Test gate §7 (T1-T5) ของโมดูล od19_mis_financial_statements.

Spec: docs/superpowers/specs/2026-11-23-od19-financial-statements-header-design.md

    T1  รวม KPI แบบ ค (ระดับหัวข้อ) = ผลรวมแบบ account_type        ผลต่าง = 0.00
    T2  สมการงบดุล  สินทรัพย์ − (หนี้สิน + ทุน) = 0.00             ผลต่าง = 0.00
    T3  กำไรสุทธิ MIS = กำไรสุทธิ Jasper                            ตรงกัน
    T4  ครอบคลุมทุกบัญชี postable ที่มี movement                    ไม่มีบัญชีตกหล่น
    T5  ข้อยกเว้น prefix (1120 = 112x ∪ 1130x, 1131 แยก, 52x/53xx)  ยอดตรงตาม prefix

การทดสอบใช้บริษัทใหม่ที่ผังบัญชีถูกควบคุม (สร้างเองทั้งหมด แบบผังไทยมีจุด)
เพื่อให้เทียบตัวเลขกับ \"ผลรวมตาม account_type\" และ Jasper ได้อย่าง deterministic
"""
import calendar
from datetime import date

from odoo import Command, fields
from odoo.tests.common import TransactionCase, tagged

BS_REPORT_XMLID = "od19_mis_financial_statements.mis_report_balance_sheet"
PL_REPORT_XMLID = "od19_mis_financial_statements.mis_report_profit_loss"


@tagged("post_install", "-at_install")
class TestFinancialStatementsHeader(TransactionCase):
    """แบบ ค — งบแสดงฐานะทางการเงิน / งบกำไรขาดทุน ระดับหัวข้อบัญชี."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # บริษัทใหม่: ไม่ระบุ country_id เพื่อไม่ให้ Odoo ไปโหลดผังบัญชี (l10n)
        # อัตโนมัติ — เราสร้างผังที่ควบคุมเองทั้งหมด
        cls.company = cls.env["res.company"].create(
            {"name": "OD19 FS Header Test Co"}
        )
        cls.env = cls.env(
            context=dict(cls.env.context, allowed_company_ids=cls.company.ids)
        )

        # ปีที่ใช้ทดสอบ = ปีก่อนหน้า (ให้วันที่ผ่านมาแล้วทั้งหมด)
        cls.year = date.today().year - 1
        cls.date_from = date(cls.year, 1, 1)
        cls.date_to = date(cls.year, 12, 31)
        cls.eom_month = 12  # Jasper ใช้สิ้นเดือนธันวาคม

        # ---------------------------------------------------------- ผังบัญชี
        # (code, name, account_type) — เฉพาะ prefix ที่รายงานรองรับ (แบบ ค)
        specs = [
            ("1110.00", "เงินสดและเงินฝากธนาคาร", "asset_cash"),
            ("1121.00", "ลูกหนี้การค้า", "asset_receivable"),
            ("1122.00", "ลูกหนี้อื่น", "asset_receivable"),
            ("1130.00", "ค่าใช้จ่ายจ่ายล่วงหน้า", "asset_current"),
            ("1131.00", "เงินทดรองจ่าย", "asset_current"),
            ("1140.00", "สินค้าคงเหลือ", "asset_current"),
            ("1210.00", "เงินลงทุนระยะยาว", "asset_non_current"),
            ("1310.00", "อาคารและอุปกรณ์", "asset_fixed"),
            ("1410.00", "เงินมัดจำและเงินค้ำประกัน", "asset_prepayments"),
            ("2110.00", "เงินเบิกเกินบัญชี", "liability_current"),
            ("2130.00", "เจ้าหนี้การค้า", "liability_payable"),
            ("2210.00", "หนี้สินหมุนเวียนอื่น", "liability_current"),
            ("2310.00", "เงินกู้ยืมระยะยาว", "liability_non_current"),
            ("3100.00", "ทุนเรือนหุ้น", "equity"),
            ("3200.00", "สำรองตามกฎหมาย", "equity"),
            ("3300.00", "กำไรสะสม", "equity"),
            ("4110.00", "รายได้จากการขาย", "income"),
            ("4120.00", "รายได้จากการบริการ", "income"),
            ("4200.00", "กำไรจากอัตราแลกเปลี่ยน", "income_other"),
            ("4300.00", "รายได้อื่น", "income_other"),
            ("5110.00", "ต้นทุนขาย", "expense_direct_cost"),
            ("5120.00", "ต้นทุนบริการ", "expense_direct_cost"),
            ("5130.00", "ขาดทุนจากอัตราแลกเปลี่ยน", "expense"),
            ("5210.00", "ค่าใช้จ่ายในการขาย", "expense"),
            ("5300.00", "ค่าใช้จ่ายในการบริหาร", "expense"),
            ("5400.00", "ต้นทุนทางการเงิน", "expense"),
            ("5410.00", "ค่าใช้จ่ายต้องห้ามตามประมวลรัษฎากร", "expense"),
            ("5420.00", "ภาษีเงินได้นิติบุคคล", "expense"),
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
        cls.all_account_ids = [acc.id for acc in cls.accounts.values()]

        cls.journal = cls.env["account.journal"].with_company(cls.company).create(
            {
                "company_id": cls.company.id,
                "name": "FS Test Journal",
                "code": "FST",
                "type": "general",
            }
        )

        # ---------------------------------------------------------- รายการ
        # ทุก move ต้องสมดุล (Dr = Cr)
        moves = [
            # ทุน: เงินสด ← ทุนเรือนหุ้น
            [("1110.00", 1_000_000, 0), ("3100.00", 0, 1_000_000)],
            # ซื้ออุปกรณ์เป็นเงินเชื่อ
            [("1310.00", 200_000, 0), ("2130.00", 0, 200_000)],
            # ซื้อสินค้าคงเหลือเป็นเงินเชื่อ
            [("1140.00", 300_000, 0), ("2130.00", 0, 300_000)],
            # ขายสินค้าเป็นเงินเชื่อ
            [("1121.00", 500_000, 0), ("4110.00", 0, 500_000)],
            # รับชำระจากลูกหนี้
            [("1110.00", 500_000, 0), ("1121.00", 0, 500_000)],
            # เงินทดรองจ่าย (เพื่อให้ 1131 มี movement — พิสูจน์ว่า bs_1120 ไม่รวม 1131)
            [("1131.00", 20_000, 0), ("1110.00", 0, 20_000)],
            # ต้นทุนขาย
            [("5110.00", 300_000, 0), ("1140.00", 0, 300_000)],
            # รายได้บริการ (เงินสด)
            [("1110.00", 120_000, 0), ("4120.00", 0, 120_000)],
            # รายได้อื่น
            [("1122.00", 30_000, 0), ("4300.00", 0, 30_000)],
            # ค่าใช้จ่ายในการขาย (จ่ายเงินสด)
            [("5210.00", 50_000, 0), ("1110.00", 0, 50_000)],
            # ค่าใช้จ่ายในการบริหาร (จ่ายเงินสด)
            [("5300.00", 80_000, 0), ("1110.00", 0, 80_000)],
            # ต้นทุนทางการเงิน (ค้างจ่าย)
            [("5400.00", 10_000, 0), ("2210.00", 0, 10_000)],
            # ชำระเจ้าหนี้การค้า
            [("2130.00", 300_000, 0), ("1110.00", 0, 300_000)],
        ]
        for idx, lines in enumerate(moves, start=1):
            cls._post_move(date(cls.year, 1, min(idx, 28)), lines)

    # ---------------------------------------------------------------- helper
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

    def _evaluate(self, report, date_from, date_to):
        aep = report._prepare_aep(self.company)
        return report.evaluate(
            aep,
            fields.Date.to_string(date_from),
            fields.Date.to_string(date_to),
            target_move="posted",
        )

    def _bs(self):
        report = self.env.ref(BS_REPORT_XMLID)
        return self._evaluate(report, self.date_from, self.date_to)

    def _pl(self):
        report = self.env.ref(PL_REPORT_XMLID)
        return self._evaluate(report, self.date_from, self.date_to)

    def _account_balance(self, code):
        """ยอดคงเหลือ (เดบิต − เครดิต) ของบัญชีหนึ่ง จาก move line ที่ post แล้ว."""
        acc = self.accounts[code]
        lines = self.env["account.move.line"].with_company(self.company).search(
            [
                ("company_id", "=", self.company.id),
                ("parent_state", "=", "posted"),
                ("account_id", "=", acc.id),
            ]
        )
        return sum(lines.mapped("balance"))

    def _group_balance(self, internal_group):
        """ผลรวม (เดบิต − เครดิต) ของทุกบัญชีใน internal_group หนึ่ง ๆ."""
        lines = self.env["account.move.line"].with_company(self.company).search(
            [
                ("company_id", "=", self.company.id),
                ("parent_state", "=", "posted"),
                ("account_id.internal_group", "=", internal_group),
            ]
        )
        return sum(lines.mapped("balance"))

    # ------------------------------------------------------------------ T1
    def test_t1_header_equals_account_type_total(self):
        """T1: ผลรวม KPI ระดับหัวข้อ = ผลรวมตาม account_type (ผลต่าง 0.00)."""
        bs = self._bs()
        pl = self._pl()

        asset = self._group_balance("asset")
        liability = self._group_balance("liability")
        equity = self._group_balance("equity")
        income = self._group_balance("income")
        expense = self._group_balance("expense")
        # กำไรสุทธิตาม account_type: รายได้ (+) หัก ค่าใช้จ่าย (−)
        pl_expected = -(income + expense)

        # ฝั่งสินทรัพย์
        self.assertAlmostEqual(bs["bs_total_assets"], asset, places=2)
        # ฝั่งหนี้สิน (ใช้เครื่องหมาย −bale → ค่าบวก)
        self.assertAlmostEqual(bs["bs_total_liab"], -liability, places=2)
        # ฝั่งทุน = บัญชีทุน + กำไรสุทธิสำหรับงวด (bs_3400)
        self.assertAlmostEqual(
            bs["bs_total_equity"], -equity + pl_expected, places=2
        )
        # กำไรสุทธิของ MIS
        self.assertAlmostEqual(pl["pl_net"], pl_expected, places=2)
        self.assertAlmostEqual(bs["bs_3400"], pl_expected, places=2)

        # roll-up ภายใน (ผลรวมบรรทัด = ยอดรวมย่อย)
        self.assertAlmostEqual(
            bs["bs_1110"] + bs["bs_1120"] + bs["bs_1131"] + bs["bs_1140"] + bs["bs_1150"],
            bs["bs_cur_assets"],
            places=2,
        )
        self.assertAlmostEqual(
            bs["bs_1210"] + bs["bs_1310"] + bs["bs_1320"] + bs["bs_1410"],
            bs["bs_noncur_assets"],
            places=2,
        )
        self.assertAlmostEqual(
            bs["bs_cur_assets"] + bs["bs_noncur_assets"],
            bs["bs_total_assets"],
            places=2,
        )

    # ------------------------------------------------------------------ T2
    def test_t2_balance_sheet_equation(self):
        """T2: สมการงบดุล สินทรัพย์ − (หนี้สิน + ทุน) = 0.00."""
        bs = self._bs()
        self.assertLess(
            abs(bs["bs_check"]),
            0.005,
            "bs_check ต้องเป็น 0: %s" % bs["bs_check"],
        )
        self.assertAlmostEqual(
            bs["bs_total_assets"], bs["bs_liab_equity_total"], places=2
        )

    # ------------------------------------------------------------------ T3
    def test_t3_net_profit_matches_jasper(self):
        """T3: กำไรสุทธิ MIS (pl_net) = กำไรสุทธิจาก engine Jasper (pl_balance)."""
        if not self.env.registry.get("balance.sheet.report"):
            self.skipTest("od19_reporting_jasper ไม่ได้ติดตั้งในฐานข้อมูลทดสอบ")

        pl = self._pl()
        jasper = self.env["balance.sheet.report"].create(
            {
                "company_id": self.company.id,
                "rpt_year": str(self.year),
                "rpt_month": str(self.eom_month),
                "target_move": "posted",
                "report_template": "pl_bs_header",
            }
        )
        parms = jasper.get_parameters()
        jasper_net = float(parms["pl_balance"])
        self.assertAlmostEqual(pl["pl_net"], jasper_net, places=2)
        # งบดุลของ MIS ต้องป้อนกำไรสุทธิเท่ากันที่ bs_3400 เช่นกัน
        bs = self._bs()
        self.assertAlmostEqual(bs["bs_3400"], jasper_net, places=2)

    # ------------------------------------------------------------------ T4
    def test_t4_all_moved_accounts_are_covered(self):
        """T4: ทุกบัญชี postable ที่มี movement ต้องถูก KPI อย่างน้อยหนึ่งตัวจับ."""
        bs_report = self.env.ref(BS_REPORT_XMLID)
        pl_report = self.env.ref(PL_REPORT_XMLID)
        covered = set(bs_report.get_kpis_by_account_id(self.company)) | set(
            pl_report.get_kpis_by_account_id(self.company)
        )

        moved_lines = self.env["account.move.line"].with_company(self.company).search(
            [
                ("company_id", "=", self.company.id),
                ("parent_state", "=", "posted"),
            ]
        )
        moved = set(moved_lines.mapped("account_id").ids)

        missing = moved - covered
        self.assertFalse(
            missing,
            "มีบัญชีที่เคลื่อนไหวแต่ไม่ถูก KPI ใดจับ: %s"
            % sorted(self.env["account.account"].browse(missing).mapped("code")),
        )
        # ทุกบัญชีที่เราสร้างต้องถูกจับด้วย (ไม่หวังผลข้ามผัง)
        uncovered_created = set(self.all_account_ids) - covered
        self.assertFalse(
            uncovered_created,
            "บัญชีที่สร้างไว้แต่ไม่ถูก KPI จับ: %s"
            % sorted(
                self.env["account.account"].browse(uncovered_created).mapped("code")
            ),
        )

    # ------------------------------------------------------------------ T5
    def test_t5_prefix_exceptions(self):
        """T5: ข้อยกเว้น prefix — 1120 = 112x ∪ 1130x, 1131 แยก, 52x/53xx แยกช่วง."""
        bs = self._bs()
        pl = self._pl()

        # bs_1120 รวม 112x + 1130x (ไม่รวม 1131)
        expected_1120 = (
            self._account_balance("1121.00")
            + self._account_balance("1122.00")
            + self._account_balance("1130.00")
        )
        self.assertAlmostEqual(bs["bs_1120"], expected_1120, places=2)

        # bs_1131 แยกจากกลุ่ม 1120
        self.assertAlmostEqual(
            bs["bs_1131"], self._account_balance("1131.00"), places=2
        )
        self.assertNotAlmostEqual(
            bs["bs_1120"], expected_1120 + self._account_balance("1131.00")
        )

        # ต้นทุนขาย/บริการ/อัตราแลกเปลี่ยน แยกช่วง 511 / 512 / 5130
        self.assertAlmostEqual(
            pl["pl_5110"], -self._account_balance("5110.00"), places=2
        )
        self.assertAlmostEqual(
            pl["pl_5120"], -self._account_balance("5120.00"), places=2
        )
        self.assertAlmostEqual(
            pl["pl_5130"], -self._account_balance("5130.00"), places=2
        )

        # ค่าใช้จ่ายดำเนินงาน 52x (521x) และ 53xx แยกช่วงกัน
        self.assertAlmostEqual(
            pl["pl_5210"], -self._account_balance("5210.00"), places=2
        )
        self.assertAlmostEqual(
            pl["pl_5300"], -self._account_balance("5300.00"), places=2
        )
        # ต้นทุนทางการเงิน 540x แยกจาก 542x (ภาษี)
        self.assertAlmostEqual(
            pl["pl_5400"], -self._account_balance("5400.00"), places=2
        )
        self.assertAlmostEqual(
            pl["pl_5420"], -self._account_balance("5420.00"), places=2
        )
