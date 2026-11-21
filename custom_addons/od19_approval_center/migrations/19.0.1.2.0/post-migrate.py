import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """K8: ย้าย source ของค่าใช้จ่ายจาก hr.expense ไปที่หัวใบ od19.expense.claim.

    ``post_init_hook`` รันเฉพาะตอนติดตั้ง จึงไม่ทำงานบน DB ที่อัปเดตด้วย ``-u``
    (เช่น odoo19_pdev/odoo19_puat ที่ seed source ไว้แล้ว) — migration นี้จึง
    repoint source เดิมให้ชี้หัวใบแทน เพื่อให้ Approval Center เห็นงานอนุมัติที่
    ย้ายไปอยู่บนหัวใบแล้ว
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    if "od19.expense.claim" not in env:
        _logger.info(
            "Approval Center: od19.expense.claim not installed, skip K8 repoint"
        )
        return
    source = env["od19.approval.source"].search(
        [("model_name", "=", "hr.expense")], limit=1
    )
    if not source:
        _logger.info("Approval Center: hr.expense source not found, skip K8 repoint")
        return
    source.write({
        "name": "ใบเบิกค่าใช้จ่าย (Expense Claim)",
        "model_id": env["ir.model"]._get("od19.expense.claim").id,
        "icon": "fa-money",
        "action_xmlid": "od19_hr_expense_claim.action_od19_expense_claim_all",
        "requester_field": "employee_id",
        "requester_kind": "employee",
        "submitted_date_field": "submit_date",
        "rejected_states": "refused",
        "success_states": "approved,posted,paid",
        "strategy": "tier_validation",
        "sla_days": 3,
    })
    source.step_ids.unlink()
    _logger.info(
        "Approval Center: expense source %s repointed to od19.expense.claim",
        source.id,
    )
