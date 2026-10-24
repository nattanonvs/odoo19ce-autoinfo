# -*- coding: utf-8 -*-
from odoo import api, fields, models

# ชื่อของ tier definition ทั้งสองรายการใช้เป็นกุญแจอ้างอิงในการ sync
OD19_SALE_TIER_MANAGER = "Sale Order Approval (Sales Manager)"
OD19_SALE_TIER_DIRECTOR = "Sale Order Approval (Sales Director)"


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_so_manager_approval_threshold = fields.Monetary(
        string="Sale Order Manager Approval Threshold",
        currency_field="currency_id",
        default=100000.0,
        help="Sale orders at or above this amount require approval from a Sales "
        "Manager (and below the director threshold).",
    )
    od19_so_director_approval_threshold = fields.Monetary(
        string="Sale Order Director Approval Threshold",
        currency_field="currency_id",
        default=500000.0,
        help="Sale orders at or above this amount require approval from a Sales "
        "Director.",
    )

    def _od19_sale_tier_domains(self):
        """คืนค่า domain ของ tier เป็น string literal ตามวงเงินของบริษัท

        ``tier.definition.definition_domain`` ถูกประเมินด้วย ``literal_eval``
        ในเครื่องยนต์ tier validation ดังนั้นต้องเป็น string ของ Python literal
        ไม่ใช่ domain แบบ dynamic จึงต้องสร้างใหม่ทุกครั้งที่วงเงินเปลี่ยน
        """
        self.ensure_one()
        manager = self.od19_so_manager_approval_threshold
        director = self.od19_so_director_approval_threshold
        return {
            OD19_SALE_TIER_MANAGER: repr(
                [("amount_total", ">=", manager), ("amount_total", "<", director)]
            ),
            OD19_SALE_TIER_DIRECTOR: repr([("amount_total", ">=", director)]),
        }

    def _od19_sync_sale_tier_definitions(self):
        """สร้าง/ปรับปรุง tier definition ของบริษัทนี้ให้ตรงกับวงเงินปัจจุบัน"""
        self.ensure_one()
        TierDefinition = self.env["tier.definition"].sudo()
        model_id = self.env["ir.model"].sudo()._get_id("sale.order")
        reviewers = {
            OD19_SALE_TIER_MANAGER: self.env.ref("sales_team.group_sale_manager").id,
            OD19_SALE_TIER_DIRECTOR: self.env.ref(
                "od19_sales_oca_bridge_workflow.group_sale_director"
            ).id,
        }
        sequences = {OD19_SALE_TIER_MANAGER: 10, OD19_SALE_TIER_DIRECTOR: 20}
        domains = self._od19_sale_tier_domains()
        for name, domain in domains.items():
            vals = {
                "name": name,
                "model_id": model_id,
                "review_type": "group",
                "reviewer_group_id": reviewers[name],
                "definition_type": "domain",
                "definition_domain": domain,
                "sequence": sequences[name],
                "company_id": self.id,
            }
            tier = TierDefinition.search(
                [
                    ("model", "=", "sale.order"),
                    ("company_id", "=", self.id),
                    ("name", "=", name),
                ],
                limit=1,
            )
            if tier:
                tier.write(vals)
            else:
                TierDefinition.create(vals)
        # ลบ record แบบเดิมที่ไม่ได้ผูกบริษัทและฮาร์ดโค้ดวงเงินไว้ (ถ้ามีตกค้าง)
        TierDefinition.search(
            [
                ("model", "=", "sale.order"),
                ("company_id", "=", False),
                ("name", "in", list(domains)),
            ]
        ).unlink()

    @api.model
    def _od19_sync_all_sale_tier_definitions(self):
        """Sync tier definition ให้ทุกบริษัท (เรียกจาก data file ตอน install/upgrade)"""
        for company in self.search([]):
            company._od19_sync_sale_tier_definitions()

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        for company in companies:
            company._od19_sync_sale_tier_definitions()
        return companies

    def write(self, vals):
        res = super().write(vals)
        if {
            "od19_so_manager_approval_threshold",
            "od19_so_director_approval_threshold",
        } & set(vals):
            for company in self:
                company._od19_sync_sale_tier_definitions()
        return res
