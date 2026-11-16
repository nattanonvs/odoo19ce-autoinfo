from odoo import api, fields, models

from .internal_issue_common import ISSUE_STREAM_SELECTION


class HelpdeskRoutingRule(models.Model):
    _name = "helpdesk.routing.rule"
    _description = "Internal Issue Routing Rule"
    _order = "sequence, id"

    name = fields.Char(string="ชื่อกฎ", required=True)
    keyword = fields.Char(
        string="คำสำคัญ",
        required=True,
        help="ค้นหาแบบไม่สนตัวพิมพ์ในชื่อเรื่อง + รายละเอียด",
    )
    issue_stream = fields.Selection(
        ISSUE_STREAM_SELECTION,
        string="ประเภทเรื่อง",
        help="ปล่อยว่าง = ใช้กับทุกประเภท",
    )
    team_id = fields.Many2one(comodel_name="helpdesk.ticket.team", string="ทีมปลายทาง")
    category_id = fields.Many2one(
        comodel_name="helpdesk.ticket.category", string="หมวดปลายทาง"
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    @api.model
    def _match_text(self, text, issue_stream=None):
        """คืน rule แรกที่ keyword ปรากฏใน ``text`` (เรียงตาม sequence, id).

        กรองตาม ``issue_stream``: กฎที่ผูก stream ไว้จะถูกใช้เฉพาะเมื่อตรงกับ
        ``issue_stream`` ที่ส่งมา ส่วนกฎที่ปล่อย stream ว่างใช้ได้กับทุกประเภท
        """
        text = (text or "").lower()
        if not text:
            return self.browse()
        for rule in self.search([("active", "=", True)], order="sequence, id"):
            if rule.issue_stream and rule.issue_stream != issue_stream:
                continue
            if rule.keyword and rule.keyword.lower() in text:
                return rule
        return self.browse()
