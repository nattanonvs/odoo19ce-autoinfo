# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

DRAFT = "draft"
ACTIVE = "active"
SUPERSEDED = "superseded"

LIST_STATE = [
    (DRAFT, "ฉบับร่าง"),
    (ACTIVE, "ประกาศใช้"),
    (SUPERSEDED, "ถูกแทนที่ (มี revision ใหม่)"),
]

COPY_TYPE = [
    ("controlled", "สำเนาควบคุม (Controlled)"),
    ("uncontrolled", "สำเนาไม่ควบคุม (Uncontrolled)"),
]


class Od19IsoDistributionList(models.Model):
    """ทะเบียนแจกจ่าย (Distribution List) — revision-driven."""

    _name = "od19.iso.distribution.list"
    _description = "ISO Distribution List"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "document_id, revision desc, id desc"
    _rec_name = "name"
    _check_company_auto = True

    name = fields.Char(
        string="เลขที่ทะเบียน",
        default="/",
        copy=False,
        readonly=True,
        help="รูปแบบ DL{yy}-{NNN} เช่น DL26-001",
    )
    document_id = fields.Many2one(
        "od19.iso.document",
        string="เอกสาร",
        required=True,
        ondelete="cascade",
    )
    revision = fields.Char(
        string="Revision (snapshot)",
        help="revision ของเอกสาร ณ ตอนประกาศใช้",
    )
    effective_date = fields.Date(
        string="วันที่มีผล", default=fields.Date.today
    )
    state = fields.Selection(
        LIST_STATE, string="สถานะ", default=DRAFT, required=True, tracking=True
    )
    line_ids = fields.One2many(
        "od19.iso.distribution.line", "distribution_list_id", string="ผู้รับ"
    )
    line_count = fields.Integer(
        string="จำนวนผู้รับ", compute="_compute_line_count"
    )
    note = fields.Text(string="หมายเหตุ")
    company_id = fields.Many2one(
        "res.company", string="บริษัท", default=lambda self: self.env.company
    )

    @api.depends("line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    # ------------------------------------------------------------------
    # Numbering
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "/":
                vals["name"] = self._generate_name()
            if vals.get("document_id") and not vals.get("revision"):
                document = self.env["od19.iso.document"].browse(
                    vals["document_id"]
                )
                vals["revision"] = document.revision
        return super().create(vals_list)

    @api.model
    def _generate_name(self):
        """สร้างเลขที่ DL{yy}-{NNN} จาก ir.sequence od19.iso.distribution.list."""
        year2 = fields.Date.today().strftime("%y")
        sequence = self.env.ref(
            "od19_iso_print_control.seq_iso_distribution_list",
            raise_if_not_found=False,
        )
        number = sequence.next_by_id() if sequence else "001"
        try:
            number = "%03d" % int(number)
        except (TypeError, ValueError):
            number = str(number)
        return "DL%s-%s" % (year2, number)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def action_activate(self):
        for rec in self:
            if rec.state == ACTIVE:
                continue
            if not rec.line_ids:
                raise UserError(
                    _("ต้องมีผู้รับอย่างน้อย 1 รายก่อนประกาศใช้ทะเบียนแจกจ่าย")
                )
            # ทะเบียน active อื่นของเอกสารเดียวกัน → superseded
            siblings = self.search([
                ("document_id", "=", rec.document_id.id),
                ("state", "=", ACTIVE),
                ("id", "!=", rec.id),
            ])
            siblings.write({"state": SUPERSEDED})
            rec.state = ACTIVE
            rec.message_post(
                body=_("ประกาศใช้ทะเบียนแจกจ่าย %s (Rev.%s)")
                % (rec.name, rec.revision or "-")
            )

    def action_supersede(self):
        for rec in self:
            rec.state = SUPERSEDED
            rec.message_post(body=_("ตั้งทะเบียนแจกจ่าย %s เป็น superseded") % rec.name)

    def action_reset_draft(self):
        for rec in self:
            if rec.state == SUPERSEDED:
                raise UserError(_("ไม่สามารถย้อนสถานะจาก superseded ได้"))
            rec.state = DRAFT


class Od19IsoDistributionLine(models.Model):
    """บรรทัดผู้รับในทะเบียนแจกจ่าย."""

    _name = "od19.iso.distribution.line"
    _description = "ISO Distribution Line"
    _order = "distribution_list_id, id"

    distribution_list_id = fields.Many2one(
        "od19.iso.distribution.list",
        string="ทะเบียนแจกจ่าย",
        required=True,
        ondelete="cascade",
    )
    document_id = fields.Many2one(
        "od19.iso.document",
        string="เอกสาร",
        related="distribution_list_id.document_id",
        store=True,
        readonly=True,
    )
    recipient_id = fields.Many2one("res.users", string="ผู้รับ (ภายใน)")
    holder_name = fields.Char(string="ชื่อผู้รับ (ภายนอก)")
    department_id = fields.Many2one("hr.department", string="แผนกผู้รับ")
    copies_required = fields.Integer(string="จำนวนสำเนาที่ต้องได้", default=1)
    copy_type = fields.Selection(
        COPY_TYPE, string="ประเภทสำเนา", default="controlled", required=True
    )
    acknowledged = fields.Boolean(string="รับทราบ/ลงนามรับแล้ว")
    note = fields.Char(string="หมายเหตุ")

    @api.onchange("recipient_id")
    def _onchange_recipient_id(self):
        for rec in self:
            if rec.recipient_id:
                employee = rec.recipient_id.employee_id
                if employee and employee.department_id:
                    rec.department_id = employee.department_id
