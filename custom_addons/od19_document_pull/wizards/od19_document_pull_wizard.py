# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class Od19DocumentPullWizard(models.TransientModel):
    _name = "od19.document.pull.wizard"
    _description = "OD19 Document Pull Wizard"

    res_model = fields.Char(
        string="Destination Model / โมเดลปลายทาง", required=True
    )
    res_id = fields.Integer(
        string="Destination ID / รหัสเอกสารปลายทาง", required=True
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner / คู่ค้า",
        compute="_compute_partner_id",
    )
    source_ref = fields.Reference(
        selection="_selection_source_ref",
        string="Source Document / เอกสารต้นทาง",
    )
    mode = fields.Selection(
        selection=[
            ("all_order", "All lines (document order) / ทั้งหมดตามลำดับเอกสาร"),
            ("select", "Select lines / เลือกรายบรรทัด"),
        ],
        string="Pull Mode / โหมดการดึง",
        default="all_order",
        required=True,
    )
    line_ids = fields.One2many(
        comodel_name="od19.document.pull.wizard.line",
        inverse_name="wizard_id",
        string="Lines / รายการ",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _od19_get_target(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id)

    @api.depends("res_model", "res_id")
    def _compute_partner_id(self):
        for wizard in self:
            target = (
                wizard._od19_get_target()
                if wizard.res_model and wizard.res_id
                else False
            )
            wizard.partner_id = (
                getattr(target, "partner_id", False) if target else False
            )

    @api.model
    def _selection_source_ref(self):
        """Models selectable as a source document on a pull wizard.

        The ORM evaluates a Reference selection on an empty recordset, both to
        render the widget and to validate values, so this list is static and
        context-independent. Which sources a given destination actually accepts
        is enforced by ``_od19_pull_check_source``.
        """
        return [
            ("purchase.order", _("Purchase Order / ใบสั่งซื้อ")),
            ("sale.order", _("Sale Order / ใบสั่งขาย")),
            ("account.move", _("Invoice/Bill / ใบแจ้งหนี้/ใบวางบิล")),
            ("purchase.request", _("Purchase Request / ใบขอซื้อ")),
            ("stock.picking", _("Transfer / ใบรับ-ส่งสินค้า")),
        ]

    @api.onchange("source_ref")
    def _onchange_source_ref(self):
        """Rebuild the candidate rows whenever the source document changes."""
        self.line_ids = [Command.clear()]
        self._od19_build_lines()

    def _od19_build_lines(self):
        self.ensure_one()
        if not self.source_ref or not self.res_model or not self.res_id:
            return
        target = self._od19_get_target()
        source = self.source_ref
        commands = [
            Command.create(target._od19_pull_line_info(source, line))
            for line in target._od19_pull_candidate_lines(source)
        ]
        self.line_ids = commands

    def _od19_selected_source_lines(self):
        """Return the recordset of selected source lines."""
        self.ensure_one()
        selected = self.line_ids.filtered("selected")
        if not selected:
            return False
        models = set(selected.mapped("res_model"))
        if len(models) != 1:
            raise UserError(
                _("Selected lines must come from a single source document.")
            )
        model_name = models.pop()
        return self.env[model_name].browse(selected.mapped("res_id"))

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------

    def action_pull(self):
        self.ensure_one()
        target = (
            self._od19_get_target()
            if self.res_model and self.res_id
            else False
        )
        if not target or not target.exists():
            raise UserError(_("The destination document no longer exists."))
        target._od19_pull_check_editable()
        source = self.source_ref
        target._od19_pull_check_source(source)

        if self.mode == "all_order":
            lines = target._od19_pull_candidate_lines(source)
        else:
            lines = self._od19_selected_source_lines()

        count = target._od19_pull_apply(source, lines) if lines else 0
        if not count:
            raise UserError(_("There is no line to pull from this document."))
        return {"type": "ir.actions.act_window_close"}
