# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
"""Confirmation wizard: the user always confirms before lines are removed."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class Od19DocumentPullRemoveWizard(models.TransientModel):
    _name = "od19.document.pull.remove.wizard"
    _description = "OD19 Document Pull Remove Wizard"

    res_model = fields.Char(
        string="Destination Model / โมเดลปลายทาง", required=True
    )
    res_id = fields.Integer(
        string="Destination ID / รหัสเอกสารปลายทาง", required=True
    )
    state = fields.Selection(
        selection=[
            ("choose", "Choose the source / เลือกเอกสารต้นทาง"),
            ("confirm", "Confirm the removal / ยืนยันการลบ"),
        ],
        string="Step / ขั้นตอน",
        default="choose",
        required=True,
    )
    source_ids = fields.One2many(
        comodel_name="od19.document.pull.remove.source",
        inverse_name="wizard_id",
        string="Source Documents / เอกสารต้นทาง",
    )
    source_id = fields.Reference(
        selection="_selection_source_id",
        string="Source Document / เอกสารต้นทาง",
    )
    source_line_ids = fields.One2many(
        comodel_name="od19.document.pull.remove.line",
        inverse_name="wizard_id",
        string="Lines to remove / รายการที่จะลบ",
    )
    remove_summary = fields.Char(
        string="Summary / สรุป",
        compute="_compute_remove_summary",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _od19_get_target(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id)

    @api.model
    def _selection_source_id(self):
        # Static and context-independent: the ORM evaluates a Reference
        # selection on an empty recordset both when rendering the widget and
        # when validating the stored value.
        return [
            ("purchase.order", _("Purchase Order / ใบสั่งซื้อ")),
            ("sale.order", _("Sale Order / ใบสั่งขาย")),
            ("account.move", _("Invoice/Bill / ใบแจ้งหนี้/ใบวางบิล")),
            ("purchase.request", _("Purchase Request / ใบขอซื้อ")),
            ("stock.picking", _("Transfer / ใบรับ-ส่งสินค้า")),
        ]

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        for wizard in wizards:
            wizard._od19_build_bound_sources()
        return wizards

    @api.onchange("res_model", "res_id")
    def _onchange_target(self):
        self._od19_build_bound_sources()

    def _od19_build_bound_sources(self):
        self.ensure_one()
        commands = []
        if self.res_model and self.res_id:
            target = self._od19_get_target().exists()
            if target:
                commands = [
                    Command.create(
                        {
                            "source_ref": "%s,%s" % (source._name, source.id),
                            "name": "%s (%s)" % (source.display_name, count),
                        }
                    )
                    for source, count in target._od19_pull_bound_sources()
                ]
        self.source_ids = [Command.clear()] + commands

    @api.depends("source_line_ids", "source_id")
    def _compute_remove_summary(self):
        for wizard in self:
            count = len(wizard.source_line_ids)
            if wizard.source_id and count:
                wizard.remove_summary = _(
                    "Document %(name)s will have %(count)s line(s) removed.",
                    name=wizard.source_id.display_name,
                    count=count,
                )
            else:
                wizard.remove_summary = False

    def _od19_push_preview_lines(self, target, source):
        self.ensure_one()
        commands = [
            Command.create(dict(vals, wizard_id=self.id))
            for vals in target._od19_pull_preview_lines(source)
        ]
        self.source_line_ids = [Command.clear()] + commands
        return self.source_line_ids

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_select_source(self):
        """Move to the confirmation step and preview the lines to remove."""
        self.ensure_one()
        target = self._od19_get_target()
        target._od19_pull_check_editable()
        if not self.source_id:
            raise UserError(_("Please select the source document to remove."))
        source = self.source_id
        target._od19_pull_check_source(source)
        lines = self._od19_push_preview_lines(target, source)
        if not lines:
            raise UserError(
                _(
                    "There is no line linked to %(name)s in this document.",
                    name=source.display_name,
                )
            )
        self.state = "confirm"
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_back(self):
        self.ensure_one()
        self.state = "choose"
        self.source_line_ids = [Command.clear()]
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_remove(self):
        """Remove the lines after the user confirmed."""
        self.ensure_one()
        target = self._od19_get_target()
        target._od19_pull_check_editable()
        if not self.source_id:
            raise UserError(_("No source document selected."))
        target._od19_pull_remove(self.source_id)
        return {"type": "ir.actions.act_window_close"}
