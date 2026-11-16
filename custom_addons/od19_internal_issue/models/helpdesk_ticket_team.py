from odoo import fields, models

from .internal_issue_common import ISSUE_STREAM_SELECTION


class HelpdeskTicketTeam(models.Model):
    _inherit = "helpdesk.ticket.team"

    issue_stream = fields.Selection(
        ISSUE_STREAM_SELECTION,
        string="ประเภทเรื่องที่รับ",
        help="ใช้ route เรื่องอัตโนมัติเมื่อผู้แจ้งเลือก issue_stream นี้",
    )
    is_triage_team = fields.Boolean(
        string="กล่องกลาง (Triage)",
        default=False,
        help="รับเรื่องที่ผู้แจ้งเลือก 'ไม่แน่ใจ' เพื่อให้ agent จัดต่อ",
    )
    weekly_priority_quota = fields.Integer(
        string="โควตางานด่วน/สัปดาห์",
        default=5,
        help="เพดานจำนวนงาน priority สูงต่อสัปดาห์; เกินโควต้าต้องขออนุมัติแซงคิว",
    )
