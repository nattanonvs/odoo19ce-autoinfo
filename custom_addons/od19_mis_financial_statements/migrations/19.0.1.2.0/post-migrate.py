import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

MODULE = "od19_mis_financial_statements"

# KPI ระดับหัวข้อบัญชีของงบกำไรขาดทุน ที่ต้องเปิดให้ตั้งงบประมาณได้ (budgetable)
# เพื่อให้คอลัมน์ "งบประมาณ" ของรายงาน Budget vs Actual คำนวณได้
BUDGETABLE_KPIS = [
    "mis_kpi_pl_4110",
    "mis_kpi_pl_4120",
    "mis_kpi_pl_5110",
    "mis_kpi_pl_5120",
    "mis_kpi_pl_4200",
    "mis_kpi_pl_4300",
    "mis_kpi_pl_5130",
    "mis_kpi_pl_5210",
    "mis_kpi_pl_5300",
    "mis_kpi_pl_5400",
    "mis_kpi_pl_5410",
    "mis_kpi_pl_5420",
]


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid in BUDGETABLE_KPIS:
        kpi = env.ref(f"{MODULE}.{xmlid}", raise_if_not_found=False)
        if not kpi:
            _logger.warning("%s: KPI %s not found, skipped", MODULE, xmlid)
            continue
        if not kpi.budgetable:
            kpi.sudo().budgetable = True
            _logger.info("%s: set %s budgetable=True", MODULE, xmlid)
