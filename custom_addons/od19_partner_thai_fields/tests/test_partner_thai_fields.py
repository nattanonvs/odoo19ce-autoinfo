# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase


class TestPartnerThaiFields(TransactionCase):
    """Basic tests for Thai-specific partner and company fields."""

    def test_partner_thai_fields_creation(self):
        partner = self.env["res.partner"].create({
            "name": "บริษัท ทดสอบ จำกัด",
            "tax_name": "บริษัท ทดสอบ จำกัด (สำนักงานใหญ่)",
            "branch_code": "00000",
            "name_en": "Test Company Limited",
            "address_en": "123 Test Street, Bangkok",
            "fax": "02-123-4567",
        })
        self.assertEqual(partner.tax_name, "บริษัท ทดสอบ จำกัด (สำนักงานใหญ่)")
        self.assertEqual(partner.branch_code, "00000")
        self.assertEqual(partner.name_en, "Test Company Limited")
        self.assertEqual(partner.address_en, "123 Test Street, Bangkok")
        self.assertEqual(partner.fax, "02-123-4567")

    def test_company_related_thai_fields(self):
        company = self.env.user.company_id
        # Set values on the company's partner
        company.partner_id.write({
            "tax_name": "Auto Info Co., Ltd.",
            "branch_code": "00000",
            "name_en": "Auto Info Co., Ltd.",
            "address_en": "Bangkok, Thailand",
            "fax": "02-000-0000",
        })
        # Company fields should mirror the partner fields
        self.assertEqual(company.tax_name, "Auto Info Co., Ltd.")
        self.assertEqual(company.branch_code, "00000")
        self.assertEqual(company.name_en, "Auto Info Co., Ltd.")
        self.assertEqual(company.address_en, "Bangkok, Thailand")
        self.assertEqual(company.fax, "02-000-0000")

    def test_branch_code_size(self):
        partner = self.env["res.partner"].create({
            "name": "Branch Size Test",
            "branch_code": "12345",
        })
        self.assertEqual(partner.branch_code, "12345")

    def test_amphoe_subdistrict_fields(self):
        partner = self.env["res.partner"].create({
            "name": "ที่อยู่ไทย ทดสอบ",
            "od19_subdistrict": "แขวงคลองเตย",
            "od19_amphoe": "เขตคลองเตย",
        })
        self.assertEqual(partner.od19_subdistrict, "แขวงคลองเตย")
        self.assertEqual(partner.od19_amphoe, "เขตคลองเตย")

    def test_company_amphoe_subdistrict_related(self):
        company = self.env.user.company_id
        company.partner_id.write({
            "od19_subdistrict": "แขวงสีลม",
            "od19_amphoe": "เขตบางรัก",
        })
        # Company fields should mirror the partner fields
        self.assertEqual(company.od19_subdistrict, "แขวงสีลม")
        self.assertEqual(company.od19_amphoe, "เขตบางรัก")

    def test_branch_name_from_branch_code_head_office(self):
        """A company with branch_code '00000' reports the head office even when
        no country is set (core l10n_th would leave the label empty)."""
        partner = self.env["res.partner"].create({
            "name": "ผู้ซื้อ ไม่ตั้งประเทศ จำกัด",
            "is_company": True,
            "branch_code": "00000",
        })
        self.assertFalse(partner.country_id)
        self.assertEqual(partner.l10n_th_branch_name, "Headquarter")

    def test_branch_name_from_branch_code_branch(self):
        partner = self.env["res.partner"].create({
            "name": "สาขา ทดสอบ จำกัด",
            "is_company": True,
            "branch_code": "00001",
        })
        self.assertEqual(partner.l10n_th_branch_name, "Branch 00001")

    def test_branch_name_falls_back_to_core(self):
        """Without branch_code the core l10n_th behaviour is preserved."""
        thailand = self.env["res.country"].search([("code", "=", "TH")], limit=1)
        partner = self.env["res.partner"].create({
            "name": "ผู้ขาย ไทย จำกัด",
            "is_company": True,
            "country_id": thailand.id,
        })
        self.assertEqual(partner.l10n_th_branch_name, "Headquarter")
